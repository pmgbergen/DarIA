from __future__ import annotations

import cv2
import numpy as np

import daria as da


def BGR2RGB(img: da.Image) -> da.Image:
    """Conversion between opencv (cv2) which has BGR-formatting and scikit-image (skimage)
    which has RGB. The same command works in both directions.

    Arguments:
        img (np.ndarray): input image

    Returns:
        np.ndarray: converted image.
    """

    img_new = img.copy()
    img_new.img = cv2.cvtColor(img_new.img, cv2.COLOR_BGR2RGB)
    return img_new


def BGR2GRAY(img: da.Image) -> da.Image:
    """Creates a grayscale daria Image from a BGR ones

    Arguments:
        img (da.Image): input image

    Returns:
        da.Image: converged image
    """
    img_gray = img.copy()
    img_gray.img = cv2.cvtColor(img_gray.img, cv2.COLOR_BGR2GRAY)
    return img_gray


def BGR2RED(img: da.Image) -> da.Image:
    """Creates a redscale daria Image from a BGR ones

    Arguments:
        img (da.Image): input image

    Returns:
        da.Image: converged image
    """
    img_red = img.copy()
    if img.colorspace == "BGR":
        img_red.img = img_red.img[:, :, 2]
    elif img.colorspace == "RGB":
        img_red.img = img_red.img[:, :, 0]
    return img_red


def BGR2GREEN(img: da.Image) -> da.Image:
    """Creates a greenscale daria Image from a BGR one

    Arguments:
        img (da.Image): input image

    Returns:
        da.Image: converged image
    """
    img_green = img.copy()
    if img.colorspace == "BGR":
        img_green.img = img_green.img[:, :, 1]
    elif img.colorspace == "RGB":
        img_green.img = img_green.img[:, :, 1]
    return img_green


def BGR2BLUE(img: da.Image) -> da.Image:
    """Creates a bluescale daria Image from a BGR ones

    Arguments:
        img (da.Image): input image

    Returns:
        da.Image: converged image
    """
    img_blue = img.copy()
    if img.colorspace == "BGR":
        img_blue.img = img_blue.img[:, :, 0]
    elif img.colorspace == "RGB":
        img_blue.img = img_blue.img[:, :, 2]
    return img_blue


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
