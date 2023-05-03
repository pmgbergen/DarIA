"""Module containing geometrical transformations for Image objects,
which also change the metadata (opposing to correction routines
aiming at modifying arrays only).

"""
import copy
import itertools
from typing import Optional, Union

import numpy as np
import scipy.optimize as optimize
from scipy.spatial.transform import Rotation

import darsia


class AngularConservativeAffineMap:
    """Affine map, restricted to translation, scaling, rotation, resulting in
    conservation of angles.

    """

    def __init__(
        self,
        pts_src: Optional[list] = None,
        pts_dst: Optional[list] = None,
        **kwargs,
    ) -> None:
        """Constructor.

        Args:
            pts_src (list): coordinates corresponding to source data
            pts_dst (list): coordinates corresponding to destination data

        NOTE: If no input is provided, an identity is constructed.

        Raises:
            ValueError: if not sufficient input data is provided.
            ValueError: if dimension not 2 or 3.

        """

        # ! ---- Characteristics

        self.isometry = kwargs.get("isometry", True)
        """Flag storing whether the underlying transformation is an isometry."""

        # ! ---- Dimension

        # Determine dimensionality from input - perform additional safety checks
        if pts_src is not None and pts_dst is not None:
            assert len(pts_src) == len(pts_dst)
            assert all([len(pts_src[0]) == len(p) for p in pts_src])
            assert all([len(pts_dst[0]) == len(p) for p in pts_dst])
            assert len(pts_src[0]) == len(pts_dst[0])
            dim = len(pts_src[0])

        elif pts_src is not None or pts_dst is not None:
            raise ValueError

        else:
            assert "dim" in kwargs and isinstance(kwargs["dim"], int)
            dim = kwargs["dim"]

        if dim not in [2, 3]:
            raise ValueError
        self.dim = dim
        """Dimension of the Euclidean space."""

        # ! ---- Map

        # If data provided, fit the parameters accordingly
        if pts_src is not None and pts_dst is not None:
            options = kwargs.get("options", {})
            self.fit(pts_src, pts_dst, **options)

        else:
            # Define identity
            self.translation = np.zeros(self.dim, dtype=float)
            """Translation vector."""

            self.scaling = 1.0
            """Scaling factor."""

            self.rotation = np.eye(self.dim)
            """Rotation matrix."""

            self.rotation_inv = np.eye(self.dim)
            """Inverse of rotation matrix."""

    def set_parameters(
        self,
        translation: Optional[np.ndarray] = None,
        scaling: Optional[float] = None,
        rotation: Optional[Union[np.ndarray, list[tuple[float, str]]]] = None,
    ) -> None:
        """Set-access of parameters of map.

        Args:
            translation (array, optional): translation vector.
            scaling (float, optional): scaling value.
            rotation (array, float, or list of tuples, optional): rotation angles.

        """
        if translation is not None:
            self.translation = translation

        if scaling is not None:
            self.scaling = scaling

        if rotation is not None:
            if self.dim == 2:
                degree = rotation
                vector = np.array([0, 0, 1])
                self.rotation = Rotation.from_rotvec(degree * vector).as_matrix()[
                    :2, :2
                ]
                self.rotation_inv = Rotation.from_rotvec(-degree * vector).as_matrix()[
                    :2, :2
                ]

            elif self.dim == 3:

                assert isinstance(rotation, list)
                self.rotation = np.eye(self.dim)
                self.rotation_inv = np.eye(self.dim)

                for degree, cartesian_axis in rotation:
                    matrix_axis, reverted = darsia.interpret_indexing(
                        cartesian_axis, "xyz"[: self.dim]
                    )
                    vector = np.eye(self.dim)[matrix_axis]
                    flip_factor = -1 if reverted else 1

                    rotation = Rotation.from_rotvec(flip_factor * degree * vector)
                    rotation_inv = Rotation.from_rotvec(-degree * vector)

                    self.rotation = np.matmul(self.rotation, rotation.as_matrix())
                    self.rotation_inv = np.matmul(
                        self.rotation_inv, rotation_inv.as_matrix()
                    )

    def set_parameters_as_vector(self, parameters: np.ndarray) -> None:
        """Wrapper for set_parameters.

        Args:
            parameters (array): all parameters concatenated as array.

        """
        rotations_dofs = 1 if self.dim == 2 else self.dim
        if self.isometry:
            assert len(parameters) == self.dim + rotations_dofs
        else:
            assert len(parameters) == self.dim + 1 + rotations_dofs
        translation = parameters[0 : self.dim]
        scaling = 1.0 if self.isometry else parameters[self.dim]
        if self.dim == 2:
            rotation = parameters[-rotations_dofs:]
        elif self.dim == 3:
            rotation = [
                (degree, axis)
                for degree, axis in zip(parameters[-rotations_dofs:], "xyz")
            ]

        self.set_parameters(translation, scaling, rotation)

    def __call__(self, array: np.ndarray) -> np.ndarray:
        """Application of map.

        Args:
            array (np.ndarray): (collection of) dim-dimensional Euclidean vector

        Returns:
            np.ndarray: function values of affine map

        """
        num, dim = np.atleast_2d(array).shape
        assert dim == self.dim
        function_values = np.outer(
            np.ones(num), self.translation
        ) + self.scaling * np.transpose(
            self.rotation.dot(np.transpose(np.atleast_2d(array)))
        )

        return function_values.reshape(array.shape)

    def inverse(self, array: np.ndarray) -> np.ndarray:
        """Application of inverse of the map.

        Args:
            array (np.ndarray): (collection of) dim-dimensional Euclidean vector

        Returns:
            np.ndarray: function values of affine inverse map

        """
        num, dim = np.atleast_2d(array).shape
        assert dim == self.dim
        function_values = (
            1.0
            / self.scaling
            * np.transpose(
                self.rotation_inv.dot(
                    np.transpose(
                        np.atleast_2d(array) - np.outer(np.ones(num), self.translation)
                    )
                )
            )
        )

        return function_values.reshape(array.shape)

    def fit(self, pts_src: list, pts_dst: list, **kwargs) -> bool:
        """Least-squares parameter fit based on source and target coordinates.

        Args:
            pts_src (list): coordinates corresponding to source data
            pts_dst (list): coordinates corresponding to destination data
            kwargs: optimization parameters

        Returns:
            bool: success of parameter fit

        """

        # Define least squares objective function
        def objective_function(params: np.ndarray):
            self.set_parameters_as_vector(params)
            pts_mapped = self.__call__(np.array(pts_src))
            diff = np.array(pts_dst) - pts_mapped
            defect = np.sum(diff**2)
            return defect

        # Fetch calibration options
        if self.isometry:
            identity_parameters = np.array(
                [0, 0, 0] if self.dim == 2 else [0, 0, 0, 0, 0, 0]
            )
        else:
            identity_parameters = np.array(
                [0, 0, 1, 0] if self.dim == 2 else [0, 0, 0, 1, 0, 0, 0]
            )
        initial_guess = kwargs.get("initial_guess", identity_parameters)
        tol = kwargs.get("tol", 1e-2)
        maxiter = kwargs.get("maxiter", 100)

        # Perform optimization step
        opt_result = optimize.minimize(
            objective_function,
            initial_guess,
            tol=tol,
            options={"maxiter": maxiter, "disp": True},
        )
        if opt_result.success:
            print(
                f"Calibration successful with obtained model parameters {opt_result.x}."
            )
        else:
            raise ValueError("Calibration not successful.")

        # Final update of model parameters
        self.set_parameters_as_vector(opt_result.x)

        return opt_result.success


