from __future__ import annotations

import cv2
import numpy as np
from scipy.ndimage import map_coordinates


# TODO: Add an automatic way (using e.g, gradient decent) to choose the parameters.
def curvature_correction(
    image: np.ndarray,
    width: float = 284,
    height: float = 150,
    horizontal_crop: float = 0.965,
    horizontal_bulge: float = -3.1e-6,
    horizontal_stretch: float = 2.35e-6,
    horizontal_stretch_mid: float = -0,
    vertical_crop: float = 0.92,
    vertical_bulge: float = 0.5e-6,
    vertical_shear: float = 2e-3,
    interpolation_order: int = 1,
) -> np.ndarray:
    """
    Curvature correction.
    Arguments:
        img (np.ndarray): image array
        img (str): path to image, alternative way to feed the actual image.
        width (float): physical width of image.
        height (float): physical height of image.
        vertical_bulge (float): parameter for the curvature correction related to
                                the vertical bulge of the image.
        horizontal_crop (float): parameter for the curvature correction for cropping the image.
        horizontal_bulge (float): parameter for the curvature correction related to
                                  the horizontal bulge of the image.
        horizontal_stretch (float): parameter for the curvature correction related to
                                    the horizontal stretch of the image.
        horizontal_stretch_mid (float): parameter for the curvature correction related to
                                        the horizontal stretch of the image.
        vertical_crop (float): parameter for the curvature correction for cropping the image.
        vertical_bulge (float): parameter for the curvature correction related to
                                the vertical bulge of the image.
        vertical_shear (float): parameter for the curvature correction correcting for
                                vertical shear in the image.
    """
    if isinstance(image, np.ndarray):
        img = image
    elif isinstance(image, str):
        img = cv2.imread(image)
    else:
        raise Exception(
            "Invalid image data. Provide either a path to an image or an image array."
        )

    # Read size of image
    Ny, Nx = img.shape[:2]

    # Center image, and set physical values
    x = (np.array(range(1, Nx + 1)) - round(Nx / 2)) / Nx * width
    y = (np.array(range(1, Ny + 1)) - round(Ny / 2)) / Ny * height
    y = y.reshape((1, Ny))

    # Make it into a meshgrid
    X, Y = np.meshgrid(x, y)

    # Curvature corrected grid using input parameters
    Xmod = horizontal_crop * np.multiply(
        np.multiply(X, (1 + horizontal_stretch * (X - horizontal_stretch_mid) ** 2)),
        (1 - vertical_bulge * Y ** 2),
    )
    Ymod = vertical_crop * (
        np.multiply(Y, (1 - horizontal_bulge * X ** 2)) - vertical_shear * X
    )

    # Map corrected grid back to positional arguments
    Xmod = Xmod * Nx / width + round(Nx / 2) - 1
    Ymod = Ymod * Ny / height + round(Ny / 2) - 1

    # Create out grid as the corrected grid, but not in meshgrid format
    out_grid = np.array([Ymod.ravel(), Xmod.ravel()])

    # Return image
    img_mod = np.zeros((Ny, Nx, 3), dtype=np.uint8)

    # Do interpolate original image on the new grid
    for i in range(img[0, 0, :].size):
        in_data = img[:, :, i]
        im_array = map_coordinates(in_data, out_grid, order=interpolation_order)
        img_mod[:, :, i] = im_array.reshape(img[:, :, 0].shape).astype(np.uint8)

    return img_mod
