from pydantic import BaseModel, Field
from typing import List, Optional, Any
from backend.schemas.nutrition import MacroItem


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    height: float


class PortionInfo(BaseModel):
    estimated_weight_g: float
    serving_text: str
    method: str
    density_g_cm3: float
    food_pixel_area: float
    depth_factor: float


class AnalyzedFoodItem(BaseModel):
    class_id: int
    name: str
    confidence: float
    confidence_pct: int
    box: BoundingBox
    portion: PortionInfo
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    macros: List[MacroItem]


class MealAnalysisResponse(BaseModel):
    success: bool
    total_items_detected: int
    food_title: str
    total_calories: float
    total_weight_g: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    serving_summary: str
    macros: List[MacroItem]
    detected_items: List[AnalyzedFoodItem]
    food_summary: Optional[List[Any]] = None
    verdict: str
    tips: List[str]
    original_image_url: str
    annotated_image_url: str
    inference_config: Optional[Any] = None
    timings: Optional[Any] = None

