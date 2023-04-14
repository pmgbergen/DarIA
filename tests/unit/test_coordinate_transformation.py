"""Module testing coordinate transformation capabilities for
images with incompatible coordinate systems.

"""

import numpy as np

import darsia


def test_coordinate_transformation_identity_2d():
    """Test coordinate transformation corresponding to identity."""

    # Define image to be transformed
    arr_src = np.array(
        [
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [0, 0, 0, 0],
        ]
    )
    image_src = darsia.Image(
        arr_src,
        dimensions=[3, 4],
    )

    # Define image representative for target canvas
    arr_dst = np.zeros((3, 4), dtype=float)
    image_dst = darsia.Image(
        arr_dst,
        dimensions=[3, 4],
    )

    voxels_src = [[0, 0], [2, 2]]
    voxels_dst = [[0, 0], [2, 2]]

    # Define coordinate transformation
    coordinate_transformation = darsia.CoordinateTransformation(
        image_src.coordinatesystem,
        image_dst.coordinatesystem,
        voxels_src,
        voxels_dst,
    )

    # Check whether coordinate transform generates the same image
    transformed_image = coordinate_transformation(image_src)
    assert np.allclose(transformed_image.img, image_src.img)

    meta_tra = transformed_image.metadata()
    meta_src = image_src.metadata()
    assert np.allclose(meta_tra["origin"], meta_src["origin"])
    assert np.allclose(meta_tra["dimensions"], meta_src["dimensions"])


def test_coordinate_transformation_change_meta_2d():
    """Test coordinate transformation corresponding to embedding with change in
    metadata.

    """

    # Define image to be transformed
    arr_src = np.array(
        [
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [0, 0, 0, 0],
        ]
    )
    image_src = darsia.Image(
        arr_src,
        dimensions=[3, 4],
    )

    # Define image representative for target canvas
    arr_dst = np.zeros((3, 4), dtype=float)
    image_dst = darsia.Image(
        arr_dst,
        dimensions=[30, 40],
        origin=[0, 2],
    )

    voxels_src = [[0, 0], [2, 2]]
    voxels_dst = [[0, 0], [2, 2]]

    # Define coordinate transformation
    coordinate_transformation = darsia.CoordinateTransformation(
        image_src.coordinatesystem,
        image_dst.coordinatesystem,
        voxels_src,
        voxels_dst,
    )

    # Check whether coordinate transform generates the same image
    transformed_image = coordinate_transformation(image_src)
    assert np.allclose(transformed_image.img, image_src.img)

    meta_tra = transformed_image.metadata()
    meta_dst = image_dst.metadata()
    assert np.allclose(meta_tra["origin"], meta_dst["origin"])
    assert np.allclose(meta_tra["dimensions"], meta_dst["dimensions"])
