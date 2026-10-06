from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional

from backend.schemas.nutrition import MealNutritionCalculationRequest, MealNutritionResponse
from backend.services.nutrition_calculator import NutritionCalculatorService

router = APIRouter(prefix="/api/nutrition", tags=["Nutrition Engine"])


@router.get(
    "/database/all",
    summary="Get all food items in the ICMR-NIN nutrition database",
)
def get_all_nutrition_items():
    service = NutritionCalculatorService.get_instance()
    items = service.get_all_foods()
    return {
        "total_items": len(items),
        "foods": items,
    }


@router.get(
    "/{food_name}",
    summary="Lookup nutrition data for a specific food item",
)
def get_food_nutrition(
    food_name: str,
    weight_grams: Optional[float] = Query(None, description="Optional weight in grams (defaults to standard serving)"),
):
    service = NutritionCalculatorService.get_instance()
    entry = service.get_food_entry(food_name)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food item '{food_name}' not found in database.",
        )

    wt = weight_grams if weight_grams is not None else entry.get("typical_serving_weight_g", 100.0)
    item_calc = service.calculate_item_macros(food_name, wt)

    return {
        "food_id": food_name.lower(),
        "name": entry.get("name", food_name.capitalize()),
        "category": entry.get("category", "general"),
        "dietary_type": entry.get("dietary_type", "veg"),
        "glycemic_index": entry.get("glycemic_index", "medium"),
        "serving_unit": entry.get("serving_unit", "1 serving"),
        "typical_serving_weight_g": entry.get("typical_serving_weight_g", 100.0),
        "source": entry.get("source", "ICMR-NIN IFCT 2017"),
        "per_100g": entry.get("per_100g", {}),
        "calculated_serving": item_calc,
    }


@router.post(
    "/calculate",
    response_model=MealNutritionResponse,
    summary="Calculate total calories and macronutrients for a meal",
)
def calculate_meal_nutrition(req: MealNutritionCalculationRequest):
    service = NutritionCalculatorService.get_instance()
    items_list = [
        {"food_name": item.food_name, "weight_grams": item.weight_grams}
        for item in req.items
    ]
    return service.calculate_total_meal(
        items=items_list,
        daily_cal_target=req.user_daily_calories or 2000.0,
    )
