import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.config import BASE_DIR
from backend.schemas.nutrition import MacroItem, CalculatedMealItem, MealNutritionResponse, FoodNutritionInfo

NUTRITION_DB_PATH = BASE_DIR / "data" / "nutrition_database.json"

# Macro UI styling tokens matching frontend
MACRO_METADATA = {
    "protein": {"key": "Protein", "unit": "g", "color": "mint", "cal_per_g": 4.0},
    "carbs": {"key": "Carbs", "unit": "g", "color": "amber", "cal_per_g": 4.0},
    "fat": {"key": "Fat", "unit": "g", "color": "berry", "cal_per_g": 9.0},
    "fiber": {"key": "Fiber", "unit": "g", "color": "sky", "cal_per_g": 2.0},
}


class NutritionCalculatorService:
    _instance: Optional["NutritionCalculatorService"] = None

    def __init__(self, db_path: Path = NUTRITION_DB_PATH):
        self.db_path = db_path
        self._load_database()

    def _load_database(self):
        if not self.db_path.exists():
            raise FileNotFoundError(f"Nutrition database not found at {self.db_path}")
        with open(self.db_path, "r", encoding="utf-8") as f:
            self.database: Dict[str, Any] = json.load(f)
        print(f"[NutritionCalculator] Loaded {len(self.database)} food items from database.")

    @classmethod
    def get_instance(cls) -> "NutritionCalculatorService":
        if cls._instance is None:
            cls._instance = NutritionCalculatorService()
        return cls._instance

    def _normalize_name(self, food_name: str) -> str:
        """Normalizes and maps aliases to standard database keys."""
        cleaned = food_name.strip().lower().replace("-", "_").replace(" ", "_")
        alias_map = {
            "chapathi": "chapati",
            "roti": "chapati",
            "phulka": "chapati",
            "plain_dosa": "dosa",
            "masala_dosa": "dosa",
            "puri": "poori",
            "cottage_cheese": "paneer",
            "white_rice": "rice",
            "steamed_rice": "rice",
            "chana_masala": "chole",
            "kidney_beans": "rajma",
            "yogurt": "curd",
            "chaas": "buttermilk",
        }
        return alias_map.get(cleaned, cleaned)

    def get_food_entry(self, food_name: str) -> Optional[Dict[str, Any]]:
        norm = self._normalize_name(food_name)
        if norm in self.database:
            return self.database[norm]
        # Partial search
        for key, val in self.database.items():
            if norm in key or key in norm:
                return val
        return None

    def get_all_foods(self) -> List[Dict[str, Any]]:
        results = []
        for key, item in self.database.items():
            results.append({
                "food_id": key,
                "name": item.get("name", key.capitalize()),
                "category": item.get("category", "general"),
                "dietary_type": item.get("dietary_type", "veg"),
                "serving_unit": item.get("serving_unit", "1 serving"),
                "typical_serving_weight_g": item.get("typical_serving_weight_g", 100),
                "calories_per_100g": item.get("per_100g", {}).get("calories_kcal", 0),
            })
        return results

    def calculate_item_macros(
        self,
        food_name: str,
        weight_grams: float,
        daily_cal_target: float = 2000.0,
    ) -> CalculatedMealItem:
        entry = self.get_food_entry(food_name)
        display_name = entry.get("name", food_name.capitalize()) if entry else food_name.capitalize()
        serving_unit = entry.get("serving_unit", f"{int(weight_grams)}g") if entry else f"{int(weight_grams)}g"

        if not entry:
            # Fallback approximate values if unlisted (standard 150 kcal/100g)
            per_100g = {"calories_kcal": 150.0, "protein_g": 5.0, "carbs_g": 20.0, "fat_g": 5.0, "fiber_g": 2.0}
        else:
            per_100g = entry["per_100g"]

        factor = weight_grams / 100.0
        cal = round(per_100g.get("calories_kcal", 0.0) * factor, 1)
        prot = round(per_100g.get("protein_g", 0.0) * factor, 1)
        carbs = round(per_100g.get("carbs_g", 0.0) * factor, 1)
        fat = round(per_100g.get("fat_g", 0.0) * factor, 1)
        fiber = round(per_100g.get("fiber_g", 0.0) * factor, 1)

        # Build UI Macro items with percentages
        total_macro_cals = max(cal, 1.0)
        macros = [
            MacroItem(
                key="Protein",
                value=prot,
                unit="g",
                pct=min(100, int(round((prot * 4.0 / total_macro_cals) * 100))),
                color="mint",
            ),
            MacroItem(
                key="Carbs",
                value=carbs,
                unit="g",
                pct=min(100, int(round((carbs * 4.0 / total_macro_cals) * 100))),
                color="amber",
            ),
            MacroItem(
                key="Fat",
                value=fat,
                unit="g",
                pct=min(100, int(round((fat * 9.0 / total_macro_cals) * 100))),
                color="berry",
            ),
            MacroItem(
                key="Fiber",
                value=fiber,
                unit="g",
                pct=min(100, int(round((fiber / 30.0) * 100))),
                color="sky",
            ),
        ]

        return CalculatedMealItem(
            food_name=display_name,
            weight_grams=round(weight_grams, 1),
            serving_description=f"{serving_unit} · {int(weight_grams)} g",
            calories_kcal=cal,
            protein_g=prot,
            carbs_g=carbs,
            fat_g=fat,
            fiber_g=fiber,
            macros=macros,
        )

    def calculate_total_meal(
        self,
        items: List[Dict[str, Any]],  # [{"food_name": "idli", "weight_grams": 90}]
        daily_cal_target: float = 2000.0,
    ) -> MealNutritionResponse:
        calculated_items: List[CalculatedMealItem] = []
        tot_cal = 0.0
        tot_wt = 0.0
        tot_p = 0.0
        tot_c = 0.0
        tot_f = 0.0
        tot_fib = 0.0

        for it in items:
            name = it.get("food_name", "food")
            wt = float(it.get("weight_grams", 100.0))
            calc = self.calculate_item_macros(name, wt, daily_cal_target)
            calculated_items.append(calc)

            tot_cal += calc.calories_kcal
            tot_wt += calc.weight_grams
            tot_p += calc.protein_g
            tot_c += calc.carbs_g
            tot_f += calc.fat_g
            tot_fib += calc.fiber_g

        tot_cal = round(tot_cal, 1)
        tot_wt = round(tot_wt, 1)
        tot_p = round(tot_p, 1)
        tot_c = round(tot_c, 1)
        tot_f = round(tot_f, 1)
        tot_fib = round(tot_fib, 1)

        # Macro percentage split
        total_macro_energy = max((tot_p * 4.0) + (tot_c * 4.0) + (tot_f * 9.0), 1.0)
        p_pct = min(100, int(round((tot_p * 4.0 / total_macro_energy) * 100)))
        c_pct = min(100, int(round((tot_c * 4.0 / total_macro_energy) * 100)))
        f_pct = min(100, int(round((tot_f * 9.0 / total_macro_energy) * 100)))
        fib_pct = min(100, int(round((tot_fib / 30.0) * 100)))

        meal_macros = [
            MacroItem(key="Protein", value=tot_p, unit="g", pct=p_pct, color="mint"),
            MacroItem(key="Carbs", value=tot_c, unit="g", pct=c_pct, color="amber"),
            MacroItem(key="Fat", value=tot_f, unit="g", pct=f_pct, color="berry"),
            MacroItem(key="Fiber", value=tot_fib, unit="g", pct=fib_pct, color="sky"),
        ]

        # Generate summary description
        names_list = [ci.food_name for ci in calculated_items]
        summary_title = " + ".join(names_list) if names_list else "Meal"
        serving_summary = f"{len(calculated_items)} items · {int(tot_wt)} g"

        # Generate verdict and tips
        verdict, tips = self._generate_preliminary_verdict_and_tips(tot_p, tot_c, tot_f, tot_fib, names_list)

        return MealNutritionResponse(
            total_calories=tot_cal,
            total_weight_g=tot_wt,
            total_protein_g=tot_p,
            total_carbs_g=tot_c,
            total_fat_g=tot_f,
            total_fiber_g=tot_fib,
            serving_summary=f"{summary_title} ({serving_summary})",
            macros=meal_macros,
            items=calculated_items,
            verdict=verdict,
            tips=tips,
        )

    def _generate_preliminary_verdict_and_tips(
        self, p: float, c: float, f: float, fib: float, foods: List[str]
    ) -> (str, List[str]):
        tips = []
        if p >= 20.0:
            verdict = "Excellent high-protein meal — supports muscle recovery and satiety."
        elif c > 60.0 and p < 10.0:
            verdict = "Carb-dense meal. Consider adding a protein source like paneer, dal, or curd."
        elif f > 25.0:
            verdict = "Higher fat content detected. Balance with lighter sides for the next meal."
        else:
            verdict = "Well-balanced meal with moderate macronutrient distribution."

        # Contextual tips
        if fib < 3.0:
            tips.append("Add a side of green cucumber/tomato salad to increase dietary fiber.")
        if p < 15.0:
            tips.append("Pair with a bowl of curd or buttermilk to boost protein and gut-healthy probiotics.")
        if any("poori" in food.lower() for food in foods):
            tips.append("Poori is deep-fried; keep serving to 2 pieces to manage dietary fats.")
        if any("paneer" in food.lower() for food in foods):
            tips.append("Paneer provides rich calcium and high biological value protein.")

        if not tips:
            tips.append("Stay hydrated! Aim to drink 300ml of water 30 minutes after your meal.")

        return verdict, tips
