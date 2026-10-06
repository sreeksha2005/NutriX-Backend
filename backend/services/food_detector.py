import uuid
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

from backend.config import (
    YOLO_MODEL_PATH, UPLOAD_DIR,
    CONFIDENCE_THRESHOLD, IOU_THRESHOLD, MAX_IMAGE_PIXELS,
)
from backend.schemas.food import BoundingBox, AnalyzedFoodItem, PortionInfo, MealAnalysisResponse
from backend.schemas.nutrition import MacroItem
from backend.services.portion_estimator import PortionEstimatorService
from backend.services.nutrition_calculator import NutritionCalculatorService

logger = logging.getLogger("nutrix.detector")


class FoodDetectorService:
    _instance: Optional["FoodDetectorService"] = None
    _model: Optional[YOLO] = None

    def __init__(self, model_path: str = YOLO_MODEL_PATH):
        self.model_path = model_path
        self._load_model()
        self.portion_estimator = PortionEstimatorService.get_instance()
        self.nutrition_calculator = NutritionCalculatorService.get_instance()

    def _load_model(self):
        """Loads the trained YOLOv8 model weights."""
        if not Path(self.model_path).exists():
            raise FileNotFoundError(
                f"YOLO model weights not found at: {self.model_path}. "
                "Please check the path in config.py"
            )
        print(f"[FoodDetector] Loading YOLOv8 model from {self.model_path}...")
        self.model = YOLO(self.model_path)
        print(f"[FoodDetector] Model loaded successfully! Classes: {self.model.names}")
        print(f"[FoodDetector] Inference config: conf={CONFIDENCE_THRESHOLD}, iou={IOU_THRESHOLD}")

    @classmethod
    def get_instance(cls) -> "FoodDetectorService":
        if cls._instance is None:
            cls._instance = FoodDetectorService()
        return cls._instance

    def _validate_and_preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """Validates image bytes and returns a cv2 BGR image, resizing if too large."""
        if len(image_bytes) > 20 * 1024 * 1024:  # 20MB hard limit
            raise ValueError("Image file exceeds 20MB size limit.")

        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image file format. Could not decode image.")

        img_h, img_w = img.shape[:2]
        total_pixels = img_h * img_w

        # Downscale very large images to prevent OOM
        if total_pixels > MAX_IMAGE_PIXELS:
            scale = np.sqrt(MAX_IMAGE_PIXELS / total_pixels)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            logger.info(f"Resized large image from {img_w}x{img_h} to {new_w}x{new_h}")

        return img

    def analyze_meal(
        self,
        image_bytes: bytes,
        confidence_threshold: float = None,
        user_daily_calories: float = 2000.0,
    ) -> MealAnalysisResponse:
        """
        Runs the full AI Pipeline:
        1. Image Validation & Preprocessing
        2. YOLOv8 Food Detection (with configurable conf + IoU NMS)
        3. Confidence Filtering
        4. DeepLabV3 Segmentation + MiDaS Depth Portion Estimation
        5. ICMR-NIN Nutrition Calculation & Macro Breakdown
        """
        timings: Dict[str, float] = {}
        pipeline_start = time.perf_counter()

        # Use config default if caller doesn't override
        if confidence_threshold is None:
            confidence_threshold = CONFIDENCE_THRESHOLD

        # --- Step 1: Image Validation & Preprocessing ---
        t0 = time.perf_counter()
        img = self._validate_and_preprocess_image(image_bytes)
        timings["image_preprocessing_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        img_h, img_w = img.shape[:2]
        file_id = str(uuid.uuid4())[:8]
        raw_filename = f"raw_{file_id}.jpg"
        annotated_filename = f"annotated_{file_id}.jpg"

        raw_filepath = UPLOAD_DIR / raw_filename
        annotated_filepath = UPLOAD_DIR / annotated_filename

        # Save original raw image
        cv2.imwrite(str(raw_filepath), img)

        # --- Step 2: YOLO Inference ---
        t0 = time.perf_counter()
        results = self.model.predict(
            source=img,
            conf=confidence_threshold,
            iou=IOU_THRESHOLD,
            save=False,
            verbose=False,
        )
        timings["yolo_inference_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        annotated_img = img.copy()
        analyzed_items: List[AnalyzedFoodItem] = []
        meal_items_for_calc: List[Dict[str, Any]] = []

        color_palette = [
            (56, 180, 74),   # Green
            (235, 120, 30),  # Orange
            (40, 110, 240),  # Blue
            (210, 50, 150),  # Berry
            (20, 180, 230),  # Cyan
        ]

        # --- Step 3 & 4: Confidence Filtering + Portion Estimation ---
        t0 = time.perf_counter()

        if len(results) > 0:
            result = results[0]
            boxes = result.boxes

            # Pre-compute full scene depth map once for efficiency
            depth_map = self.portion_estimator.depth_estimator.estimate_depth_map(img)

            for box in boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                class_name = self.model.names.get(class_id, f"food_{class_id}")

                xyxy = box.xyxy[0].tolist()
                x1, y1, x2, y2 = map(int, xyxy)
                w = x2 - x1
                h = y2 - y1

                # 1. Estimate Portion (Area x Depth x Density -> Grams)
                portion_res = self.portion_estimator.estimate_portion(
                    image_bgr=img,
                    food_name=class_name,
                    bbox=(x1, y1, x2, y2),
                    depth_map=depth_map,
                )
                est_weight = portion_res.estimated_weight_g

                # 2. Calculate Item Nutrition
                item_nutrition = self.nutrition_calculator.calculate_item_macros(
                    food_name=class_name,
                    weight_grams=est_weight,
                    daily_cal_target=user_daily_calories,
                )

                portion_info = PortionInfo(
                    estimated_weight_g=est_weight,
                    serving_text=f"{int(est_weight)}g",
                    method=portion_res.confidence_method,
                    density_g_cm3=portion_res.density_g_cm3,
                    food_pixel_area=portion_res.food_pixel_area,
                    depth_factor=portion_res.depth_factor,
                )

                analyzed_item = AnalyzedFoodItem(
                    class_id=class_id,
                    name=class_name,
                    confidence=round(confidence, 4),
                    confidence_pct=int(round(confidence * 100)),
                    box=BoundingBox(
                        x1=x1, y1=y1, x2=x2, y2=y2, width=w, height=h
                    ),
                    portion=portion_info,
                    calories_kcal=item_nutrition.calories_kcal,
                    protein_g=item_nutrition.protein_g,
                    carbs_g=item_nutrition.carbs_g,
                    fat_g=item_nutrition.fat_g,
                    fiber_g=item_nutrition.fiber_g,
                    macros=item_nutrition.macros,
                )

                analyzed_items.append(analyzed_item)
                meal_items_for_calc.append({
                    "food_name": class_name,
                    "weight_grams": est_weight,
                })

                # Draw bounding box and enhanced nutrition label
                color = color_palette[class_id % len(color_palette)]
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 3)

                label = f"{class_name.capitalize()} {int(confidence * 100)}% ({int(est_weight)}g · {int(item_nutrition.calories_kcal)} kcal)"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                label_y = y1 - 8 if y1 - 8 > th + 5 else y1 + th + 10

                cv2.rectangle(
                    annotated_img,
                    (x1, label_y - th - 5),
                    (x1 + tw + 10, label_y + 5),
                    color,
                    -1,
                )
                cv2.putText(
                    annotated_img,
                    label,
                    (x1 + 5, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

        timings["portion_nutrition_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # Save annotated image
        cv2.imwrite(str(annotated_filepath), annotated_img)

        # --- Step 5: Calculate combined total meal nutrition ---
        t0 = time.perf_counter()
        total_meal = self.nutrition_calculator.calculate_total_meal(
            items=meal_items_for_calc,
            daily_cal_target=user_daily_calories,
        )
        timings["meal_aggregation_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        food_titles = [item.name.capitalize() for item in analyzed_items]
        food_title_str = " + ".join(food_titles) if food_titles else "No Food Detected"

        # Build food_summary: count of each food class detected
        food_counts: Dict[str, int] = {}
        for item in analyzed_items:
            food_counts[item.name] = food_counts.get(item.name, 0) + 1
        food_summary = [{"food": k, "quantity": v} for k, v in food_counts.items()]

        timings["total_pipeline_ms"] = round((time.perf_counter() - pipeline_start) * 1000, 1)

        # Log timing summary
        print(
            f"[FoodDetector] Pipeline timings: "
            f"preprocess={timings['image_preprocessing_ms']}ms, "
            f"yolo={timings['yolo_inference_ms']}ms, "
            f"portion+nutrition={timings['portion_nutrition_ms']}ms, "
            f"aggregation={timings['meal_aggregation_ms']}ms, "
            f"total={timings['total_pipeline_ms']}ms "
            f"| detections={len(analyzed_items)} (conf>={confidence_threshold}, iou={IOU_THRESHOLD})"
        )

        return MealAnalysisResponse(
            success=True,
            total_items_detected=len(analyzed_items),
            food_title=food_title_str,
            total_calories=total_meal.total_calories,
            total_weight_g=total_meal.total_weight_g,
            total_protein_g=total_meal.total_protein_g,
            total_carbs_g=total_meal.total_carbs_g,
            total_fat_g=total_meal.total_fat_g,
            total_fiber_g=total_meal.total_fiber_g,
            serving_summary=total_meal.serving_summary,
            macros=total_meal.macros,
            detected_items=analyzed_items,
            food_summary=food_summary,
            verdict=total_meal.verdict,
            tips=total_meal.tips,
            original_image_url=f"/uploads/{raw_filename}",
            annotated_image_url=f"/uploads/{annotated_filename}",
            inference_config={
                "confidence_threshold": confidence_threshold,
                "iou_threshold": IOU_THRESHOLD,
            },
            timings=timings,
        )
