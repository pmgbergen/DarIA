"""Preset for a standard FluidFlower analysis pipeline.

This preset is designed for a simple tabletop setup with a dominating sand layer.
It includes the following steps:
1. Shape correction: drift and curvature correction
2. Segmentation: segmentation of the image
3. Color correction: illumination and color correction

The setup method is used to define the tabletop based on characteristic input images.
The read_image method is used to read an image and apply the corrections.
The save and load methods are used to save and load the tabletop.

Modifications to the pipeline can be made by changing the setup method or by adding
additional methods. The expert_knowledge method can be used to apply expert knowledge
to the image after preprocessing.

"""

from pathlib import Path
from typing import Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
import skimage

import darsia


class SimpleFluidFlower:
    def __init__(
        self,
        baseline: Path,
        active_corrections: list[
            Literal[
                "type", "drift", "curvature", "illumination", "relative-color", "color"
            ]
        ] = [
            "type",
            "drift",
            "curvature",
            "relative-color",
            "color",
        ],
        debug: bool = False,
    ) -> None:
        """Constructor for SimpleFluidFlower.

        The correction routines assume a simple setup (e.g., no strong curvature) and
        at least one dominating sand layer spreading the domain.

        Args:
            baseline (Path): path to baseline image
            debug (bool): flag for debugging

        """
        self.raw_baseline = darsia.imread(baseline)
        """Baseline image for the tabletop without any corrections."""

        self.reference_date = self.raw_baseline.date
        """Reference date of experiment."""

        self.corrections = []
        """List of corrections to be applied to the images."""

        self.drift_config = {}
        """Configuration for drift correction."""

        self.curvature_config = {}
        """Configuration for curvature correction."""

        self.debug = debug
        """Flag for debugging."""

        self.active_type_correction = "type" in active_corrections
        """Flag for type correction."""

        self.active_drift_correction = "drift" in active_corrections
        """Flag for drift correction."""

        self.active_curvature_correction = "curvature" in active_corrections
        """Flag for curvature correction."""

        self.active_relative_color_correction = "relative-color" in active_corrections
        """Flag for relative color correction."""

        self.active_illumination_correction = "illumination" in active_corrections
        """Flag for illumination correction."""

        self.active_color_correction = "color" in active_corrections
        """Flag for color correction."""

    def setup(
        self,
        specs: dict,
        segmentation: Optional[Path] = None,
        curvature_options: Optional[dict] = None,
        relative_color_options: Optional[dict] = None,
        illumination_options: Optional[dict] = None,
    ) -> None:
        """Setup Table top based on characteristic input image (preferably the baseline).

        Args:
            specs (dict): specifications of the FluidFlower, includes:
                - width (float): width of the ROI
                - height (float): height of the ROI
                - depth (float): depth of the porous medium
                - porosity (float): porosity of the porous medium
                - colorchecker_position (str): position of the color checker
            segmentation (Path): path to segmentation image
            curvature_options (dict): options for curvature correction, includes:
                - roi (Path): path to image with ROI
                - roi_mode (str): mode for ROI selection
                - roi_color (list[float]): color of the ROI, only used in automatic mode
            relative_color_options (dict): options for relative color correction, includes:
                - images (list[Path]): list of paths to images
            illumination_options (dict): options for illumination correction, includes:
                - illumination_mode (str): mode for illumination

        """

        # Specs of ROI
        self.width = specs.get("width", 0.92)
        self.height = specs.get("height", 0.55)
        self.depth = specs.get("depth", 0.012)
        self.porosity = specs.get("porosity", 0.44)
        self.colorchecker_position = specs.get("colorchecker_position", "upper_right")

        # ! ---- INITIALIZATION ----
        self.corrections = []
        self.baseline = self.raw_baseline.copy()

        # ! ---- SETUP TYPE CORRECTION/CONVERSION ----
        if self.active_type_correction:
            self.type_conversion = darsia.TypeCorrection(np.float64)
            self.corrections.append(self.type_conversion)
            self.baseline = self.type_conversion(self.baseline)

        # ! ---- SETUP SHAPE CORRECTION ----

        if self.active_drift_correction:
            self.drift_correction = self.setup_drift_correction()
            self.corrections.append(self.drift_correction)
            self.baseline = self.drift_correction(self.baseline)

        if self.active_curvature_correction:
            assert curvature_options is not None
            if "cache" in curvature_options:
                # Read from cache
                self.curvature_correction = darsia.CurvatureCorrection()
                self.curvature_correction.load(
                    curvature_options["cache"] / Path("curvature.npz")
                )
            else:
                # Build from scratch
                roi = curvature_options["roi"]
                roi_mode = curvature_options.get("roi_mode", "interactive")
                roi_color = curvature_options.get("roi_color", None)
                self.curvature_correction = self.setup_curvature_correction(
                    roi, roi_mode, roi_color
                )
            self.corrections.append(self.curvature_correction)
            self.baseline = self.curvature_correction(self.baseline)

        # ! ---- SETUP RELATIVE COLOR CORRECTION ----
        if self.active_relative_color_correction:
            assert relative_color_options is not None
            relative_color_images = []
            for path in relative_color_options.pop("images"):
                img = darsia.imread(path)
                for correction in self.corrections:
                    img = correction(img)
                relative_color_images.append(img)
            self.relative_color_correction = darsia.RelativeColorCorrection(
                self.baseline, relative_color_images, relative_color_options
            )
            self.corrections.append(self.relative_color_correction)
            self.baseline = self.relative_color_correction(self.baseline)

        # ! ---- SETUP SEGMENTATION ----

        if segmentation is None:
            self.labels = darsia.ones_like(self.baseline, dtype=np.uint8)
        else:
            self.labels = self.setup_segmentation(segmentation)

        # ! ---- SETUP ILLUMINATION CORRECTION ----
        if self.active_illumination_correction:
            assert illumination_options is not None
            illumination_mode = illumination_options.get(
                "illumination_mode", "automatic"
            )
            self.illumination_correction = self.setup_illumination_correction(
                illumination_mode
            )
            self.corrections.append(self.illumination_correction)

        # ! ---- SETUP COLOR CORRECTION ----
        if self.active_color_correction:
            self.color_correction = self.setup_color_correction()
            self.corrections.append(self.color_correction)

        # ! ---- BASELINE ----

        self.baseline = self.raw_baseline.copy()
        for correction in self.corrections:
            self.baseline = correction(self.baseline)
        self.expert_knowledge(self.baseline)

        # ! ---- GEOMETRY ----

        shape_meta = self.baseline.shape_metadata()
        self.geometry = darsia.ExtrudedPorousGeometry(
            depth=self.depth, porosity=self.porosity, **shape_meta
        )

    def setup_drift_correction(
        self,
    ) -> darsia.DriftCorrection:
        """Setup drift correction based on color checker.

        Returns:
            DriftCorrection: drift_correction

        """

        # Define translation correction object based on color checker
        _, cc_voxels = darsia.find_colorchecker(
            self.raw_baseline, self.colorchecker_position
        )
        self.drift_config = {"roi": cc_voxels}
        drift_correction = darsia.DriftCorrection(
            self.raw_baseline, config=self.drift_config
        )
        return drift_correction

    def setup_curvature_correction(
        self,
        roi: Path,
        roi_mode: Literal["interactive", "automatic"],
        roi_color: Optional[list[float]] = None,
    ) -> darsia.CurvatureCorrection:
        """Setup shape correction based on provided images.

        Args:
            roi (Path): path to image with ROI
            roi_mode (Literal["interactive", "automatic"]): mode for ROI selection
            roi_color (Optional[list[float]]): color of the ROI, only used in automatic mode

        Returns:
            CurvatureCorrection: curvature_correction

        """

        # Read auxiliary images for calibration - make sure they are of the same size
        roi_image = darsia.resize(
            darsia.imread(roi),
            ref_image=self.raw_baseline,
        )

        # Define  Restrict to region with frame
        crop_assistant = darsia.CropAssistant(
            roi_image, width=self.width, height=self.height
        )
        if roi_mode == "interactive":
            # Generate curvature config from image using interactive mode
            self.curvature_config = crop_assistant()
        elif roi_mode == "automatic":
            # Generate curvature config from marked image
            self.curvature_config = crop_assistant.from_image(color=roi_color)
            # Close current plot (internally opened in the assistant)
            plt.close()
        else:
            raise ValueError(f"Unknown roi_mode: {roi_mode}")
        curvature_correction = darsia.CurvatureCorrection(config=self.curvature_config)
        return curvature_correction

    def setup_illumination_correction(
        self,
        illumination_mode: Literal["automatic", "interactive"] = "automatic",
    ) -> darsia.IlluminationCorrection:
        """Setup color correction based on color checker.

        Args:
            illumination_mode (Literal["automatic", "interactive"]): mode for illumination

        Returns:
            IlluminationCorrection: illumination_correction

        """
        # Define illumination gradient correction by estimating the lightness on distributed
        # samples. Use random samples in main reservoir.
        # Define main reservoir as the label with largest count
        largest_label = np.argmax(np.bincount(self.labels.img.flatten()))
        mask = self.labels.img == largest_label

        # Find random patches, restricted to the masked regions
        width = 50
        if illumination_mode == "interactive":
            sample_assistant = darsia.BoxSelectionAssistant(self.baseline, width=width)
            samples = sample_assistant()
        else:
            num_patches = 10
            samples = darsia.random_patches(mask, width=width, num_patches=num_patches)

        # Find sample in the center
        # TODO

        # Determine illumination correction based on inputs
        illumination_correction = darsia.IlluminationCorrection()
        illumination_correction.setup(
            self.baseline,
            samples,
            ref_sample=-1,
            filter=lambda x: skimage.filters.gaussian(x, sigma=200),
            colorspace="hsl-scalar",
            interpolation="illumination",
            show_plot=False,
        )

        return illumination_correction

    def setup_color_correction(
        self,
    ) -> darsia.ColorCorrection:
        """Setup color correction based on color checker.

        Returns:
            ColorCorrection: color_correction

        """
        # Define color correction object - target here the same colors as in the original
        # image (modulo curvature correction)
        colorchecker, cc_aligned_voxels = darsia.find_colorchecker(
            self.baseline, self.colorchecker_position
        )
        self.color_config = {
            "colorchecker": colorchecker,
            "roi": cc_aligned_voxels,
            "clip": False,
        }
        color_correction = darsia.ColorCorrection(config=self.color_config)

        return color_correction

    def setup_segmentation(self, segmentation: Path) -> darsia.Image:
        """Setup segmentation based on provided image.

        Args:
            segmentation (Path): path to segmentation image

        Returns:
            darsia.Labels: labels object

        """
        segmentation_image = darsia.resize(
            darsia.imread(segmentation),
            ref_image=self.raw_baseline,
            interpolation="inter_nearest",
        )
        segmentation_image = self.curvature_correction(segmentation_image)

        # Define geometric segmentation using assistant
        assistant = darsia.LabelsAssistant(
            background=segmentation_image, verbosity=self.debug
        )
        labels = assistant()

        return labels

    def set_corrections(self) -> None:
        """Set corrections based on configuration."""

        if self.drift_config:
            self.drift_correction = darsia.DriftCorrection(
                self.raw_baseline, config=self.drift_config
            )

        if self.curvature_config:
            self.curvature_correction = darsia.CurvatureCorrection(
                config=self.curvature_config
            )

        if self.color_config:
            self.color_correction = darsia.ColorCorrection(config=self.color_config)

    def activate_corrections(self, corrections: list[str]) -> None:
        """Activate corrections based on input list and update baseline.

        Args:
            corrections (list[str]): list of corrections to activate; expected values are
                "drift", "curvature", "illumination", "color"

        """
        # Update corrections
        self.corrections = []
        if "type" in corrections and hasattr(self, "type_conversion"):
            self.corrections.append(self.type_conversion)
        if "drift" in corrections and hasattr(self, "drift_correction"):
            self.corrections.append(self.drift_correction)
        if "curvature" in corrections and hasattr(self, "curvature_correction"):
            self.corrections.append(self.curvature_correction)
        if "relative-color" in corrections and hasattr(
            self, "relative_color_correction"
        ):
            self.corrections.append(self.relative_color_correction)
        if "illumination" in corrections and hasattr(self, "illumination_correction"):
            self.corrections.append(self.illumination_correction)
        if "color" in corrections and hasattr(self, "color_correction"):
            self.corrections.append(self.color_correction)

        # Update baseline
        self.baseline = self.raw_baseline.copy()
        for correction in self.corrections:
            self.baseline = correction(self.baseline)
        self.expert_knowledge(self.baseline)

    def expert_knowledge(self, img: darsia.Image) -> None:
        """Possibility to apply expert knowledge to the image after preprocessing.

        Args:
            img (np.ndarray): image array

        """
        ...

    def read_image(self, path: Path) -> darsia.Image:
        """Read image and apply corrections.

        Args:
            path (Path): path to image

        Returns:
            darsia.Image: image object

        """

        # Read image from file and apply corrections
        img = darsia.imread(
            path, transformations=self.corrections, reference_date=self.reference_date
        )

        # Deactivate water zone
        self.expert_knowledge(img)

        return img

    # ! ---- I/O ----

    def save(self, folder: Path) -> None:
        """Save the tabletop to a folder.

        Args:
            folder (Path): path to folder

        """
        # Make sure folder exists
        folder.mkdir(parents=True, exist_ok=True)

        # # Save baseline
        # self.baseline.save(folder / Path("baseline.npz"))

        # Save corrections
        if self.active_drift_correction:
            self.drift_correction.save(folder / Path("drift.npz"))
        if self.active_curvature_correction:
            self.curvature_correction.save(folder / Path("curvature.npz"))
        if self.active_relative_color_correction:
            self.relative_color_correction.save(folder / Path("relative_color.npz"))
        if self.active_illumination_correction:
            self.illumination_correction.save(folder / Path("illumination.npz"))
        if self.active_color_correction:
            self.color_correction.save(folder / Path("color.npz"))

        # Save segmentation
        self.labels.save(folder / Path("labels.npz"))

        # Save specs
        specs = {
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "porosity": self.porosity,
        }
        np.savez(folder / Path("specs.npz"), specs=specs)
        print(f"Specs saved to {folder / Path('specs.npz')}.")

        print(f"Tabletop saved to {folder}.")

    def load(self, folder: Path) -> None:

        # Load specs
        specs = np.load(folder / Path("specs.npz"), allow_pickle=True)["specs"].item()
        self.width = specs["width"]
        self.height = specs["height"]
        self.depth = specs["depth"]
        self.porosity = specs["porosity"]

        # Load baseline
        self.reference_date = self.raw_baseline.date
        self.baseline = self.raw_baseline.copy()

        # Load corrections
        self.corrections = []

        if self.active_type_correction:
            self.type_conversion = darsia.TypeCorrection(np.float64)
            self.corrections.append(self.type_conversion)

        if self.active_drift_correction:
            self.drift_correction = darsia.DriftCorrection(self.raw_baseline)
            self.drift_correction.load(folder / Path("drift.npz"))
            self.corrections.append(self.drift_correction)
            self.baseline = self.drift_correction(self.baseline)

        if self.active_curvature_correction:
            self.curvature_correction = darsia.CurvatureCorrection()
            self.curvature_correction.load(folder / Path("curvature.npz"))
            self.corrections.append(self.curvature_correction)
            self.baseline = self.curvature_correction(self.baseline)

        if self.active_relative_color_correction:
            self.relative_color_correction = darsia.RelativeColorCorrection(
                self.baseline
            )
            self.relative_color_correction.load(folder / Path("relative_color.npz"))
            self.corrections.append(self.relative_color_correction)
            self.baseline = self.relative_color_correction(self.baseline)

        if self.active_illumination_correction:
            self.illumination_correction = darsia.IlluminationCorrection()
            self.illumination_correction.load(folder / Path("illumination.npz"))
            self.corrections.append(self.illumination_correction)
            self.baseline = self.illumination_correction(self.baseline)

        if self.active_color_correction:
            self.color_correction = darsia.ColorCorrection()
            self.color_correction.load(folder / Path("color.npz"))
            self.corrections.append(self.color_correction)
            self.baseline = self.color_correction(self.baseline)

        # Load segmentation
        if (folder / Path("labels.npz")).exists():
            self.labels = darsia.imread(folder / Path("labels.npz"))
        else:
            self.labels = darsia.ones_like(self.baseline, dtype=np.uint8)

        # Apply expert knowledge
        self.expert_knowledge(self.baseline)

        # Load geometry
        shape_meta = self.baseline.shape_metadata()
        self.geometry = darsia.ExtrudedPorousGeometry(
            depth=self.depth, porosity=self.porosity, **shape_meta
        )
