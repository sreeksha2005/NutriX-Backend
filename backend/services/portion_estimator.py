import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import cv2
import numpy as np

from backend.config import BASE_DIR
from backend.services.segmentation import FoodSegmentationService
from backend.services.depth_estimator import DepthEstimatorService

DENSITY_CONFIG_PATH = BASE_DIR / "data" / "food_density.json"


class PortionEstimationResult:
    def __init__(
        self,
        food_name: str,
        estimated_weight_g: float,
        confidence_method: str,
        food_pixel_area: float,
        depth_factor: float,
        density_g_cm3: float,
        is_fallback: bool = False,
    ):
        self.food_name = food_name
        self.estimated_weight_g = estimated_weight_g
        self.confidence_method = confidence_method
        self.food_pixel_area = food_pixel_area
        self.depth_factor = depth_factor
        self.density_g_cm3 = density_g_cm3
        self.is_fallback = is_fallback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "food_name": self.food_name,
            "estimated_weight_g": self.estimated_weight_g,
            "confidence_method": self.confidence_method,
            "food_pixel_area": self.food_pixel_area,
            "depth_factor": self.depth_factor,
            "density_g_cm3": self.density_g_cm3,
            "is_fallback": self.is_fallback,
        }


class PortionEstimatorService:
    _instance: Optional["PortionEstimatorService"] = None

    def __init__(self, config_path: Path = DENSITY_CONFIG_PATH):
        self.config_path = config_path
        self._load_density_matrix()
        self.segmenter = FoodSegmentationService.get_instance()
        self.depth_estimator = DepthEstimatorService.get_instance()

    def _load_density_matrix(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Food density config not found at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.density_matrix: Dict[str, Any] = json.load(f)
        print(f"[PortionEstimator] Loaded food density calibration matrix ({len(self.density_matrix)} classes).")

    @classmethod
    def get_instance(cls) -> "PortionEstimatorService":
        if cls._instance is None:
            cls._instance = PortionEstimatorService()
        return cls._instance

    def _normalize_food_name(self, food_name: str) -> str:
        cleaned = food_name.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "chapathi": "chapati",
            "roti": "chapati",
            "phulka": "chapati",
            "plain_dosa": "dosa",
            "masala_dosa": "dosa",
            "puri": "poori",
            "cottage_cheese": "paneer",
        }
        return aliases.get(cleaned, cleaned)

    def get_class_params(self, food_name: str) -> Dict[str, Any]:
        norm = self._normalize_food_name(food_name)
        if norm in self.density_matrix:
            return self.density_matrix[norm]
        # Generic defaults
        return {
            "density_g_per_cm3": 0.80,
            "standard_weight_g": 100.0,
            "min_weight_g": 30.0,
            "max_weight_g": 250.0,
            "standard_thickness_cm": 2.0,
            "standard_diameter_cm": 10.0,
            "shape_factor": 0.75,
        }

    def estimate_portion(
        self,
        image_bgr: np.ndarray,
        food_name: str,
        bbox: Tuple[int, int, int, int],  # (x1, y1, x2, y2)
        depth_map: Optional[np.ndarray] = None,
    ) -> PortionEstimationResult:
        """
        Executes multi-stage portion estimation:
        YOLO BBox -> Segmentation Mask Area -> Monocular Depth -> Density -> Mass (grams)
        """
        norm_name = self._normalize_food_name(food_name)
        params = self.get_class_params(norm_name)
        img_h, img_w = image_bgr.shape[:2]
        total_image_pixels = float(img_h * img_w)

        x1, y1, x2, y2 = bbox
        bbox_w = max(1, x2 - x1)
        bbox_h = max(1, y2 - y1)
        bbox_area = float(bbox_w * bbox_h)

        # Baseline calibration scale: standard plate assumed to occupy ~40-60% of frame
        pixel_fraction = bbox_area / total_image_pixels

        try:
            # 1. Semantic / Contour Segmentation
            seg_res = self.segmenter.extract_food_mask(image_bgr, bbox)
            food_pixels = seg_res["food_pixel_area"]
            mask = seg_res["mask"]
            area_ratio = seg_res["area_ratio"]

            # 2. Monocular Relative Depth Estimation
            if depth_map is None:
                depth_map = self.depth_estimator.estimate_depth_map(image_bgr)

            depth_factor = self.depth_estimator.get_region_relative_depth(
                depth_map=depth_map,
                bbox=bbox,
                mask=mask,
            )

            # 3. Geometric Area-to-Weight Calculation
            std_wt = params["standard_weight_g"]
            shape_factor = params.get("shape_factor", 0.75)
            density = params.get("density_g_per_cm3", 0.80)

            # Expected relative pixel occupancy for a standard piece
            # A standard serving piece typically takes ~12-25% of image width in a typical meal photo
            calibrated_size_ratio = np.sqrt(food_pixels / total_image_pixels) / 0.35
            # Dampen extreme zoom variations with square root scaling
            size_multiplier = float(np.clip(np.sqrt(calibrated_size_ratio), 0.70, 1.45))

            # Compute estimated weight: standard_weight * size_scale * depth_scale * area_coverage
            estimated_weight = std_wt * size_multiplier * depth_factor * (area_ratio / shape_factor)

            # Clamp within physiological bounds
            min_wt = params.get("min_weight_g", std_wt * 0.6)
            max_wt = params.get("max_weight_g", std_wt * 2.0)
            final_weight = round(float(np.clip(estimated_weight, min_wt, max_wt)), 1)

            return PortionEstimationResult(
                food_name=norm_name,
                estimated_weight_g=final_weight,
                confidence_method="deeplab_midas_volume",
                food_pixel_area=round(food_pixels, 1),
                depth_factor=round(depth_factor, 3),
                density_g_cm3=density,
                is_fallback=False,
            )

        except Exception as e:
            # Robust fallback: BBox heuristic
            std_wt = params["standard_weight_g"]
            min_wt = params.get("min_weight_g", std_wt * 0.6)
            max_wt = params.get("max_weight_g", std_wt * 2.0)
            density = params.get("density_g_per_cm3", 0.80)

            bbox_ratio = np.sqrt(bbox_area / total_image_pixels) / 0.40
            scale = float(np.clip(np.sqrt(bbox_ratio), 0.75, 1.40))
            fallback_weight = round(float(np.clip(std_wt * scale, min_wt, max_wt)), 1)

            return PortionEstimationResult(
                food_name=norm_name,
                estimated_weight_g=fallback_weight,
                confidence_method="bbox_heuristic_fallback",
                food_pixel_area=bbox_area,
                depth_factor=1.0,
                density_g_cm3=density,
                is_fallback=True,
            )
