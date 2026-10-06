from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class MacroItem(BaseModel):
    key: str  # "Protein", "Carbs", "Fat", "Fiber"
    value: float
    unit: str = "g"
    pct: int = Field(description="Percentage of daily target or macro energy")
    color: str  # "mint" for protein, "amber" for carbs, "berry" for fat, "sky" for fiber


class FoodNutritionInfo(BaseModel):
    food_id: str
    name: str
    serving_unit: str
    typical_serving_weight_g: float
    category: str
    dietary_type: str
    glycemic_index: str
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    macros: List[MacroItem]
    source: str


class CustomItemCalculation(BaseModel):
    food_name: str
    weight_grams: float


class MealNutritionCalculationRequest(BaseModel):
    items: List[CustomItemCalculation]
    user_daily_calories: Optional[float] = 2000.0


class CalculatedMealItem(BaseModel):
    food_name: str
    weight_grams: float
    serving_description: str
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    macros: List[MacroItem]


class MealNutritionResponse(BaseModel):
    total_calories: float
    total_weight_g: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    serving_summary: str
    macros: List[MacroItem]
    items: List[CalculatedMealItem]
    verdict: str
    tips: List[str]
