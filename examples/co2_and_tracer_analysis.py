"""
Example script for simple image analysis. By comparison of images
of the same well test, a tracer concentration can be determined.
"""

import os
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import skimage

import daria


def preprocessing(img: np.ndarray) -> np.ndarray:
    """Standard for reading an image from file, applying curvature correction
    and and color correction.

    Args:
        img (np.ndarray): image array

    Returns:
        np.ndarray: corrected image
    """

    # Define curvature correction object, initiated with config file
    # (which can be created the workflow presented in the Jupyter notebook
    # examples/notebooks/curvature_correction_walkthrough.ipynb).
    curvature_correction = daria.CurvatureCorrection(
        config_source=str(Path(f"{os.path.dirname(__file__)}/images/config.json")),
        width=2.8,
        height=1.5,
    )

    # Apply curvature correction.
    img = curvature_correction(img)

    # Transform to RGB space.
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Apply color correction - need to specify a crude ROI containing the color checker.
    roi_cc = (slice(0, 600), slice(0, 700))
    color_correction = daria.ColorCorrection()
    img = color_correction(img, roi_cc)

    return img


def determine_tracer(img: np.ndarray, base: np.ndarray) -> np.ndarray:
    """Extract tracer based on a reference image.

    Args:
        img (np.ndarray):  probe image array
        base (np.ndarray): baseline image array

    Returns:
        np.ndarray: concentration map
    """
    # Transform images to grayscale
    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    base = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY)

    # Take (unsigned) difference
    diff = skimage.util.compare_images(img, base, method="diff")

    # Apply smoothing filter
    diff = skimage.filters.rank.median(diff, skimage.morphology.disk(20))

    # The next step is to translate the color intensity to the actual concentration.
    # Such post-processing is very much scenario dependent and require further knowledge
    # of the physical process, or injection schedule etc. Here, an arbitrary thresholding
    # routine is applied as an example. More advanced postprocessing routines are also
    # possible,

    # Apply thresholding to cut off noise
    thresh_min = 5
    thresh_max = 40
    tracer_min_mask = diff <= thresh_min
    diff[tracer_min_mask] = 0
    diff[~tracer_min_mask] -= thresh_min
    tracer_max_mask = diff >= thresh_max - thresh_min
    diff[tracer_max_mask] = thresh_max - thresh_min

    # Transform to float data type for simpler conversion to tracer concentration
    diff = skimage.util.img_as_float(diff)

    # Rescale image to physically meaningful range [0,1]
    diff = skimage.exposure.rescale_intensity(diff)

    return diff


# !----- Main routine for co2 analysis

# Read image and preprocess baseline image
baseline = cv2.imread(str(Path(f"{os.path.dirname(__file__)}/images/co2_0.jpg")))
baseline = preprocessing(baseline)

# Read and preprocess test image
co2_image = cv2.imread(str(Path(f"{os.path.dirname(__file__)}/images/co2_2.jpg")))
co2_image = preprocessing(co2_image)

# Determine co2
co2 = determine_tracer(co2_image, baseline)

# Plot
plt.imshow(co2)
plt.show(block=False)
# Pause longer if it is desired to keep the images on the screen
plt.pause(3)
plt.close()

# !----- Main routine for tracer analysis

# Read in baseline figure and apply correction once
baseline = cv2.imread(str(Path(f"{os.path.dirname(__file__)}/images/tracer_0.jpg")))
baseline = preprocessing(baseline)

# Read in test figure and apply correction
# tracer_image = cv2.imread("./images/tracer_1.jpg")
# tracer_image = cv2.imread("./images/tracer_2.jpg")
tracer_image = cv2.imread(str(Path(f"{os.path.dirname(__file__)}/images/tracer_3.jpg")))
tracer_image = preprocessing(tracer_image)

# Determine tracer
tracer = determine_tracer(tracer_image, baseline)

# Plot
plt.imshow(tracer)
plt.show(block=False)
# Pause longer if it is desired to keep the images on the screen
plt.pause(3)
plt.close()