class CoordinateTransformation(darsia.BaseCorrection):
    """
    General affine transformation (translation, scaling, rotation),
    applicable for general (up to 4d) images.

    NOTE: Inherit from base correction to make use of the plain array correction
    routines but complement with meta corrections.

    """

    def __init__(
        self,
        coordinatesystem_src: darsia.CoordinateSystem,
        coordinatesystem_dst: darsia.CoordinateSystem,
        voxels_src: list,
        voxels_dst: list,
        use_cartesian: bool = False,
        **kwargs,
    ) -> None:
        """Constructor.

        Args:
            coordinatesystem_src (CoordinateSystem): coordinate system corresponding
                to voxels_src
            coordinatesystem_dst (CoordinateSystem): coordinate system corresponding
                to voxels_dst
            voxels_src (list): voxel coordinates corresponding to source data; in matrix
                indexing
            voxels_dst (list): voxel coordinates corresponding to destination data; use
                matrix indexing
            use_cartesian (bool): Flag controlling whether the coordinate transformation
                uses Cartesian or  voxel coordinates for the actual map

        """
        # Cache coordinate systems
        self.coordinatesystem_src = coordinatesystem_src
        """Coordinate system corresponding to the input."""

        self.coordinatesystem_dst = coordinatesystem_dst
        """Coordinate system corresponding to the output/target."""

        # Construct optimal coordinate transform in the Cartesian coordinate space.
        # Thus, need to base the construction on the actual relative coordinates.
        isometry = kwargs.get("isometry", False)
        self.use_cartesian = use_cartesian or isometry
        """Flag controlling whether the coordinate transformation uses Cartesian or
        voxel coordinates for the actual map. Overwritten if isometry is activated."""
        if self.use_cartesian:
            pts_src = self.coordinatesystem_src.coordinate(voxels_src)
            pts_dst = self.coordinatesystem_dst.coordinate(voxels_dst)
        else:
            pts_src = voxels_src
            pts_dst = voxels_dst

        # Fetch additional properties
        assert self.coordinatesystem_src.dim == self.coordinatesystem_dst.dim
        self.dim = self.coordinatesystem_src.dim
        """Dimension of the underlying Euclidean spaces."""

        options = kwargs.get("fit_options", {})
        self.angular_conservative_map = AngularConservativeAffineMap(
            pts_src,
            pts_dst,
            dim=self.dim,
            isometry=isometry,
            options=options,
        )
        """Actual coordinate transformation operating between Cartesian spaces."""

    def find_intersection(self) -> tuple[slice, slice]:
        """Determine the active canvas in coordinatesystem_dst, covered by
        coordinatesystem_src after transformed onto the target canvas.

        NOTE: Only supported for 2d.
        NOTE: Requires extra dependency.

        Returns:
            tuple of slices: voxel intervals ready to be used to extract subregions.

        Raises:
            NotImplementedError: if dimension not 2
            ImportError: if Python package largestinteriorrectangle not installed.

        """

        if not self.dim == 2:
            raise NotImplementedError("Intersection option only supported in 2d.")

        try:
            import largestinteriorrectangle as lir
        except ImportError:
            raise ImportError("largestinteriorrectangle not available")

        # Find the voxel locations of the corners in the source array - need them sorted.
        shape_src = self.coordinatesystem_src.shape
        corner_voxels_src = np.array(
            [
                [0, 0],
                [shape_src[0], 0],
                [shape_src[0], shape_src[1]],
                [0, shape_src[1]],
            ]
        )

        # Map these to the target canvas
        corner_coordinates_src = self.coordinatesystem_src.coordinate(corner_voxels_src)
        corner_coordinates_dst = self.angular_conservative_map(corner_coordinates_src)
        corner_voxels_dst = self.coordinatesystem_dst.voxel(corner_coordinates_dst)

        # Clip to active canvas
        num_corners = len(corner_voxels_src)
        shape_dst = self.coordinatesystem_dst.shape
        active_corner_voxels_dst = np.clip(
            corner_voxels_dst,
            0,
            np.outer(np.ones(num_corners), np.array(shape_dst) - 1),
        )

        # Determine the largest interior rectangle - require to transform to format
        # expected by lir
        lir_dst = lir.lir(np.array([active_corner_voxels_dst]).astype(np.int32))
        rectangle_mask_corners = [lir.pt1(lir_dst), lir.pt2(lir_dst)]

        return (
            slice(rectangle_mask_corners[0][0], rectangle_mask_corners[1][0]),
            slice(rectangle_mask_corners[0][1], rectangle_mask_corners[1][1]),
        )

    def correct_array(self, array_src: np.ndarray) -> np.ndarray:
        """Correction routine of array data.

        Args:
            image_src (np.ndarray): array corresponding to some source image

        Returns:
            np.ndarray: array corresponding to some destination image

        """
        # Strategy: Warp entire array by mapping target voxels to destination voxels by
        # applying the inverse mapping.

        # Collect all target voxels in num_voxels_dst x dim format, and convert to
        # Cartesian coordinates
        shape_dst = self.coordinatesystem_dst.shape
        voxels_dst = np.array(
            list(itertools.product(*[range(shape_dst[i]) for i in range(self.dim)]))
        )

        # Find corresponding voxels in the original image by applying the inverse map
        if self.use_cartesian:
            coordinates_dst = self.coordinatesystem_dst.coordinate(voxels_dst)
            coordinates_src = self.angular_conservative_map.inverse(coordinates_dst)
            voxels_src = self.coordinatesystem_src.voxel(coordinates_src)
        else:
            voxels_src = np.round(
                self.angular_conservative_map.inverse(voxels_dst)
            ).astype(int)
        num_voxels = len(voxels_src)

        # Determine active voxels - have to lie within active coordinate system
        shape_src = self.coordinatesystem_src.shape
        mask = np.all(
            np.logical_and(
                0 <= voxels_src,
                voxels_src <= np.outer(np.ones(num_voxels), np.array(shape_src) - 1),
            ),
            axis=1,
        )

        # Warp. Assign voxel values (no interpolation)
        shape = *shape_dst, *list(array_src.shape)[self.dim :]
        array_dst = np.zeros(shape)
        array_dst[tuple(voxels_dst[mask, j] for j in range(self.dim))] = array_src[
            tuple(voxels_src[mask, j] for j in range(self.dim))
        ]

        return array_dst

    def correct_metadata(self, meta_src: dict) -> dict:
        """Correction routine of metadata.

        Args:
            meta_src (dict): metadata corresponding to some source image

        Returns:
            dict: metadata corresponding to a destination image

        """
        # Start with copy
        meta_dst = copy.copy(meta_src)

        # Modify dimensions
        meta_dst["dimensions"] = self.coordinatesystem_dst.dimensions

        # Modify origin
        meta_dst["origin"] = self.coordinatesystem_dst._coordinate_of_origin_voxel

        return meta_dst

    def __call__(self, image: darsia.Image) -> darsia.Image:
        """Main routine, transforming an image and its meta.

        Args:
            image (darsia.Image): input image

        Returns:
            darsia.Image: transformed image

        """
        # Transform the image data (without touching the meta)
        transformed_image_with_original_meta = super().__call__(
            image, return_image=True
        )

        # Transform the meta
        meta_src = image.metadata()
        transformed_meta = self.correct_metadata(meta_src)

        # Define the transformed image with tranformed meta
        return type(image)(transformed_image_with_original_meta.img, **transformed_meta)
