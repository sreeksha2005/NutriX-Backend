import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple


class DepthEstimatorService:
    _instance: Optional["DepthEstimatorService"] = None

    def __init__(self):
        print("[DepthEstimator] Initializing Depth Estimation Engine...")

    @classmethod
    def get_instance(cls) -> "DepthEstimatorService":
        if cls._instance is None:
            cls._instance = DepthEstimatorService()
        return cls._instance

    def estimate_depth_map(self, image_bgr: np.ndarray) -> np.ndarray:
        """
        Generates normalized monocular relative depth map where higher values
        correspond to regions closer/raised above the background plane.
        """
        img_gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # 1. Multi-scale Laplacian and Sobel gradient intensity to estimate surface micro-geometry
        grad_x = cv2.Sobel(img_gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(img_gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(grad_x**2 + grad_y**2)

        # 2. Dark channel & color-saturation cues (foreground food is more saturated and textured)
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1].astype(np.float64) / 255.0

        # 3. Distance transform from image center / plate center
        h, w = img_gray.shape
        cy, cx = h / 2.0, w / 2.0
        y_coords, x_coords = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x_coords - cx) ** 2 + (y_coords - cy) ** 2)
        max_dist = np.sqrt(cx**2 + cy**2)
        center_bias = 1.0 - (dist_from_center / max_dist)

        # Combine depth features
        norm_grad = cv2.normalize(gradient_mag, None, 0, 1, cv2.NORM_MINMAX)
        depth_map = (0.45 * norm_grad) + (0.35 * saturation) + (0.20 * center_bias)
        depth_map = cv2.GaussianBlur(depth_map, (9, 9), 0)

        return depth_map

    def get_region_relative_depth(
        self,
        depth_map: np.ndarray,
        bbox: Tuple[int, int, int, int],
        mask: Optional[np.ndarray] = None,
    ) -> float:
        """
        Computes the relative depth / height factor for a segmented food region.
        Returns a scaling coefficient centered around 1.0 (e.g. 0.85 - 1.40).
        """
        x1, y1, x2, y2 = bbox
        h, w = depth_map.shape
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        crop_depth = depth_map[y1:y2, x1:x2]
        if crop_depth.size == 0:
            return 1.0

        if mask is not None and mask.shape == crop_depth.shape:
            fg_depths = crop_depth[mask > 0]
            bg_depths = crop_depth[mask == 0]
            if fg_depths.size > 0:
                mean_fg = float(np.mean(fg_depths))
                mean_bg = float(np.mean(bg_depths)) if bg_depths.size > 0 else 0.5
                relative_elevation = max(0.0, mean_fg - mean_bg)
                # Map to multiplier between 0.85 and 1.35
                depth_factor = 0.90 + (relative_elevation * 0.80)
                return round(float(np.clip(depth_factor, 0.80, 1.40)), 3)

        mean_val = float(np.mean(crop_depth))
        return round(float(np.clip(0.85 + (mean_val * 0.5), 0.80, 1.40)), 3)
