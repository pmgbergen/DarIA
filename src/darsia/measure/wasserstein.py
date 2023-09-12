"""Wasserstein distance computed using variational methods.

"""
from __future__ import annotations

import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pyamg
import scipy.sparse as sps

import darsia

# General TODO list
# - improve documentation, in particular with focus on keywords
# - remove plotting
# - improve assembling of operators through partial assembling
# - improve stopping criteria
# - use better quadrature for l1_dissipation?


class VariationalWassersteinDistance(darsia.EMD):
    """Base class for setting up the variational Wasserstein distance.

    The variational Wasserstein distance is defined as the solution to the following
    optimization problem (also called the Beckman problem):
    inf ||u||_{L^1} s.t. div u = m_1 - m_2, u in H(div).
    u is the flux, m_1 and m_2 are the mass distributions which are transported by u
    from m_1 to m_2.

    Specialized classes implement the solution of the Beckman problem using different
    methods. There are two main methods:
    - Newton's method (:class:`WassersteinDistanceNewton`)
    - Split Bregman method (:class:`WassersteinDistanceBregman`)

    """

    def __init__(
        self,
        shape: tuple,
        voxel_size: list,
        dim: int,
        options: dict = {},
    ) -> None:
        """
        Args:

            shape (tuple): shape of the image
            voxel_size (list): voxel size of the image
            dim (int): dimension of the problem
            options (dict): options for the solver
                - num_iter (int): maximum number of iterations. Defaults to 100.
                - tol (float): tolerance for the stopping criterion. Defaults to 1e-6.
                - L (float): parameter for the Bregman iteration. Defaults to 1.0.
                - regularization (float): regularization parameter for the Bregman
                    iteration. Defaults to 0.0.
                - aa_depth (int): depth of the Anderson acceleration. Defaults to 0.
                - aa_restart (int): restart of the Anderson acceleration. Defaults to None.
                - scaling (float): scaling of the fluxes in the plot. Defaults to 1.0.
                - lumping (bool): lump the mass matrix. Defaults to True.

        """
        # Cache geometrical infos
        self.shape = shape
        self.voxel_size = voxel_size
        self.dim = dim

        assert dim == 2, "Currently only 2D images are supported."

        self.options = options
        self.regularization = self.options.get("regularization", 0.0)
        self.verbose = self.options.get("verbose", False)

        # Setup of finite volume discretization
        self._setup()

    def _setup(self) -> None:
        """Setup of fixed discretization"""

        # ! ---- Grid management ----

        # Define dimensions of the problem and indexing of cells, from here one start
        # counting rows from left to right, from top to bottom.
        dim_cells = self.shape
        num_cells = np.prod(dim_cells)
        flat_numbering_cells = np.arange(num_cells, dtype=int)
        numbering_cells = flat_numbering_cells.reshape(dim_cells)

        # Define center cell
        center_cell = np.array([self.shape[0] // 2, self.shape[1] // 2]).astype(int)
        self.flat_center_cell = np.ravel_multi_index(center_cell, dim_cells)

        # Consider only inner faces; implicitly define indexing of faces (first
        # vertical, then horizontal). The counting of vertical faces starts from top to
        # bottom and left to right. The counting of horizontal faces starts from left to
        # right and top to bottom.
        vertical_faces_shape = (self.shape[0], self.shape[1] - 1)
        horizontal_faces_shape = (self.shape[0] - 1, self.shape[1])
        num_vertical_faces = np.prod(vertical_faces_shape)
        num_horizontal_faces = np.prod(horizontal_faces_shape)
        num_faces_axis = [
            num_vertical_faces,
            num_horizontal_faces,
        ]
        num_faces = np.sum(num_faces_axis)

        # Define flat indexing of faces: vertical faces first, then horizontal faces
        flat_vertical_faces = np.arange(num_vertical_faces, dtype=int)
        flat_horizontal_faces = num_vertical_faces + np.arange(
            num_horizontal_faces, dtype=int
        )
        vertical_faces = flat_vertical_faces.reshape(vertical_faces_shape)
        horizontal_faces = flat_horizontal_faces.reshape(horizontal_faces_shape)

        # Identify vertical faces on top, inner and bottom
        top_row_vertical_faces = np.ravel(vertical_faces[0, :])
        inner_vertical_faces = np.ravel(vertical_faces[1:-1, :])
        bottom_row_vertical_faces = np.ravel(vertical_faces[-1, :])
        # Identify horizontal faces on left, inner and right
        left_col_horizontal_faces = np.ravel(horizontal_faces[:, 0])
        inner_horizontal_faces = np.ravel(horizontal_faces[:, 1:-1])
        right_col_horizontal_faces = np.ravel(horizontal_faces[:, -1])

        # ! ---- Connectivity ----

        # Define connectivity and direction of the normal on faces
        connectivity = np.zeros((num_faces, 2), dtype=int)
        # Vertical faces to left cells
        connectivity[: num_faces_axis[0], 0] = np.ravel(numbering_cells[:, :-1])
        # Vertical faces to right cells
        connectivity[: num_faces_axis[0], 1] = np.ravel(numbering_cells[:, 1:])
        # Horizontal faces to top cells
        connectivity[num_faces_axis[0] :, 0] = np.ravel(numbering_cells[:-1, :])
        # Horizontal faces to bottom cells
        connectivity[num_faces_axis[0] :, 1] = np.ravel(numbering_cells[1:, :])

        # Define reverse connectivity. Cell to vertical faces
        connectivity_cell_to_vertical_face = -np.ones((num_cells, 2), dtype=int)
        # Left vertical face of cell
        connectivity_cell_to_vertical_face[
            np.ravel(numbering_cells[:, 1:]), 0
        ] = flat_vertical_faces
        # Right vertical face of cell
        connectivity_cell_to_vertical_face[
            np.ravel(numbering_cells[:, :-1]), 1
        ] = flat_vertical_faces
        # Define reverse connectivity. Cell to horizontal faces
        connectivity_cell_to_horizontal_face = np.zeros((num_cells, 2), dtype=int)
        # Top horizontal face of cell
        connectivity_cell_to_horizontal_face[
            np.ravel(numbering_cells[1:, :]), 0
        ] = flat_horizontal_faces
        # Bottom horizontal face of cell
        connectivity_cell_to_horizontal_face[
            np.ravel(numbering_cells[:-1, :]), 1
        ] = flat_horizontal_faces

        # Info about inner cells
        # TODO rm?
        inner_cells_with_vertical_faces = np.ravel(numbering_cells[:, 1:-1])
        inner_cells_with_horizontal_faces = np.ravel(numbering_cells[1:-1, :])
        num_inner_cells_with_vertical_faces = len(inner_cells_with_vertical_faces)
        num_inner_cells_with_horizontal_faces = len(inner_cells_with_horizontal_faces)

        # ! ---- Operators ----

        # Define sparse divergence operator, integrated over elements.
        # Note: The global direction of the degrees of freedom is hereby fixed for all
        # faces. Fluxes across vertical faces go from left to right, fluxes across
        # horizontal faces go from bottom to top. To oppose the direction of the outer
        # normal, the sign of the divergence is flipped for one side of cells for all
        # faces.
        div_shape = (num_cells, num_faces)
        div_data = np.concatenate(
            (
                self.voxel_size[0] * np.ones(num_vertical_faces, dtype=float),
                self.voxel_size[1] * np.ones(num_horizontal_faces, dtype=float),
                -self.voxel_size[0] * np.ones(num_vertical_faces, dtype=float),
                -self.voxel_size[1] * np.ones(num_horizontal_faces, dtype=float),
            )
        )
        div_row = np.concatenate(
            (
                connectivity[
                    flat_vertical_faces, 0
                ],  # vertical faces, cells to the left
                connectivity[
                    flat_horizontal_faces, 0
                ],  # horizontal faces, cells to the top
                connectivity[
                    flat_vertical_faces, 1
                ],  # vertical faces, cells to the right (opposite normal)
                connectivity[
                    flat_horizontal_faces, 1
                ],  # horizontal faces, cells to the bottom (opposite normal)
            )
        )
        div_col = np.tile(np.arange(num_faces, dtype=int), 2)
        self.div = sps.csc_matrix(
            (div_data, (div_row, div_col)),
            shape=div_shape,
        )

        # Define sparse mass matrix on cells: flat_mass -> flat_mass
        self.mass_matrix_cells = sps.diags(
            np.prod(self.voxel_size) * np.ones(num_cells, dtype=float)
        )

        # Define sparse mass matrix on faces: flat fluxes -> flat fluxes
        lumping = self.options.get("lumping", True)
        if lumping:
            self.mass_matrix_faces = 0.5 * sps.diags(
                np.prod(self.voxel_size) * np.ones(num_faces, dtype=float)
            )
        else:
            # Define true RT0 mass matrix on faces: flat fluxes -> flat fluxes
            mass_matrix_faces_shape = (num_faces, num_faces)
            mass_matrix_faces_data = np.prod(self.voxel_size) * np.concatenate(
                (
                    2 / 3 * np.ones(num_faces, dtype=float),  # all faces
                    1
                    / 6
                    * np.ones(
                        num_inner_cells_with_vertical_faces, dtype=float
                    ),  # left faces
                    1
                    / 6
                    * np.ones(
                        num_inner_cells_with_vertical_faces, dtype=float
                    ),  # right faces
                    1
                    / 6
                    * np.ones(
                        num_inner_cells_with_horizontal_faces, dtype=float
                    ),  # top faces
                    1
                    / 6
                    * np.ones(
                        num_inner_cells_with_horizontal_faces, dtype=float
                    ),  # bottom faces
                )
            )
            mass_matrix_faces_row = np.concatenate(
                (
                    np.arange(num_faces, dtype=int),
                    connectivity_cell_to_vertical_face[
                        inner_cells_with_vertical_faces, 0
                    ],
                    connectivity_cell_to_vertical_face[
                        inner_cells_with_vertical_faces, 1
                    ],
                    connectivity_cell_to_horizontal_face[
                        inner_cells_with_horizontal_faces, 0
                    ],
                    connectivity_cell_to_horizontal_face[
                        inner_cells_with_horizontal_faces, 1
                    ],
                )
            )
            mass_matrix_faces_col = np.concatenate(
                (
                    np.arange(num_faces, dtype=int),
                    connectivity_cell_to_vertical_face[
                        inner_cells_with_vertical_faces, 1
                    ],
                    connectivity_cell_to_vertical_face[
                        inner_cells_with_vertical_faces, 0
                    ],
                    connectivity_cell_to_horizontal_face[
                        inner_cells_with_horizontal_faces, 1
                    ],
                    connectivity_cell_to_horizontal_face[
                        inner_cells_with_horizontal_faces, 0
                    ],
                )
            )
            self.mass_matrix_faces = sps.csc_matrix(
                (
                    mass_matrix_faces_data,
                    (mass_matrix_faces_row, mass_matrix_faces_col),
                ),
                shape=mass_matrix_faces_shape,
            )

        # Operator for averaging fluxes on orthogonal, neighboring faces
        orthogonal_face_average_shape = (num_faces, num_faces)
        orthogonal_face_average_data = 0.25 * np.concatenate(
            (
                np.ones(
                    2 * len(top_row_vertical_faces)
                    + 4 * len(inner_vertical_faces)
                    + 2 * len(bottom_row_vertical_faces)
                    + 2 * len(left_col_horizontal_faces)
                    + 4 * len(inner_horizontal_faces)
                    + 2 * len(right_col_horizontal_faces),
                    dtype=float,
                ),
            )
        )
        orthogonal_face_average_rows = np.concatenate(
            (
                np.tile(top_row_vertical_faces, 2),
                np.tile(inner_vertical_faces, 4),
                np.tile(bottom_row_vertical_faces, 2),
                np.tile(left_col_horizontal_faces, 2),
                np.tile(inner_horizontal_faces, 4),
                np.tile(right_col_horizontal_faces, 2),
            )
        )
        orthogonal_face_average_cols = np.concatenate(
            (
                # top row: left cell -> bottom face
                connectivity_cell_to_horizontal_face[
                    connectivity[top_row_vertical_faces, 0], 1
                ],
                # top row: vertical face -> right cell -> bottom face
                connectivity_cell_to_horizontal_face[
                    connectivity[top_row_vertical_faces, 1], 1
                ],
                # inner rows: vertical face -> left cell -> top face
                connectivity_cell_to_horizontal_face[
                    connectivity[inner_vertical_faces, 0], 0
                ],
                # inner rows: vertical face -> left cell -> bottom face
                connectivity_cell_to_horizontal_face[
                    connectivity[inner_vertical_faces, 0], 1
                ],
                # inner rows: vertical face -> right cell -> top face
                connectivity_cell_to_horizontal_face[
                    connectivity[inner_vertical_faces, 1], 0
                ],
                # inner rows: vertical face -> right cell -> bottom face
                connectivity_cell_to_horizontal_face[
                    connectivity[inner_vertical_faces, 1], 1
                ],
                # bottom row: vertical face -> left cell -> top face
                connectivity_cell_to_horizontal_face[
                    connectivity[bottom_row_vertical_faces, 0], 0
                ],
                # bottom row: vertical face -> right cell -> top face
                connectivity_cell_to_horizontal_face[
                    connectivity[bottom_row_vertical_faces, 1], 0
                ],
                # left column: horizontal face -> top cell -> right face
                connectivity_cell_to_vertical_face[
                    connectivity[left_col_horizontal_faces, 0], 1
                ],
                # left column: horizontal face -> bottom cell -> right face
                connectivity_cell_to_vertical_face[
                    connectivity[left_col_horizontal_faces, 1], 1
                ],
                # inner columns: horizontal face -> top cell -> left face
                connectivity_cell_to_vertical_face[
                    connectivity[inner_horizontal_faces, 0], 0
                ],
                # inner columns: horizontal face -> top cell -> right face
                connectivity_cell_to_vertical_face[
                    connectivity[inner_horizontal_faces, 0], 1
                ],
                # inner columns: horizontal face -> bottom cell -> left face
                connectivity_cell_to_vertical_face[
                    connectivity[inner_horizontal_faces, 1], 0
                ],
                # inner columns: horizontal face -> bottom cell -> right face
                connectivity_cell_to_vertical_face[
                    connectivity[inner_horizontal_faces, 1], 1
                ],
                # right column: horizontal face -> top cell -> left face
                connectivity_cell_to_vertical_face[
                    connectivity[right_col_horizontal_faces, 0], 0
                ],
                # right column: horizontal face -> bottom cell -> left face
                connectivity_cell_to_vertical_face[
                    connectivity[right_col_horizontal_faces, 1], 0
                ],
            )
        )
        self.orthogonal_face_average = sps.csc_matrix(
            (
                orthogonal_face_average_data,
                (orthogonal_face_average_rows, orthogonal_face_average_cols),
            ),
            shape=orthogonal_face_average_shape,
        )

        # Define sparse embedding operators, and quick access through indices.
        # Assume the ordering of the faces is vertical faces first, then horizontal
        # faces. After that, cell variabes are provided for the potential, finally a
        # scalar variable for the lagrange multiplier.
        self.flux_embedding = sps.csc_matrix(
            (
                np.ones(num_faces, dtype=float),
                (np.arange(num_faces), np.arange(num_faces)),
            ),
            shape=(num_faces + num_cells + 1, num_faces),
        )

        self.flux_indices = np.arange(num_faces)
        self.potential_indices = np.arange(num_faces, num_faces + num_cells)
        self.lagrange_multiplier_indices = np.array([num_faces + num_cells], dtype=int)

        # ! ---- Utilities ----
        aa_depth = self.options.get("aa_depth", 0)
        aa_restart = self.options.get("aa_restart", None)
        self.anderson = (
            darsia.AndersonAcceleration(
                dimension=None, depth=aa_depth, restart=aa_restart
            )
            if aa_depth > 0
            else None
        )

        # ! ---- Cache ----
        self.num_faces = num_faces
        self.num_cells = num_cells
        self.dim_cells = dim_cells
        self.numbering_cells = numbering_cells
        self.num_faces_axis = num_faces_axis
        self.vertical_faces_shape = vertical_faces_shape
        self.horizontal_faces_shape = horizontal_faces_shape

    def _problem_specific_setup(self, mass_diff: np.ndarray) -> None:
        """Resetup of fixed discretization"""

        # Fix index of center cell
        self.constrained_cell_flat_index = self.flat_center_cell
        self.potential_constraint = sps.csc_matrix(
            (
                np.ones(1, dtype=float),
                (np.zeros(1, dtype=int), np.array([self.constrained_cell_flat_index])),
            ),
            shape=(1, self.num_cells),
            dtype=float,
        )

        # Linear part of the operator.
        self.broken_darcy = sps.bmat(
            [
                [None, -self.div.T, None],
                [self.div, None, -self.potential_constraint.T],
                [None, self.potential_constraint, None],
            ],
            format="csc",
        )

    def split_solution(
        self, solution: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, float]:
        """Split the solution into (flat) fluxes, potential and lagrange multiplier.

        Args:
            solution (np.ndarray): solution

        Returns:
            tuple: fluxes, potential, lagrange multiplier

        """
        # Split the solution
        flat_flux = solution[: self.num_faces]
        flat_potential = solution[self.num_faces : self.num_faces + self.num_cells]
        flat_lagrange_multiplier = solution[-1]

        return flat_flux, flat_potential, flat_lagrange_multiplier

    # ! ---- Projections inbetween faces and cells ----

    def face_to_cell(self, flat_flux: np.ndarray) -> np.ndarray:
        """Reconstruct the fluxes on the cells from the fluxes on the faces.

        Use the Raviart-Thomas reconstruction of the fluxes on the cells from the fluxes
        on the faces, and use arithmetic averaging of the fluxes on the faces,
        equivalent with the L2 projection of the fluxes on the faces to the fluxes on
        the cells.

        Matrix-free implementation.

        Args:
            flat_flux (np.ndarray): flat fluxes (normal fluxes on the faces)

        Returns:
            np.ndarray: cell-based vectorial fluxes

        """
        # Reshape fluxes - use duality of faces and normals
        horizontal_fluxes = flat_flux[: self.num_faces_axis[0]].reshape(
            self.vertical_faces_shape
        )
        vertical_fluxes = flat_flux[self.num_faces_axis[0] :].reshape(
            self.horizontal_faces_shape
        )

        # Determine a cell-based Raviart-Thomas reconstruction of the fluxes, projected
        # onto piecewise constant functions.
        cell_flux = np.zeros((*self.dim_cells, self.dim), dtype=float)
        # Horizontal fluxes
        cell_flux[:, :-1, 0] += 0.5 * horizontal_fluxes
        cell_flux[:, 1:, 0] += 0.5 * horizontal_fluxes
        # Vertical fluxes
        cell_flux[:-1, :, 1] += 0.5 * vertical_fluxes
        cell_flux[1:, :, 1] += 0.5 * vertical_fluxes

        return cell_flux

    def cell_to_face(self, cell_qty: np.ndarray, mode: str) -> np.ndarray:
        """Project scalar cell quantity to scalr face quantity.

        Allow for arithmetic or harmonic averaging of the cell quantity to the faces. In
        the harmonic case, the averaging is regularized to avoid division by zero.
        Matrix-free implementation.

        Args:
            cell_qty (np.ndarray): scalar-valued cell-based quantity
            mode (str): mode of projection, either "arithmetic" or "harmonic"
                (averaging)

        Returns:
            np.ndarray: face-based quantity

        """
        # Determine the fluxes on the faces
        if mode == "arithmetic":
            # Employ arithmetic averaging
            horizontal_face_qty = 0.5 * (cell_qty[:, :-1] + cell_qty[:, 1:])
            vertical_face_qty = 0.5 * (cell_qty[:-1, :] + cell_qty[1:, :])
        elif mode == "harmonic":
            # Employ harmonic averaging
            arithmetic_avg_horizontal = 0.5 * (cell_qty[:, :-1] + cell_qty[:, 1:])
            arithmetic_avg_vertical = 0.5 * (cell_qty[:-1, :] + cell_qty[1:, :])
            # Regularize to avoid division by zero
            regularization = 1e-10
            arithmetic_avg_horizontal = (
                arithmetic_avg_horizontal
                + (2 * np.sign(arithmetic_avg_horizontal) + 1) * regularization
            )
            arithmetic_avg_vertical = (
                0.5 * arithmetic_avg_vertical
                + (2 * np.sign(arithmetic_avg_vertical) + 1) * regularization
            )
            product_horizontal = np.multiply(cell_qty[:, :-1], cell_qty[:, 1:])
            product_vertical = np.multiply(cell_qty[:-1, :], cell_qty[1:, :])

            # Determine the harmonic average
            horizontal_face_qty = product_horizontal / arithmetic_avg_horizontal
            vertical_face_qty = product_vertical / arithmetic_avg_vertical
        else:
            raise ValueError(f"Mode {mode} not supported.")

        # Reshape the fluxes - hardcoding the connectivity here
        face_qty = np.concatenate(
            [horizontal_face_qty.ravel(), vertical_face_qty.ravel()]
        )

        return face_qty

    # NOTE: Currently not in use. TODO rm?
    #    def face_restriction(self, cell_flux: np.ndarray) -> np.ndarray:
    #        """Restrict vector-valued fluxes on cells to normal components on faces.
    #
    #        Matrix-free implementation. The fluxes on the faces are determined by
    #        arithmetic averaging of the fluxes on the cells in the direction of the normal
    #        of the face.
    #
    #        Args:
    #            cell_flux (np.ndarray): cell-based fluxes
    #
    #        Returns:
    #            np.ndarray: face-based fluxes
    #
    #        """
    #        # Determine the fluxes on the faces through arithmetic averaging
    #        horizontal_fluxes = 0.5 * (cell_flux[:, :-1, 0] + cell_flux[:, 1:, 0])
    #        vertical_fluxes = 0.5 * (cell_flux[:-1, :, 1] + cell_flux[1:, :, 1])
    #
    #        # Reshape the fluxes
    #        flat_flux = np.concatenate(
    #            [horizontal_fluxes.ravel(), vertical_fluxes.ravel()], axis=0
    #        )
    #
    #        return flat_flux

    # ! ---- Effective quantities ----

    def transport_density(self, cell_flux: np.ndarray) -> np.ndarray:
        """Compute the transport density of the solution.

        Args:
            flat_flux (np.ndarray): flat fluxes

        Returns:
            np.ndarray: transport density
        """
        return np.linalg.norm(cell_flux, 2, axis=-1)

    # TODO consider to replace transport_density with this function:

    # def compute_transport_density(self, solution: np.ndarray) -> np.ndarray:
    #     """Compute the transport density from the solution.

    #     Args:
    #         solution (np.ndarray): solution

    #     Returns:
    #         np.ndarray: transport density

    #     """
    #     # Compute transport density
    #     flat_flux, _, _ = self.split_solution(solution)
    #     cell_flux = self.face_to_cell(flat_flux)
    #     norm = np.linalg.norm(cell_flux, 2, axis=-1)
    #     return norm

    def l1_dissipation(self, flat_flux: np.ndarray, mode: str) -> float:
        """Compute the l1 dissipation potential of the solution.

        Args:
            flat_flux (np.ndarray): flat fluxes

        Returns:
            float: l1 dissipation potential

        """
        if mode == "cell_arithmetic":
            cell_flux = self.face_to_cell(flat_flux)
            cell_flux_norm = np.ravel(np.linalg.norm(cell_flux, 2, axis=-1))
            return self.mass_matrix_cells.dot(cell_flux_norm).sum()
        elif mode == "face_arithmetic":
            face_flux_norm = self.vector_face_flux_norm(flat_flux, "face_arithmetic")
            return self.mass_matrix_faces.dot(face_flux_norm).sum()

    # ! ---- Lumping of effective mobility

    def vector_face_flux_norm(self, flat_flux: np.ndarray, mode: str) -> np.ndarray:
        """Compute the norm of the vector-valued fluxes on the faces.

        Args:
            flat_flux (np.ndarray): flat fluxes (normal fluxes on the faces)
            mode (str): mode of the norm, either "cell_arithmetic", "cell_harmonic" or
                "face_arithmetic". In the cell-based modes, the fluxes are projected to
                the cells and the norm is computed there. In the face-based mode, the
                norm is computed directly on the faces.

        Returns:
            np.ndarray: norm of the vector-valued fluxes on the faces

        """

        # Determine the norm of the fluxes on the faces
        if mode in ["cell_arithmetic", "cell_harmonic"]:
            # Consider the piecewise constant projection of vector valued fluxes
            cell_flux = self.face_to_cell(flat_flux)
            # Determine the norm of the fluxes on the cells
            cell_flux_norm = np.maximum(
                np.linalg.norm(cell_flux, 2, axis=-1), self.regularization
            )
            # Determine averaging mode from mode - either arithmetic or harmonic
            average_mode = mode.split("_")[1]
            flat_flux_norm = self.cell_to_face(cell_flux_norm, mode=average_mode)

        elif mode == "face_arithmetic":
            # Define natural vector valued flux on faces (taking arithmetic averages
            # of continuous fluxes over cells evaluated at faces)
            tangential_flux = self.orthogonal_face_average.dot(flat_flux)
            # Determine the l2 norm of the fluxes on the faces, add some regularization
            flat_flux_norm = np.sqrt(flat_flux**2 + tangential_flux**2)

        else:
            raise ValueError(f"Mode {mode} not supported.")

        return flat_flux_norm

    # ! ---- Main methods ----

    def __call__(
        self,
        img_1: darsia.Image,
        img_2: darsia.Image,
        plot_solution: bool = False,
        return_solution: bool = False,
    ) -> float:
        """L1 Wasserstein distance for two images with same mass.

        NOTE: Images need to comply with the setup of the object.

        Args:
            img_1 (darsia.Image): image 1
            img_2 (darsia.Image): image 2
            plot_solution (bool): plot the solution. Defaults to False.
            return_solution (bool): return the solution. Defaults to False.

        Returns:
            float or array: distance between img_1 and img_2.

        """

        # Start taking time
        tic = time.time()

        # Compatibilty check
        assert img_1.scalar and img_2.scalar
        self._compatibility_check(img_1, img_2)

        # Determine difference of distriutions and define corresponding rhs
        mass_diff = img_1.img - img_2.img
        flat_mass_diff = np.ravel(mass_diff)
        self._problem_specific_setup(mass_diff)

        # Main method
        distance, solution, status = self._solve(flat_mass_diff)

        # Split the solution
        flat_flux, flat_potential, _ = self.split_solution(solution)

        # Reshape the fluxes and potential to grid format
        flux = self.face_to_cell(flat_flux)
        potential = flat_potential.reshape(self.dim_cells)

        # Determine transport density
        transport_density = self.transport_density(flux)

        # Stop taking time
        toc = time.time()
        status["elapsed_time"] = toc - tic
        print("Elapsed time: ", toc - tic)

        # Plot the solution
        if plot_solution:
            self._plot_solution(mass_diff, flux, potential, transport_density)

        if return_solution:
            return distance, flux, potential, transport_density, status
        else:
            return distance

    # TODO rm.
    def _plot_solution(
        self,
        mass_diff: np.ndarray,
        flux: np.ndarray,
        potential: np.ndarray,
        transport_density: np.ndarray,
    ) -> None:
        """Plot the solution.

        Args:
            mass_diff (np.ndarray): difference of mass distributions
            flux (np.ndarray): fluxes
            potential (np.ndarray): potential
            transport_density (np.ndarray): transport density

        """
        # Fetch options
        plot_options = self.options.get("plot_options", {})

        # Store plot
        save_plot = plot_options.get("save", False)
        if save_plot:
            name = plot_options.get("name", None)
            folder = plot_options.get("folder", ".")
            Path(folder).mkdir(parents=True, exist_ok=True)
        show_plot = plot_options.get("show", True)

        # Control of flux arrows
        scaling = plot_options.get("scaling", 1.0)
        resolution = plot_options.get("resolution", 1)

        # Meshgrid
        Y, X = np.meshgrid(
            self.voxel_size[0] * (0.5 + np.arange(self.shape[0] - 1, -1, -1)),
            self.voxel_size[1] * (0.5 + np.arange(self.shape[1])),
            indexing="ij",
        )

        # Plot the potential
        plt.figure("Beckman solution potential")
        plt.pcolormesh(X, Y, potential, cmap="turbo")
        plt.colorbar(label="potential")
        plt.quiver(
            X[::resolution, ::resolution],
            Y[::resolution, ::resolution],
            scaling * flux[::resolution, ::resolution, 0],
            -scaling * flux[::resolution, ::resolution, 1],
            angles="xy",
            scale_units="xy",
            scale=1,
            alpha=0.25,
            width=0.005,
        )
        plt.xlabel("x [m]")
        plt.ylabel("y [m]")
        plt.ylim(top=0.08)  # TODO rm?
        if save_plot:
            plt.savefig(
                folder + "/" + name + "_beckman_solution_potential.png",
                dpi=500,
                transparent=True,
            )

        # Plot the fluxes
        plt.figure("Beckman solution fluxes")
        plt.pcolormesh(X, Y, mass_diff, cmap="turbo", vmin=-1, vmax=3.5)
        plt.colorbar(label="mass difference")
        plt.quiver(
            X[::resolution, ::resolution],
            Y[::resolution, ::resolution],
            scaling * flux[::resolution, ::resolution, 0],
            -scaling * flux[::resolution, ::resolution, 1],
            angles="xy",
            scale_units="xy",
            scale=1,
            alpha=0.25,
            width=0.005,
        )
        plt.xlabel("x [m]")
        plt.ylabel("y [m]")
        plt.ylim(top=0.08)
        plt.text(
            0.0025,
            0.075,
            name,
            color="white",
            alpha=0.9,
            rotation=0,
            fontsize=14,
        )  # TODO rm?
        if save_plot:
            plt.savefig(
                folder + "/" + name + "_beckman_solution_fluxes.png",
                dpi=500,
                transparent=True,
            )

        # Plot the transport density
        plt.figure("L1 optimal transport density")
        plt.pcolormesh(X, Y, transport_density, cmap="turbo")
        plt.colorbar(label="flux modulus")
        plt.xlabel("x [m]")
        plt.ylabel("y [m]")
        plt.ylim(top=0.08)  # TODO rm?
        if save_plot:
            plt.savefig(
                folder + "/" + name + "_beckman_solution_transport_density.png",
                dpi=500,
                transparent=True,
            )

        if show_plot:
            plt.show()
        else:
            plt.close("all")


class WassersteinDistanceNewton(VariationalWassersteinDistance):
    """Class to determine the L1 EMD/Wasserstein distance solved with Newton's method."""

    def residual(self, rhs: np.ndarray, solution: np.ndarray) -> np.ndarray:
        """Compute the residual of the solution.

        Args:
            rhs (np.ndarray): right hand side
            solution (np.ndarray): solution

        Returns:
            np.ndarray: residual

        """
        flat_flux, _, _ = self.split_solution(solution)
        mode = self.options.get("mode", "face_arithmetic")
        flat_flux_norm = np.maximum(
            self.vector_face_flux_norm(flat_flux, mode=mode), self.regularization
        )
        flat_flux_normed = flat_flux / flat_flux_norm

        return (
            rhs
            - self.broken_darcy.dot(solution)
            - self.flux_embedding.dot(self.mass_matrix_faces.dot(flat_flux_normed))
        )

    def jacobian(self, solution: np.ndarray) -> sps.linalg.LinearOperator:
        """Compute the LU factorization of the jacobian of the solution.

        Args:
            solution (np.ndarray): solution

        Returns:
            sps.linalg.splu: LU factorization of the jacobian

        """
        flat_flux, _, _ = self.split_solution(solution)
        mode = self.options.get("mode", "face_arithmetic")
        flat_flux_norm = np.maximum(
            self.vector_face_flux_norm(flat_flux, mode=mode), self.regularization
        )
        approx_jacobian = sps.bmat(
            [
                [
                    sps.diags(np.maximum(self.L, 1.0 / flat_flux_norm), dtype=float)
                    * self.mass_matrix_faces,
                    -self.div.T,
                    None,
                ],
                [self.div, None, -self.potential_constraint.T],
                [None, self.potential_constraint, None],
            ],
            format="csc",
        )
        return approx_jacobian

    def darcy_jacobian(self) -> sps.linalg.LinearOperator:
        """Compute the Jacobian of a standard homogeneous Darcy problem.

        The mobility is defined by the used via options["L_init"]. The jacobian is
        cached for later use.

        """
        L_init = self.options.get("L_init", 1.0)
        jacobian = sps.bmat(
            [
                [L_init * self.mass_matrix_faces, -self.div.T, None],
                [self.div, None, -self.potential_constraint.T],
                [None, self.potential_constraint, None],
            ],
            format="csc",
        )
        return jacobian

    def setup_infrastructure(self) -> None:
        """Setup the infrastructure for reduced systems through Gauss elimination.

        Provide internal data structures for the reduced system.

        """
        # Step 1: Compute the jacobian of the Darcy problem

        # The Darcy problem is sufficient
        jacobian = self.darcy_jacobian()

        # Step 2: Remove flux blocks through Schur complement approach

        # Build Schur complement wrt. flux-flux block
        J_inv = sps.diags(1.0 / jacobian.diagonal()[self.flux_indices])
        D = jacobian[self.num_faces :, : self.num_faces].copy()
        schur_complement = D.dot(J_inv.dot(D.T))

        # Cache divergence matrix
        self.D = D.copy()
        self.DT = self.D.T.copy()

        # Cache (constant) jacobian subblock
        self.jacobian_subblock = jacobian[self.num_faces :, self.num_faces :].copy()

        # Add Schur complement - use this to identify sparsity structure
        # Cache the reduced jacobian
        self.reduced_jacobian = self.jacobian_subblock + schur_complement

        # Step 3: Remove potential block through Gauss elimination

        # Find row entries to be removed
        rm_row_entries = np.arange(
            self.reduced_jacobian.indptr[self.constrained_cell_flat_index],
            self.reduced_jacobian.indptr[self.constrained_cell_flat_index + 1],
        )

        # Find column entries to be removed
        rm_col_entries = np.where(
            self.reduced_jacobian.indices == self.constrained_cell_flat_index
        )[0]

        # Collect all entries to be removes
        rm_indices = np.unique(
            np.concatenate((rm_row_entries, rm_col_entries)).astype(int)
        )
        # Cache for later use in remove_lagrange_multiplier
        self.rm_indices = rm_indices

        # Identify rows to be reduced
        rm_rows = [
            np.max(np.where(self.reduced_jacobian.indptr <= index)[0])
            for index in rm_indices
        ]

        # Reduce data - simply remove
        fully_reduced_jacobian_data = np.delete(self.reduced_jacobian.data, rm_indices)

        # Reduce indices - remove and shift
        fully_reduced_jacobian_indices = np.delete(
            self.reduced_jacobian.indices, rm_indices
        )
        fully_reduced_jacobian_indices[
            fully_reduced_jacobian_indices > self.constrained_cell_flat_index
        ] -= 1

        # Reduce indptr - shift and remove
        # NOTE: As only a few entries should be removed, this is not too expensive
        # and a for loop is used
        fully_reduced_jacobian_indptr = self.reduced_jacobian.indptr.copy()
        for row in rm_rows:
            fully_reduced_jacobian_indptr[row + 1 :] -= 1
        fully_reduced_jacobian_indptr = np.unique(fully_reduced_jacobian_indptr)

        # Make sure two rows are removed and deduce shape of reduced jacobian
        assert (
            len(fully_reduced_jacobian_indptr) == len(self.reduced_jacobian.indptr) - 2
        ), "Two rows should be removed."
        fully_reduced_jacobian_shape = (
            len(fully_reduced_jacobian_indptr) - 1,
            len(fully_reduced_jacobian_indptr) - 1,
        )

        # Cache the fully reduced jacobian
        self.fully_reduced_jacobian = sps.csc_matrix(
            (
                fully_reduced_jacobian_data,
                fully_reduced_jacobian_indices,
                fully_reduced_jacobian_indptr,
            ),
            shape=fully_reduced_jacobian_shape,
        )

        # Cache the indices and indptr
        self.fully_reduced_jacobian_indices = fully_reduced_jacobian_indices.copy()
        self.fully_reduced_jacobian_indptr = fully_reduced_jacobian_indptr.copy()
        self.fully_reduced_jacobian_shape = fully_reduced_jacobian_shape

        # Step 4: Identify inclusions (index arrays)

        # Define reduced system indices wrt full system
        self.reduced_system_indices = np.concatenate(
            [self.potential_indices, self.lagrange_multiplier_indices]
        )

        # Define fully reduced system indices wrt reduced system - need to remove cell
        # (and implicitly lagrange multiplier)
        self.fully_reduced_system_indices = np.delete(
            np.arange(self.num_cells), self.constrained_cell_flat_index
        )

        # Define fully reduced system indices wrt full system
        self.fully_reduced_system_indices_full = self.reduced_system_indices[
            self.fully_reduced_system_indices
        ]

    def remove_flux(self, jacobian: sps.csc_matrix, residual: np.ndarray) -> tuple:
        """Remove the flux block from the jacobian and residual.

        Args:
            jacobian (sps.csc_matrix): jacobian
            residual (np.ndarray): residual

        Returns:
            tuple: reduced jacobian, reduced residual, inverse of flux block

        """
        # Build Schur complement wrt flux-block
        J_inv = sps.diags(1.0 / jacobian.diagonal()[self.flux_indices])
        schur_complement = self.D.dot(J_inv.dot(self.DT))

        # Gauss eliminiation on matrices
        reduced_jacobian = self.jacobian_subblock + schur_complement

        # Gauss elimination on vectors
        reduced_residual = residual[self.reduced_system_indices].copy()
        reduced_residual -= self.D.dot(J_inv.dot(residual[self.flux_indices]))

        return reduced_jacobian, reduced_residual, J_inv

    def remove_lagrange_multiplier(self, jacobian, residual, solution) -> tuple:
        """Shortcut for removing the lagrange multiplier from the reduced jacobian.

        Args:

            solution (np.ndarray): solution, TODO make function independent of solution

        Returns:
            tuple: fully reduced jacobian, fully reduced residual

        """
        # Make sure the jacobian is a CSC matrix
        assert isinstance(jacobian, sps.csc_matrix), "Jacobian should be a CSC matrix."

        # Effective Gauss-elimination for the particular case of the lagrange multiplier
        self.fully_reduced_jacobian.data[:] = np.delete(
            self.reduced_jacobian.data.copy(), self.rm_indices
        )
        # NOTE: The indices have to be restored if the LU factorization is to be used
        # FIXME omit if not required
        self.fully_reduced_jacobian.indices = self.fully_reduced_jacobian_indices.copy()

        # Rhs is not affected by Gauss elimination as it is assumed that the residual
        # is zero in the constrained cell, and the pressure is zero there as well.
        # If not, we need to do a proper Gauss elimination on the right hand side!
        if abs(residual[-1]) > 1e-6:
            raise NotImplementedError("Implementation requires residual to be zero.")
        if abs(solution[self.num_faces + self.constrained_cell_flat_index]) > 1e-6:
            raise NotImplementedError("Implementation requires solution to be zero.")
        fully_reduced_residual = self.reduced_residual[
            self.fully_reduced_system_indices
        ].copy()

        return self.fully_reduced_jacobian, fully_reduced_residual

    def linearization_step(
        self, solution: np.ndarray, rhs: np.ndarray, iter: int
    ) -> tuple[np.ndarray, np.ndarray, list[float]]:
        """Newton step for the linearization of the problem.

        In the first iteration, the linearization is the linearization of the Darcy
        problem.

        Args:
            solution (np.ndarray): solution
            rhs (np.ndarray): right hand side
            iter (int): iteration number

        Returns:
            tuple: update, residual, stats (timinings)

        """
        # Determine residual and (full) Jacobian
        tic = time.time()
        if iter == 0:
            residual = rhs.copy()
            approx_jacobian = self.darcy_jacobian()
        else:
            residual = self.residual(rhs, solution)
            approx_jacobian = self.jacobian(solution)
        toc = time.time()
        time_setup = toc - tic

        # Allocate update
        update = np.zeros_like(solution, dtype=float)

        # Setup linear solver
        tic = time.time()
        linear_solver = self.options.get("linear_solver", "lu")
        assert linear_solver in [
            "lu",
            "lu-flux-reduced",
            "amg-flux-reduced",
            "lu-potential",
            "amg-potential",
        ], f"Linear solver {linear_solver} not supported."

        if linear_solver in ["amg-flux-reduced", "amg-potential"]:
            # TODO add possibility for user control
            ml_options = {
                # B=X.reshape(
                #    n * n, 1
                # ),  # the representation of the near null space (this is a poor choice)
                # BH=None,  # the representation of the left near null space
                "symmetry": "hermitian",  # indicate that the matrix is Hermitian
                # strength="evolution",  # change the strength of connection
                "aggregate": "standard",  # use a standard aggregation method
                "smooth": (
                    "jacobi",
                    {"omega": 4.0 / 3.0, "degree": 2},
                ),  # prolongation smoothing
                "presmoother": ("block_gauss_seidel", {"sweep": "symmetric"}),
                "postsmoother": ("block_gauss_seidel", {"sweep": "symmetric"}),
                # improve_candidates=[
                #    ("block_gauss_seidel", {"sweep": "symmetric", "iterations": 4}),
                #    None,
                # ],
                "max_levels": 4,  # maximum number of levels
                "max_coarse": 1000,  # maximum number on a coarse level
                # keep=False,  # keep extra operators around in the hierarchy (memory)
            }
            tol_amg = self.options.get("linear_solver_tol", 1e-6)
            res_history_amg = []

        # Solve linear system for the update
        if linear_solver == "lu":
            # Solve full system
            tic = time.time()
            jacobian_lu = sps.linalg.splu(approx_jacobian)
            time_setup = time.time() - tic
            tic = time.time()
            update = jacobian_lu.solve(residual)
            time_solve = time.time() - tic
        elif linear_solver in ["lu-flux-reduced", "amg-flux-reduced"]:
            # Solve potential-multiplier problem

            # Reduce flux block
            tic = time.time()
            (
                self.reduced_jacobian,
                self.reduced_residual,
                jacobian_flux_inv,
            ) = self.remove_flux(approx_jacobian, residual)

            if linear_solver == "lu-flux-reduced":
                lu = sps.linalg.splu(self.reduced_jacobian)
                time_setup = time.time() - tic
                tic = time.time()
                update[self.reduced_system_indices] = lu.solve(self.reduced_residual)

            elif linear_solver == "amg-flux-reduced":
                ml = pyamg.smoothed_aggregation_solver(
                    self.reduced_jacobian, **ml_options
                )
                time_setup = time.time() - tic
                tic = time.time()
                update[self.reduced_system_indices] = ml.solve(
                    self.reduced_residual,
                    tol=tol_amg,
                    residuals=res_history_amg,
                )

            # Compute flux update
            update[self.flux_indices] = jacobian_flux_inv.dot(
                residual[self.flux_indices]
                + self.DT.dot(update[self.reduced_system_indices])
            )
            time_solve = time.time() - tic

        elif linear_solver in ["lu-potential", "amg-potential"]:
            # Solve pure potential problem

            # Reduce flux block
            tic = time.time()
            (
                self.reduced_jacobian,
                self.reduced_residual,
                jacobian_flux_inv,
            ) = self.remove_flux(approx_jacobian, residual)

            # Reduce to pure pressure system
            (
                self.fully_reduced_jacobian,
                self.fully_reduced_residual,
            ) = self.remove_lagrange_multiplier(
                self.reduced_jacobian, self.reduced_residual, solution
            )

            if linear_solver == "lu-potential":
                lu = sps.linalg.splu(self.fully_reduced_jacobian)
                time_setup = time.time() - tic
                tic = time.time()
                update[self.fully_reduced_system_indices_full] = lu.solve(
                    self.fully_reduced_residual
                )

            elif linear_solver == "amg-potential":
                ml = pyamg.smoothed_aggregation_solver(
                    self.fully_reduced_jacobian, **ml_options
                )
                time_setup = time.time() - tic
                tic = time.time()
                update[self.fully_reduced_system_indices_full] = ml.solve(
                    self.fully_reduced_residual,
                    tol=tol_amg,
                    residuals=res_history_amg,
                )

            # Compute flux update
            update[self.flux_indices] = jacobian_flux_inv.dot(
                residual[self.flux_indices]
                + self.DT.dot(update[self.reduced_system_indices])
            )
            time_solve = time.time() - tic

        # Diagnostics
        if linear_solver in ["amg-flux-reduced", "amg-potential"]:
            if self.options.get("linear_solver_verbosity", False):
                num_amg_iter = len(res_history_amg)
                res_amg = res_history_amg[-1]
                print(ml)
                print(
                    f"#AMG iterations: {num_amg_iter}; Residual after AMG step: {res_amg}"
                )

        # Collect stats
        stats = [time_setup, time_solve]

        return update, residual, stats

    def _solve(self, flat_mass_diff: np.ndarray) -> tuple[float, np.ndarray, dict]:
        """Solve the Beckman problem using Newton's method.

        Args:
            flat_mass_diff (np.ndarray): difference of mass distributions

        Returns:
            tuple: distance, solution, status

        """
        # TODO rm: Observation: AA can lead to less stagnation, more accurate results,
        # and therefore better solutions to mu and u. Higher depth is better, but more
        # expensive.

        # Setup
        tic = time.time()
        self.setup_infrastructure()
        time_infrastructure = time.time() - tic
        print("timing infra structure", time_infrastructure)

        # Solver parameters
        num_iter = self.options.get("num_iter", 100)
        tol_residual = self.options.get("tol_residual", 1e-6)
        tol_increment = self.options.get("tol_increment", 1e-6)
        tol_distance = self.options.get("tol_distance", 1e-6)

        # Relaxation parameter
        self.L = self.options.get("L", 1.0)

        # Define right hand side
        rhs = np.concatenate(
            [
                np.zeros(self.num_faces, dtype=float),
                self.mass_matrix_cells.dot(flat_mass_diff),
                np.zeros(1, dtype=float),
            ]
        )

        # Initialize solution
        solution_i = np.zeros_like(rhs)

        # Initialize container for storing the convergence history
        convergence_history = {
            "distance": [],
            "residual": [],
            "decomposed residual": [],
            "increment": [],
            "decomposed increment": [],
            "distance increment": [],
            "timing": [],
        }

        # Print header
        if self.verbose:
            print(
                "--- ; ",
                "Newton iteration",
                "distance",
                "residual",
                "mass conservation residual",
                "increment",
                "flux increment",
                "distance increment",
            )

        # Newton iteration
        for iter in range(num_iter):
            # Keep track of old flux, and old distance
            old_solution_i = solution_i.copy()
            old_distance = self.l1_dissipation(solution_i)

            # Newton step
            update_i, residual_i, stats_i = self.linearization_step(
                solution_i, rhs, iter
            )
            solution_i += update_i

            # Apply Anderson acceleration to flux contribution (the only nonlinear part).
            # Application to full solution, or just the potential, lead to divergence,
            # while application to the flux, results in improved performance.
            tic = time.time()
            if self.anderson is not None:
                solution_i[: self.num_faces] = self.anderson(
                    solution_i[: self.num_faces], update_i[: self.num_faces], iter
                )
            toc = time.time()
            time_anderson = toc - tic
            stats_i.append(time_anderson)

            # Update distance
            new_distance = self.l1_dissipation(solution_i)

            # Compute the error:
            # - full residual
            # - residual of the flux equation
            # - residual of mass conservation equation
            # - residual of the constraint equation
            # - full increment
            # - flux increment
            # - potential increment
            # - lagrange multiplier increment
            # - distance increment
            increment = solution_i - old_solution_i
            error = [
                np.linalg.norm(residual_i, 2),
                [
                    np.linalg.norm(residual_i[: self.num_faces], 2),
                    np.linalg.norm(residual_i[self.num_faces : -1], 2),
                    np.linalg.norm(residual_i[-1:], 2),
                ],
                np.linalg.norm(increment, 2),
                [
                    np.linalg.norm(increment[: self.num_faces], 2),
                    np.linalg.norm(increment[self.num_faces : -1], 2),
                    np.linalg.norm(increment[-1:], 2),
                ],
                abs(new_distance - old_distance),
            ]

            # Update convergence history
            convergence_history["distance"].append(new_distance)
            convergence_history["residual"].append(error[0])
            convergence_history["decomposed residual"].append(error[1])
            convergence_history["increment"].append(error[2])
            convergence_history["decomposed increment"].append(error[3])
            convergence_history["distance increment"].append(error[4])
            convergence_history["timing"].append(stats_i)

            if self.verbose:
                print(
                    "Newton iteration",
                    iter,
                    new_distance,
                    error[0],  # residual
                    error[1],  # mass conservation residual
                    error[2],  # full increment
                    error[3],  # flux increment
                    error[4],  # distance increment
                    stats_i,  # timing
                )

            # Stopping criterion
            # TODO include criterion build on staganation of the solution
            if iter > 1 and (
                (error[0] < tol_residual and error[2] < tol_increment)
                or error[4] < tol_distance
            ):
                break

        # Define performance metric
        status = {
            "converged": iter < num_iter,
            "number iterations": iter,
            "distance": new_distance,
            "residual": error[0],
            "mass conservation residual": error[1],
            "increment": error[2],
            "flux increment": error[3],
            "distance increment": abs(new_distance - old_distance),
            "convergence history": convergence_history,
        }

        return new_distance, solution_i, status


class WassersteinDistanceBregman(VariationalWassersteinDistance):
    def _problem_specific_setup(self, mass_diff: np.ndarray) -> None:
        super()._problem_specific_setup(mass_diff)
        self.L = self.options.get("L", 1.0)
        l_scheme_mixed_darcy = sps.bmat(
            [
                [self.L * self.mass_matrix_faces, -self.div.T, None],
                [self.div, None, -self.potential_constraint.T],
                [None, self.potential_constraint, None],
            ],
            format="csc",
        )
        self.l_scheme_mixed_darcy_lu = sps.linalg.splu(l_scheme_mixed_darcy)

    def _shrink(
        self, flat_flux: np.ndarray, mode: str = "cell_arithmetic"
    ) -> np.ndarray:
        """Shrink operation in the split Bregman method.

        Operation on fluxes.

        Args:
            flat_flux (np.ndarray): flux
            mode (str, optional): mode of the shrink operation. Defaults to "cell_arithmetic".

        Returns:
            np.ndarray: shrunk fluxes

        """
        if mode == "cell_arithmetic":
            # Idea: Determine the shrink factor based on the cell reconstructions of the
            # fluxes. Convert cell-based shrink factors to face-based shrink factors
            # through arithmetic averaging.
            cell_flux = self.face_to_cell(flat_flux)
            norm = np.linalg.norm(cell_flux, 2, axis=-1)
            cell_scaling = np.maximum(norm - 1 / self.L, 0) / (
                norm + self.regularization
            )
            flat_scaling = self.cell_to_face(cell_scaling, mode="arithmetic")

        elif mode == "face_normal":
            # Only consider normal direction (does not take into account the full flux)
            # TODO rm.
            norm = np.linalg.norm(flat_flux, 2, axis=-1)
            flat_scaling = np.maximum(norm - 1 / self.L, 0) / (
                norm + self.regularization
            )

        else:
            raise NotImplementedError(f"Mode {mode} not supported.")

        return flat_scaling * flat_flux

    def _solve(self, flat_mass_diff):
        # Solver parameters
        num_iter = self.options.get("num_iter", 100)
        tol_residual = self.options.get("tol_residual", 1e-6)
        tol_increment = self.options.get("tol_increment", 1e-6)
        tol_distance = self.options.get("tol_distance", 1e-6)

        # Relaxation parameter
        self.L = self.options.get("L", 1.0)
        rhs = np.concatenate(
            [
                np.zeros(self.num_faces, dtype=float),
                self.mass_matrix_cells.dot(flat_mass_diff),
                np.zeros(1, dtype=float),
            ]
        )

        # Keep track of how often the distance increases.
        num_neg_diff = 0

        # Initialize container for storing the convergence history
        convergence_history = {
            "distance": [],
            "mass residual": [],
            "force": [],
            "flux increment": [],
            "aux increment": [],
            "force increment": [],
            "distance increment": [],
            "timing": [],
        }

        # Print header
        if self.verbose:
            print(
                "--- ; ",
                "Bregman iteration",
                "L",
                "distance",
                "mass conservation residual",
                "increment",
                "flux increment",
                "distance increment",
            )

        # Initialize Bregman variables - two auxiliary variables
        old_aux_variable = np.zeros(self.num_faces, dtype=float)
        new_aux_variable = np.zeros(self.num_faces, dtype=float)
        old_force = np.zeros(self.num_faces, dtype=float)
        new_force = np.zeros(self.num_faces, dtype=float)

        # Bregman iterations
        solution_i = np.zeros_like(rhs)
        old_flat_flux_i = solution_i[: self.num_faces]
        for iter in range(num_iter):
            old_distance = self.l1_dissipation(solution_i)

            # 1. Solve linear system with trust in current flux.
            tic = time.time()
            flat_flux_i, _, _ = self.split_solution(solution_i)
            rhs_i = rhs.copy()
            rhs_i[: self.num_faces] = self.L * self.mass_matrix_faces.dot(flat_flux_i)
            intermediate_solution_i = self.l_scheme_mixed_darcy_lu.solve(rhs_i)
            time_linearization = time.time() - tic

            # 2. Shrink step for vectorial fluxes. To comply with the RT0 setting, the
            # shrinkage operation merely determines the scalar. We still aim at
            # following along the direction provided by the vectorial fluxes.
            tic = time.time()
            intermediate_flat_flux_i, _, _ = self.split_solution(
                intermediate_solution_i
            )
            new_flat_flux_i = self._shrink(intermediate_flat_flux_i)
            time_shrink = time.time() - tic

            # Apply Anderson acceleration to flux contribution (the only nonlinear part).
            tic = time.time()
            if self.anderson is not None:
                flux_inc = new_flat_flux_i - flat_flux_i
                new_flat_flux_i = self.anderson(new_flat_flux_i, flux_inc, iter)
            toc = time.time()
            time_anderson = toc - tic

            # Collect stats
            stats_i = [time_linearization, time_shrink, time_anderson]

            # Update flux solution
            solution_i = intermediate_solution_i.copy()
            solution_i[: self.num_faces] = new_flat_flux_i

            # Update distance
            new_distance = self.l1_dissipation(solution_i)

            # Determine the error in the mass conservation equation
            mass_conservation_residual = np.linalg.norm(
                (rhs_i - self.broken_darcy.dot(solution_i))[self.num_faces : -1], 2
            )

            # Determine increments
            flux_increment = new_flat_flux_i - old_flat_flux_i
            aux_increment = new_aux_variable - old_aux_variable
            force_increment = new_force - old_force

            # Determine force
            force = np.linalg.norm(new_force, 2)

            # Compute the error:
            # - residual of mass conservation equation - should be always zero if exact solver used
            # - force
            # - flux increment
            # - aux increment
            # - force increment
            # - distance increment
            error = [
                mass_conservation_residual,
                force,
                np.linalg.norm(flux_increment),
                np.linalg.norm(aux_increment),
                np.linalg.norm(force_increment),
                abs(new_distance - old_distance),
            ]

            # Update convergence history
            convergence_history["distance"].append(new_distance)
            convergence_history["mass residual"].append(error[0])
            convergence_history["force"].append(error[1])
            convergence_history["flux increment"].append(error[2])
            convergence_history["aux increment"].append(error[3])
            convergence_history["force increment"].append(error[4])
            convergence_history["distance increment"].append(error[5])
            convergence_history["timing"].append(stats_i)

            # Print status
            if self.verbose:
                print(
                    "Bregman iteration",
                    iter,
                    new_distance,
                    self.L,
                    error[0],  # mass conservation residual
                    error[1],  # force
                    error[2],  # flux increment
                    error[3],  # aux increment
                    error[4],  # force increment
                    error[5],  # distance increment
                    stats_i,  # timing
                )

            # Keep track if the distance increases.
            if new_distance > old_distance:
                num_neg_diff += 1

            # Increase L if stagnating of the distance increases too often.
            update_l = self.options.get("update_l", True)
            if update_l:
                tol_distance = self.options.get("tol_distance", 1e-12)
                max_iter_increase_diff = self.options.get("max_iter_increase_diff", 20)
                l_factor = self.options.get("l_factor", 2)
                if (
                    abs(new_distance - old_distance) < tol_distance
                    or num_neg_diff > max_iter_increase_diff
                ):
                    # Update L
                    self.L = self.L * l_factor

                    # Update linear system
                    l_scheme_mixed_darcy = sps.bmat(
                        [
                            [self.L * self.mass_matrix_faces, -self.div.T, None],
                            [self.div, None, -self.potential_constraint.T],
                            [None, self.potential_constraint, None],
                        ],
                        format="csc",
                    )
                    self.l_scheme_mixed_darcy_lu = sps.linalg.splu(l_scheme_mixed_darcy)

                    # Reset stagnation counter
                    num_neg_diff = 0

                L_max = self.options.get("L_max", 1e8)
                if self.L > L_max:
                    break

            # TODO include criterion build on staganation of the solution
            if iter > 1 and (
                (error[0] < tol_residual and error[2] < tol_increment)
                or error[5] < tol_distance
            ):
                break

        # Define performance metric
        status = {
            "converged": iter < num_iter,
            "number iterations": iter,
            "distance": new_distance,
            "mass conservation residual": error[0],
            "flux increment": error[2],
            "distance increment": abs(new_distance - old_distance),
            "convergence history": convergence_history,
        }

        return new_distance, solution_i, status


# Unified access
def wasserstein_distance(
    mass_1: darsia.Image,
    mass_2: darsia.Image,
    method: str,
    **kwargs,
):
    """Unified access to Wasserstein distance computation between images with same mass.

    Args:
        mass_1 (darsia.Image): image 1
        mass_2 (darsia.Image): image 2
        method (str): method to use ("newton", "bregman", or "cv2.emd")
        **kwargs: additional arguments (only for "newton" and "bregman")
            - options (dict): options for the method.
            - plot_solution (bool): plot the solution. Defaults to False.
            - return_solution (bool): return the solution. Defaults to False.

    """
    if method.lower() in ["newton", "bregman"]:
        shape = mass_1.img.shape
        voxel_size = mass_1.voxel_size
        dim = mass_1.space_dim

        # Fetch options
        options = kwargs.get("options", {})
        plot_solution = kwargs.get("plot_solution", False)
        return_solution = kwargs.get("return_solution", False)

        if method.lower() == "newton":
            w1 = WassersteinDistanceNewton(shape, voxel_size, dim, options)
        elif method.lower() == "bregman":
            w1 = WassersteinDistanceBregman(shape, voxel_size, dim, options)
        return w1(
            mass_1, mass_2, plot_solution=plot_solution, return_solution=return_solution
        )

    elif method.lower() == "cv2.emd":
        preprocess = kwargs.get("preprocess")
        w1 = darsia.EMD(preprocess)
        return w1(mass_1, mass_2)

    else:
        raise NotImplementedError(f"Method {method} not implemented.")
