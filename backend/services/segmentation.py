
import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional


class FoodSegmentationService:
    _instance: Optional["FoodSegmentationService"] = None

    def __init__(self):
        self._init_deeplab()

    def _init_deeplab(self):
        """Disable unused DeepLabV3 to reduce RAM usage."""
        self.device = "cpu"
        self.model = None
        self.transforms = None
        print(
            "[FoodSegmentation] DeepLabV3 disabled; "
            "using OpenCV GrabCut and Adaptive Contour engine."
        )

    @classmethod
    def get_instance(cls) -> "FoodSegmentationService":
        if cls._instance is None:
            cls._instance = FoodSegmentationService()
        return cls._instance

    def extract_food_mask(
        self,
        image_bgr: np.ndarray,
        bbox: Tuple[int, int, int, int],
    ) -> Dict[str, Any]:
        """
        Extracts a binary segmentation mask for the food item inside bbox.

        Returns mask, food_pixel_area, bbox_pixel_area, area_ratio,
        aspect_ratio, and crop.
        """
        img_h, img_w = image_bgr.shape[:2]
        x1, y1, x2, y2 = bbox

        # Keep bounding box coordinates inside the image.
        x1 = max(0, min(x1, img_w - 1))
        y1 = max(0, min(y1, img_h - 1))
        x2 = max(x1 + 1, min(x2, img_w))
        y2 = max(y1 + 1, min(y2, img_h))

        crop = image_bgr[y1:y2, x1:x2]
        crop_h, crop_w = crop.shape[:2]
        bbox_area = float(crop_h * crop_w)

        # Fallback for very small crops.
        if crop_h < 10 or crop_w < 10:
            mask = np.ones((crop_h, crop_w), dtype=np.uint8) * 255
            return {
                "mask": mask,
                "food_pixel_area": bbox_area,
                "bbox_pixel_area": bbox_area,
                "area_ratio": 1.0,
                "aspect_ratio": crop_w / max(crop_h, 1),
                "crop": crop,
            }

        # OpenCV GrabCut segmentation.
        mask = np.zeros(crop.shape[:2], np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        margin_x = max(2, int(crop_w * 0.05))
        margin_y = max(2, int(crop_h * 0.05))

        rect = (
            margin_x,
            margin_y,
            crop_w - (2 * margin_x),
            crop_h - (2 * margin_y),
        )

        try:
            cv2.grabCut(
                crop,
                mask,
                rect,
                bgd_model,
                fgd_model,
                iterCount=3,
                mode=cv2.GC_INIT_WITH_RECT,
            )

            binary_mask = np.where(
                (mask == 2) | (mask == 0), 0, 255
            ).astype("uint8")

        except Exception as e:
            print(f"[FoodSegmentation] GrabCut fallback: {e}")

            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)

            _, binary_mask = cv2.threshold(
                blur,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )

        # Smooth the segmentation mask.
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (5, 5)
        )

        binary_mask = cv2.morphologyEx(
            binary_mask, cv2.MORPH_CLOSE, kernel
        )
        binary_mask = cv2.morphologyEx(
            binary_mask, cv2.MORPH_OPEN, kernel
        )

        food_pixels = int(np.count_nonzero(binary_mask))

        # Use an elliptical mask if segmentation finds too few pixels.
        if food_pixels < 0.10 * bbox_area:
            binary_mask = np.zeros(
                (crop_h, crop_w), dtype=np.uint8
            )

            cv2.ellipse(
                binary_mask,
                (crop_w // 2, crop_h // 2),
                (
                    max(1, crop_w // 2 - margin_x),
                    max(1, crop_h // 2 - margin_y),
                ),
                0,
                0,
                360,
                255,
                -1,
            )

            food_pixels = int(np.count_nonzero(binary_mask))

        return {
            "mask": binary_mask,
            "food_pixel_area": float(food_pixels),
            "bbox_pixel_area": bbox_area,
            "area_ratio": round(food_pixels / bbox_area, 3),
            "aspect_ratio": round(crop_w / max(crop_h, 1), 3),
            "crop": crop,
        }
