"""Module to extract characteristic data from input image for given patches."""

import string
from warnings import warn

import cv2
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np


def extract_characteristic_data(
    signal: np.ndarray,
    samples: list[tuple[slice]],
    filter: callable = lambda x: x,
    show_plot: bool = False,
) -> np.ndarray:
    """Assistant to extract representative colors from input image for given patches.

    Args:
        signal (np.ndarray): input signal, assumed to have the structure of a 2d,
            colored image.
        samples (list of slices): list of 2d regions of interest
        filter (callable): function to preprocess the signal before analysis, e.g.,
            Gaussian filter.
        show_plot (boolean): flag controlling whether plots are displayed.

    Returns:
        np.ndarray: characteristic colors for chosen samples.

    """
    # Init data vector
    data_dim = signal.shape[-1]
    if data_dim not in [1, 3]:
        data_dim = 1
        warn("Implicitly assume that the data is scalar.")
    num_samples = len(samples)  # number of patches
    data_clusters = np.zeros((num_samples, data_dim))

    # Alphabet useful for labeling in plots
    letters = list(string.ascii_uppercase) + list(string.ascii_lowercase)

    # Visualise patches
    if show_plot:
        _, ax = plt.subplots()
        ax.imshow(np.abs(signal))  # visualise data
        ax.set_xlabel("horizontal pixel")
        ax.set_ylabel("vertical pixel")

    # Preprocess signal
    signal = filter(signal).copy()

    # Analyze patches separately
    for i, p in enumerate(samples):
        # Control patch dimension
        assert len(p) == 2, "Patch must be 2d"

        # Cluster analysis for extractin dominant data/colors
        patch = signal[p]
        flat_image = np.reshape(patch, (-1, data_dim))
        pixels = np.float32(flat_image)
        n_colors = 5
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            200,
            0.1,
        )
        flags = cv2.KMEANS_RANDOM_CENTERS
        _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags)
        _, counts = np.unique(labels, return_counts=True)
        data_clusters[i] = palette[np.argmax(counts)]

        # Visualise patches on image
        if show_plot:
            rect = patches.Rectangle(
                (p[1].start, p[0].start),
                p[1].stop - p[1].start,
                p[0].stop - p[0].start,
                linewidth=1,
                edgecolor="w",
                facecolor="none",
            )
            ax.text(
                int(p[1].start + 0.05 * (p[1].stop - p[1].start)),
                int(p[0].start + 0.95 * (p[0].stop - p[0].start)),
                letters[i],
                fontsize=12,
                color="white",
            )
            ax.add_patch(rect)

    if show_plot:
        if data_dim == 3:
            warn("Assuming data is color data and using RGB as axes.")
            c = np.abs(data_clusters)
            plt.figure("Relative dominant colors")
            ax = plt.axes(projection="3d")
            ax.set_xlabel("R")
            ax.set_ylabel("G")
            ax.set_zlabel("B")
            ax.scatter(
                data_clusters[:, 0], data_clusters[:, 1], data_clusters[:, 2], c=c
            )
            for i, c in enumerate(data_clusters):
                ax.text(c[0], c[1], c[2], letters[i])
        plt.show()

    return data_clusters
