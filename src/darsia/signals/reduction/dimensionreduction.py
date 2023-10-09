"""Dimension modification (reduction along axis and extrusion).

"""

from typing import Union

import numpy as np

import darsia


class AxisReduction:
    """Object for reduction along a provided axis."""

    def __init__(
        self, axis: Union[str, int], dim: int = 3, mode: str = "average", **kwargs
    ) -> None:
        """
        Args:
            axis (int or str): numeric axis index (matrix indexing) or Cartesian axis
            dim (int): dimension of the input image
            mode (str): mode used in the reduction ("average", "sum", "slice")
            kwargs: additional arguments:
                - "depth" (int): depth of the slice (only for mode "slice")

        Raises:
            NotImplementedError: if dim not 3.

        """

        # Convert axis to numeric index
        if isinstance(axis, str):
            assert axis in "xyz"[:dim]
            index, _ = darsia.interpret_indexing(axis, "ijk"[:dim])

        elif isinstance(axis, int):
            assert axis in range(dim)
            index = axis
            index_alpha = "ijk"[:dim][index]
            cartesian_index, _ = darsia.interpret_indexing(index_alpha, "xyz"[:dim])
            axis = "xyz"[cartesian_index]

        self.index: int = index
        """Matrix index along which reduction is performed."""

        self.axis: int = "xyz".find(axis)
        """Cartesian axis along which reduction is performed."""

        self.mode: str = mode
        """Mode."""

        self.kwargs: dict = kwargs
        """Additional arguments."""

    def __call__(self, img: darsia.Image) -> darsia.Image:
        """Reduction routine.

        Args:
            img (Image): nd image.

        Returns:
            Image: (n-1)d image.

        """
        # Manage update of indexing
        original_dim = img.space_dim
        original_axes = "xyz"[:original_dim]
        original_indexing = img.indexing

        # Safety checks
        if not original_indexing == "ijk"[:original_dim]:
            raise NotImplementedError(
                "Only 3d case with standard matrix indexing supported."
            )

        new_dim = original_dim - 1
        new_axes = "xyz"[:new_dim]
        new_indexing = "ijk"[:new_dim]

        interim_indexing = original_indexing.replace(original_indexing[self.index], "")

        # Reduce the data
        if self.mode in ["average", "sum"]:
            img_arr = np.sum(img.img, axis=self.index)

            if self.mode == "average":
                img_arr /= img.img.shape[self.index]
            elif self.mode == "sum":
                pass
        elif self.mode == "slice":
            full_arr = img.img.copy()
            full_arr = np.moveaxis(full_arr, self.index, 0)
            for i in range(self.index - 1, 0, -1):
                full_arr = np.moveaxis(full_arr, i - 1, i)
            depth = self.kwargs["depth"]
            img_arr = full_arr[depth, ...]

        # Reduce dimensions
        new_dimensions = img.dimensions.copy()
        new_dimensions.pop(self.index)

        # Find coordinate of Cartesian 'origin', i.e., [xmin, ymin, zmin]
        min_corner = img.origin.copy()
        for index, matrix_index in enumerate(original_indexing):
            axis, reverse_axis = darsia.interpret_indexing(matrix_index, original_axes)
            if reverse_axis:
                min_corner[axis] -= img.dimensions[index]

        # Reduce to the reduced space
        new_min_corner = min_corner.tolist()
        new_min_corner.pop(self.axis)

        # Determine reduced origin - init with reduced [xmin, ymin, zmin] and add
        # dimensions following the same convention used in the definition of
        # default_origin in Image.
        new_origin = np.array(new_min_corner)
        for new_index, interim_matrix_index in enumerate(interim_indexing):
            # Fetch corresponding character index
            new_matrix_index = new_indexing[new_index]

            # NOTE: The new index is assumed to correspond to new_indexing,
            # uniquely defining the new axis.
            new_cartesian_index, revert_axis = darsia.interpret_indexing(
                new_matrix_index, new_axes
            )

            if revert_axis:
                new_origin[new_cartesian_index] += new_dimensions[new_index]

        # Fetch and adapt metadata
        metadata = img.metadata()
        metadata["space_dim"] = new_dim
        metadata["indexing"] = new_indexing
        metadata["origin"] = new_origin
        metadata["dimensions"] = new_dimensions

        return type(img)(img=img_arr, **metadata)


def reduce_axis(
    image: darsia.Image, axis: Union[str, int], mode: str = "average", **kwargs
) -> darsia.Image:
    """Utility function, essentially wrapping AxisReduction as a method.

    Args:
        img (Image): nd image.
        axis (int or str): numeric index (corresponding to matrix indexing) or
            Cartesian axis
        mode (str): mode used in the reduction ("sum", "scaled", "slice")
        kwargs: additional arguments:
            - "depth" (int): depth of the slice (only for mode "slice")

    Returns:
        Image: (n-1)d image.

    """
    dim = image.space_dim
    reduction = AxisReduction(axis, dim, mode, **kwargs)
    return reduction(image)


def extrude_along_axis(img: darsia.Image, height: float, num: int) -> darsia.Image:
    """Extrude 2d image to a 3d image.

    NOTE: For now the extrusion is performed along the z axis.

    Args:
        img (darsia.Image): 2d image
        height (float): height of the extrusion
        num (int): number of pixels per extruded axis

    Returns:
        darsia.Image: 3d image

    """
    # Fetch data and extrude along 0-axis (z-axis)
    arr = img.img
    shape = arr.shape
    arr_3d = np.zeros((num, *shape), dtype=arr.dtype)
    for i in range(num):
        arr_3d[i, ...] = arr

    # Update metadata
    meta = img.metadata()
    assert meta["space_dim"] == 2
    meta["space_dim"] = 3
    meta["dimensions"] = [height, *meta["dimensions"]]
    meta["indexing"] = "ijk"
    meta["origin"] = [height, *meta["origin"]]

    return type(img)(img=arr_3d, **meta)
