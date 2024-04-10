"""Module containing several utils operating on binary signals.

"""

from __future__ import annotations

import abc
from typing import Callable, Optional, Union

import cv2
import numpy as np
import skimage

import darsia


class BaseCriterion:
    """Abstract criterion class."""

    def bind(self, signal: np.ndarray, unprocessed_signal: np.ndarray) -> None:
        """
        Binding routine, allowing to fix and prepare.

        Args:
            signal (np.ndarray): processed signal
            unprocessed_signal (np.ndarray): unprocessed signal
        """
        self.signal = signal

    @abc.abstractmethod
    def __call__(self, roi) -> np.ndarray:
        """
        Main method, to be overwritten.
        """
        pass


class ValueCriterion(BaseCriterion):
    """
    Criterion checking for absolute maximal values.
    """

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def __call__(self, roi) -> np.ndarray:
        return np.max(self.signal[roi]) > self.threshold


class RelativeValueCriterion(BaseCriterion):
    """
    Criterion checking for relative maximal values.
    """

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def __call__(self, roi) -> np.ndarray:
        return np.max(self.signal[roi]) > self.threshold * np.min(self.signal[roi])


class TransformedValueCriterion(BaseCriterion):
    """
    Criterion checking for absolute maximal values in a transformed
    version of the unprocessed signal.
    """

    def __init__(self, transformation: callable, threshold: float) -> None:
        self.transformation = transformation
        self.threshold = threshold

    def bind(self, signal: np.ndarray, unprocessed_signal: np.ndarray) -> None:
        self.processed_signal = self.transformation(unprocessed_signal)

    def __call__(self, roi) -> np.ndarray:
        return np.max(self.processed_signal[roi]) > self.threshold


class GradientModulusCriterion(BaseCriterion):
    """
    Criterion checking for absolute maximal value of the
    gradient modulus of the signal.
    """

    def __init__(
        self, threshold: Optional[float] = None, key: str = "", **kwargs
    ) -> None:
        self.threshold = threshold

    def bind(self, signal: np.ndarray, unprocessed_signal: np.ndarray) -> None:
        dx = darsia.forward_diff_x(signal)
        dy = darsia.forward_diff_y(signal)
        self.gradient_modulus = np.sqrt(dx**2 + dy**2)

    def __call__(self, roi) -> np.ndarray:
        return np.max(self.gradient_modulus[roi]) > self.threshold


class CombinedCriterion(BaseCriterion):
    """
    General combination of criteria, provided as list.
    """

    def __init__(self, criteria: list[BaseCriterion]) -> None:
        self.criteria = criteria

    def bind(self, signal: np.ndarray, unprocessed_signal) -> None:
        for i in range(len(self.criteria)):
            self.criteria[i].bind(signal, unprocessed_signal)

    def __call__(self, signal: np.ndarray) -> np.ndarray:
        return all([criterion(signal) for criterion in self.criteria])


class BinaryDataSelector:
    """
    Data selector acting on criteria, both volume and contour based.
    """

    def __init__(
        self, criterion: Optional[BaseCriterion] = None, key: str = "", **kwargs
    ) -> None:
        """
        Constructor, initializing criteria. Possibly from keyword arguments.

        Provide the following possibilities:
            * absolute value based
            * relative value based
            * absolute value for signal and transformed unprocessed signal
            * gradient modulus based
        """
        if criterion is not None:
            self.criterion = criterion
        else:
            criterion_key: str = kwargs.get(key + "criterion")
            threshold = kwargs.get(key + "threshold")

            if criterion_key == "value":
                self.criterion = ValueCriterion(threshold)
                self.type = "volume"

            elif criterion_key == "relative value":
                self.criterion = RelativeValueCriterion(threshold)
                self.type = "volume"

            elif criterion_key == "value/value extra color":
                # Value
                value_criterion = ValueCriterion(threshold[0])

                # Value of extra color
                color: Union[str, Callable] = kwargs.get(key + "extra color")
                transformation = darsia.MonochromaticReduction(color=color)
                extra_color_criterion = TransformedValueCriterion(
                    transformation,
                    threshold[1],
                )

                # Combine both
                self.criterion = CombinedCriterion(
                    [value_criterion, extra_color_criterion]
                )
                self.type = "volume"

            elif criterion_key == "gradient modulus":
                self.criterion = GradientModulusCriterion(threshold)
                self.type = "contour"

            else:
                raise ValueError(f"Criterion type {criterion_key} not supported.")

    def __call__(
        self, signal: np.ndarray, mask: np.ndarray, unprocessed_signal: np.ndarray
    ) -> np.ndarray:
        """
        Select from data labeled regions which satisfy some criterion.

        Args:
            signal (np.ndarray): signal
            mask (np.ndarray): mask
            unprocessed_signal (np.ndarray): original signal

        Returns:
            np.ndarray: boolean mask, reevaluated based on criteria.
        """
        # Bind data
        self.criterion.bind(signal, unprocessed_signal)

        # Initialize result
        cleaned_mask = np.zeros_like(mask, dtype=bool)

        # Label the mask
        labels, num_labels = skimage.measure.label(mask, return_num=True)

        # Investigate each labeled region separately; omit label 0, which corresponds
        # to non-marked area.
        for label in range(1, num_labels + 1):

            # Fix one label
            labeled_region = labels == label
            roi = np.logical_and(labeled_region, mask)

            if self.type == "volume":
                # Check the criterion for the subregion
                accept = np.count_nonzero(roi) > 0 and self.criterion(roi)
                cleaned_mask[labeled_region] = accept

            elif self.type == "contour":
                # Determine contour set of labeled region
                contours, _ = cv2.findContours(
                    skimage.img_as_ubyte(labeled_region),
                    cv2.RETR_TREE,
                    cv2.CHAIN_APPROX_SIMPLE,
                )

                # For each part of the contour set, check whether the gradient is sufficiently
                # large at any location
                for c in contours:

                    # Extract coordinates of contours - have to flip columns, since cv2
                    # provides reverse matrix indexing, and also 3 components, with the
                    # second one single dimensioned.
                    c = (c[:, 0, 1], c[:, 0, 0])

                    # Check the criterion for the subregion
                    accept = np.count_nonzero(roi) > 0 and self.criterion(c)
                    cleaned_mask[labeled_region] = accept

        return cleaned_mask
