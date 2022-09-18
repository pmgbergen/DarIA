from __future__ import annotations

import numpy as np


def cv2ToSkimage(img: np.ndarray) -> np.ndarray:
    """Conversion between opencv (cv2) which has BGR-formatting and scikit-image (skimage)
    which has RGB. The same command works in both directions.

    Arguments:
        img (np.ndarray): input image

    Returns:
        np.ndarray: converted image.
    """
    return img[:, :, ::-1]


def matrixToCartesianIndexing(img: np.ndarray) -> np.ndarray:
    """
    Reordering data indexing converting from (row,col) to (x,y) indexing.

    The conventional matrix indexing uses the (row, col) format, such
    that the top left corner is the (0,0) pixel. On the other hand,
    Cartesian indexing uses the (x,y) order and thereby identifies
    the lower left corner by (0,0). This routine is in particular useful
    when communicating image data to conventional simulators, which use
    the Cartesian indexing.

    Arguments:
        np.ndarray: image array with matrix indexing

    Returns:
        np.ndarray: image array with Cartesian indexing
    """
    # Two operations are require: Swapping axis and flipping the vertical axis.

    # Exchange first and second component, to change from (row,col) to (x,y) format.
    img = np.swapaxes(img, 0, 1)

    # Flip the orientation of the second axis, such that later y=0 is located at the bottom.
    img = np.flip(img, 1)

    return img


def cartesianToMatrixIndexing(img: np.ndarray) -> np.ndarray:
    """
    Reordering data indexing, converting from (x,y) to (row,col) indexing.

    Inverse to matrixToCartesianIndexing.

    Arguments:
        np.ndarray: image array with Cartesian indexing

    Returns:
        np.ndarray: image array with matrix indexing
    """
    # Two operations are require: Swapping axis and flipping the vertical axis.

    # Flip the orientation of the second axis, such that later row=0 is located at the top.
    img = np.flip(img, 1)

    # Exchange first and second component, to change from (x,y) to (row,col) format.
    img = np.swapaxes(img, 0, 1)

    return img
