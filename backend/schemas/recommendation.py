from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.schemas.nutrition import MacroItem


class MacroSummary(BaseModel):
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


class MealCardItem(BaseModel):
    id: str           # "breakfast", "lunch", "snack", "dinner"
    title: str        # "Breakfast", "Lunch", "Snack", "Dinner"
    food: str         # "Oats Bowl & Banana"
    kcal: int
    time: str         # "8:00 AM"
    macros: Dict[str, float]  # {"p": 12, "c": 48, "f": 8}
    dietary_type: str = "veg"


class ConditionWarning(BaseModel):
    condition: str    # "Diabetes", "PCOS", "Heart Disease"
    severity: str     # "info", "warning", "caution"
    message: str


class DietRecommendationResponse(BaseModel):
    user_goal: str
    health_conditions: List[str]
    daily_target: MacroSummary
    consumed_today: MacroSummary
    remaining_today: MacroSummary
    calorie_progress_pct: int
    protein_progress_pct: int
    carbs_progress_pct: int
    fat_progress_pct: int
    verdict: str
    tips: List[str]
    condition_warnings: List[ConditionWarning]
    suggested_meals: List[MealCardItem]


class LogMealRequest(BaseModel):
    food_name: str
    meal_type: str = "Meal"  # "Breakfast", "Lunch", "Snack", "Dinner"
    image_path: Optional[str] = ""
    annotated_image_path: Optional[str] = ""
    total_calories: float
    total_weight_g: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    serving_description: str = ""
    detected_items: Optional[List[Dict[str, Any]]] = []
    verdict: Optional[str] = ""
    tips: Optional[List[str]] = []


class MealLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    food_name: str
    meal_type: str
    total_calories: float
    total_weight_g: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    serving_description: str
    verdict: str
    created_at: str
    image_url: str
    annotated_image_url: str
