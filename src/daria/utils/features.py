"""
Class for feature detection.
"""
from typing import Optional

import cv2
import numpy as np


class FeatureDetection:
    """
    Class containing two class methods, once detecting features, and matching features.
    """

    def __init__(self):
        pass

    @classmethod
    def extract_features(
        cls, img: np.ndarray, roi: Optional[tuple] = None, max_features: int = 200
    ) -> tuple:
        """
        Extract features from an image.

        Args:
            img (np.ndarray): image array
            roi (tuple of two slices, optional): region of interest; by default the
                entire image is considered
            max_features (int): maximal number of features to be extracted

        Returns:
            tuple: tuple of
                kps: keypoints of the features; note keypoints come in (col, row),
                    i.e., reversed matrix indexing
                np.ndarray: descriptors of the features
            bool: flag indicating whether features have been found
        """

        # Restrict image to ROI
        img_roi = img[roi] if roi is not None else img

        # Convert to gray color space
        img_gray = cv2.cvtColor(img_roi, cv2.COLOR_RGB2GRAY)

        # Determine matching features; use ORB to detect keypoints
        # and extract (binary) local invariant features
        orb = cv2.ORB_create(max_features)
        (kps, descs) = orb.detectAndCompute(img_gray, None)

        # Check if features valid
        found_features = descs is not None

        return (kps, descs), found_features

    @classmethod
    def match_features(
        cls,
        features_src: tuple,
        features_dst: tuple,
        keep_percent: float = 0.1,
        return_matches: bool = False,
    ) -> tuple:
        """
        Match two sets of features via a homography.

        Args:
            features_src (tuple): source features given as tuple of keypoints and descriptors
            features_dst (tuple): destination features given as tuple of keypoints and
                descriptors
            keep_percent (float): number between 0 and 1 indicating how many features should
                be considered for finding a match; 0 denotes none, while 1 denotes all.
            return_matches (bool): flag controlling whether also the matches are returned,
                which could e.g. be used for plotting

        Returns:
            np.ndarray: homography matrix matching the features
            bool: flag indicating whether procedure has been successful
            matches (optional): matches between features # TODO type
        """
        # Unpack features (keypoints and descriptors)
        kps_src, descs_src = features_src
        kps_dst, descs_dst = features_dst

        # Match features in both images
        method = cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING
        matcher = cv2.DescriptorMatcher_create(method)
        matches = matcher.match(descs_src, descs_dst, None)

        # sort the matches by their distance (the smaller the distance,
        # the "more similar" the features are)
        matches = sorted(matches, key=lambda x: x.distance)

        # keep only the top matches to reduce noise
        have_matched_features = False
        while True:
            keep = int(len(matches) * keep_percent)
            # Apply safety measure increasing the chance to actually
            # find some match
            have_matched_features = keep >= 4
            if have_matched_features:
                break
            else:
                # Increase percentage
                keep_percent *= 1.5
                # Stop process if percentage more thann 100%
                if keep_percent > 1:
                    break

        # Consider the top matches
        matches = matches[:keep]

        # Allocate memory for the keypoints (col, row)-coordinates from the
        # top matches.
        pts_src = np.zeros((len(matches), 2), dtype="float")
        pts_dst = np.zeros((len(matches), 2), dtype="float")

        # Only continue if matching features have been found, and it is at least four;
        # four matches are needed to find a homography.
        if have_matched_features:

            # Loop over the top matches
            for (i, m) in enumerate(matches):
                # Indicate that the two keypoints in the respective images
                # map to each other
                pts_src[i] = kps_src[m.queryIdx].pt
                pts_dst[i] = kps_dst[m.trainIdx].pt

            # compute the homography matrix between the two sets of matched points
            (H, mask) = cv2.findHomography(pts_src, pts_dst, method=cv2.RANSAC)

        if return_matches:
            return (pts_src, pts_dst), have_matched_features, matches
        else:
            return (pts_src, pts_dst), have_matched_features
