"""
Module containing class which manages performing a translation based on
a provided pointwise translation map.

"""

import copy
import time
from math import ceil
from typing import Callable

import cv2
import numpy as np

import darsia


class PiecewisePerspectiveTransform:
    """
    Class performing a piecewise perspective transform, applied to a structured grid.
    The final transformation is continuous.

    """

    def __init__(self, **kwargs) -> None:
        """
        Constructor method.

        Stores external inputs as patches.

        Args:
            **kwargs (optional):
                verbosity (int): if larger than 0, statements regarding timings
                are printed.

        """
        # Initialize flag
        self.have_transform = False
        self.verbosity = kwargs.get("verbosity", 0)

    def find_and_warp(
        self,
        patches: darsia.Patches,
        displacement: Callable,
        reverse: bool = False,
    ) -> darsia.Image:
        """
        Continuously transform entire image via patchwise perspective transform.

        Perspective transforms determined by the function evaluation in all
        corners of each patch results in continuous transformations.
        Hence, stiching together the transformed images results in
        an image without overlap and gaps.

        Args:
            patches (darsia.Patches): patched image
            displacement (Callable): relative deformation map; assumed to be continuous
            reverse (bool): flag whether displacement is applied with negative weight

        Returns:
            darsia.Image: transformed image

        """
        # TODO extend to 3d?
        if patches.num_active_spatial_axes != 2:
            raise NotImplementedError

        # Initialize empty image of same type as the original image.
        # Need float for cv2.warpPerspective.
        (h, w) = patches.base.img.shape[:2]
        dtype = patches.base.img.dtype
        transformed_img_new = np.zeros(patches.base.img.shape, dtype=np.float32)

        # Init time tracker
        total_time = 0

        # Loop over all patches in a grid fashion:
        for i in range(patches.num_patches[0]):
            for j in range(patches.num_patches[1]):

                # Determine the pixels of the corners in matrix indexing
                global_corners = patches.global_corners_voxels[i, j]
                local_corners = patches.local_corners_voxels[i, j]

                # Flip axes, since cv2 requires reverse matrix indexing.
                global_corners = np.fliplr(global_corners)
                local_corners = np.fliplr(local_corners)

                # Determine the coordinates after applying the transformation.
                # NOTE: Strangely, the interpolator reshapes the arrays from
                # input to output.
                pts_src = local_corners
                pts_dst = (
                    global_corners
                    + (-1.0 if reverse else 1.0) * displacement(global_corners).T
                )

                # Find effective origin, width and height of the transformed patch.
                # Recall that coordinates are provided in reverse matrix indexing.
                origin_eff = np.array(
                    [max(0, np.min(pts_dst[:, 0])), max(0, np.min(pts_dst[:, 1]))]
                ).astype(np.int32)
                pts_dst_eff = pts_dst - origin_eff
                w_eff = ceil(min(w, np.max(pts_dst[:, 0])) - max(0, origin_eff[0]))
                h_eff = ceil(min(h, np.max(pts_dst[:, 1])) - max(0, origin_eff[1]))

                # Continue with the next patch, if the effective size becomes at most
                # a single pixel.
                if min(h_eff, w_eff) <= 1:
                    continue

                # NOTE: Flip of x and y to row and col.
                roi_eff = (
                    slice(
                        max(0, int(origin_eff[1])), min(h, int(origin_eff[1] + h_eff))
                    ),
                    slice(
                        max(0, int(origin_eff[0])), min(w, int(origin_eff[0] + w_eff))
                    ),
                )
                roi_patch_eff = (
                    slice(0, int(min(origin_eff[1] + h_eff, h) - origin_eff[1])),
                    slice(0, min(origin_eff[0] + w_eff, w) - origin_eff[0]),
                )

                # Find perspective transform mapping src to dst pixels in reverse matrix format
                P_eff = cv2.getPerspectiveTransform(
                    pts_src.astype(np.float32), pts_dst_eff.astype(np.float32)
                )

                # Map patch onto transformed region
                patch_img = patches(i, j).img.astype(np.float32)
                tic = time.time()
                tmp = cv2.warpPerspective(
                    patch_img, P_eff, (w_eff, h_eff), flags=cv2.INTER_LINEAR
                )
                transformed_img_new[roi_eff] += tmp[roi_patch_eff]

                # Update time
                total_time += time.time() - tic

        # Convert to the same data type as the input image
        transformed_img = transformed_img_new.astype(dtype)

        # TODO rm print or use verbosity.
        # print(f"total time: {total}")
        if self.verbosity > 0:
            print(f"total time new: {total_time}")

        # Use same metadata as for the base of the patches
        metadata = copy.copy(patches.base.metadata())
        return darsia.Image(img=transformed_img, **metadata)
