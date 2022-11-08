"""
Module providing structures for any general concentration analysis (tracer, co2,
multicomponent, etc. The resulting class is abstract and needs to be tailored
to the specific situation by inheritance.
"""

from pathlib import Path
from typing import Union

import daria


class ConcentrationAnalysisBase(daria.AnalysisBase):
    """Base analysis class providing general tools to perform
    analysis based on daria.ConcentrationAnalysis (and children).
    """

    def _setup_concentration_analysis(
        self,
        concentration_analysis: daria.ConcentrationAnalysis,
        cleaning_filter: Union[str, Path],
        baseline_images: Union[str, Path, list[str], list[Path]],
        update: bool = False,
    ) -> None:
        """
        Wrapper to find cleaning filter of the concentration analysis.

        Args:
            concentration_analysis (daria.ConcentrationAnalysis): concentration analysis
                to be set up.
            cleaning_filter (str or Path): path to cleaning filter array.
            baseline_images (list of str or Path): paths to baseline images.
            update (bool): flag controlling whether the calibration and setup should
                be updated.
        """
        # Set volume information
        # TODO include; after also including self.determine_effective_volumes (abstractmethod).
        #        concentration_analysis.update_volumes(self.effective_volumes)

        # Fetch or generate cleaning filter
        if not update and Path(cleaning_filter).exists():
            concentration_analysis.read_cleaning_filter_from_file(cleaning_filter)
        else:
            # Process baseline images used for setting up the cleaning filter
            if self.processed_baseline_images is None:
                self.processed_baseline_images: list[daria.Image] = [
                    self._read(path) for path in baseline_images
                ]

            # Construct the concentration analysis specific cleaning filter
            concentration_analysis.find_cleaning_filter(self.processed_baseline_images)

            # Store the cleaning filter to file for later reuse.
            concentration_analysis.write_cleaning_filter_to_file(cleaning_filter)
