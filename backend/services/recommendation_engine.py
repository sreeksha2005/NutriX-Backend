from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.models.user import HealthProfile, MealLog
from backend.schemas.recommendation import (
    MacroSummary,
    MealCardItem,
    ConditionWarning,
    DietRecommendationResponse,
)


class RecommendationEngine:
    _instance: Optional["RecommendationEngine"] = None

    @classmethod
    def get_instance(cls) -> "RecommendationEngine":
        if cls._instance is None:
            cls._instance = RecommendationEngine()
        return cls._instance

    def generate_recommendation(
        self,
        profile: HealthProfile,
        consumed_today: Dict[str, float],  # {"kcal": x, "protein_g": y, "carbs_g": z, "fat_g": a, "fiber_g": b}
        current_meal: Optional[Dict[str, Any]] = None,
    ) -> DietRecommendationResponse:
        """
        Generates comprehensive personalized dietary recommendations combining:
        - Mifflin-St Jeor TDEE & macro targets
        - Daily consumed vs remaining budget
        - Goal-specific feedback (Weight Loss / Muscle Gain / Stay Fit)
        - Condition-specific clinical rules (Diabetes, PCOS, Heart Disease)
        - Structured daily meal plan suggestions
        """
        # 1. Target values from profile
        target_kcal = float(profile.target_calories or 2000.0)
        target_p = float(profile.target_protein_g or 75.0)
        target_c = float(profile.target_carbs_g or 250.0)
        target_f = float(profile.target_fat_g or 55.0)
        target_fib = float(profile.target_fiber_g or 30.0)

        # 2. Consumed today
        c_kcal = float(consumed_today.get("kcal", 0.0))
        c_p = float(consumed_today.get("protein_g", 0.0))
        c_c = float(consumed_today.get("carbs_g", 0.0))
        c_f = float(consumed_today.get("fat_g", 0.0))
        c_fib = float(consumed_today.get("fiber_g", 0.0))

        # 3. Remaining budget
        r_kcal = max(0.0, target_kcal - c_kcal)
        r_p = max(0.0, target_p - c_p)
        r_c = max(0.0, target_c - c_c)
        r_f = max(0.0, target_f - c_f)
        r_fib = max(0.0, target_fib - c_fib)

        # Progress percentages
        pct_cal = min(100, int(round((c_kcal / max(target_kcal, 1.0)) * 100)))
        pct_p = min(100, int(round((c_p / max(target_p, 1.0)) * 100)))
        pct_c = min(100, int(round((c_c / max(target_c, 1.0)) * 100)))
        pct_f = min(100, int(round((c_f / max(target_f, 1.0)) * 100)))

        # 4. Process Health Conditions & Clinical Warnings
        conditions_str = profile.health_conditions or "None"
        conditions_list = [c.strip() for c in conditions_str.split(",") if c.strip() and c.strip().lower() != "none"]
        warnings: List[ConditionWarning] = []
        tips: List[str] = []

        conditions_lower = conditions_str.lower()

        # Clinical Condition Checks
        if "diabetes" in conditions_lower:
            warnings.append(
                ConditionWarning(
                    condition="Diabetes Management",
                    severity="warning",
                    message="Keep glycemic load low: prioritize whole grains, legumes, and high-fiber foods over refined carbs.",
                )
            )
            tips.append("Add a tablespoon of soaked chia or fenugreek (methi) seeds before meals to stabilize glucose response.")
            tips.append("Substitute polished white rice with brown rice, quinoa, or millets.")

        if "pcos" in conditions_lower:
            warnings.append(
                ConditionWarning(
                    condition="PCOS Hormone Balance",
                    severity="info",
                    message="Maintain a balanced protein-to-carb ratio to support insulin sensitivity and hormonal health.",
                )
            )
            tips.append("Include anti-inflammatory foods like flax seeds, walnuts, and spearmint tea in your daily routine.")
            tips.append("Avoid sugary beverages and focus on nutrient-dense complex carbohydrates.")

        if "heart" in conditions_lower or "hypertension" in conditions_lower:
            warnings.append(
                ConditionWarning(
                    condition="Cardiovascular & Blood Pressure",
                    severity="warning",
                    message="Limit sodium and deep-fried items. Emphasize potassium-rich vegetables and healthy unsaturated fats.",
                )
            )
            tips.append("Choose steamed or grilled dishes (idli, dhokla, roasted paneer) instead of fried pooris or vadas.")
            tips.append("Drink unsalted spiced buttermilk with roasted cumin to aid digestion and heart health.")

        # Goal-Specific Logic & Verdicts
        goal = profile.goal or "Stay Fit"
        goal_lower = goal.lower()

        if "lose" in goal_lower:
            if c_kcal > target_kcal:
                verdict = f"Daily calorie budget reached ({int(c_kcal)} / {int(target_kcal)} kcal). Focus on light hydration and green teas for the rest of today."
            elif r_p > 25.0:
                verdict = f"On track with calories! You have a {int(r_p)}g protein gap remaining — choose a lean protein source for your next meal."
            else:
                verdict = f"Great calorie deficit control ({int(c_kcal)} kcal consumed). Keep meals rich in fiber and leafy greens."
            tips.append("Drink a full glass of water 20 minutes before each meal to naturally improve satiety.")

        elif "gain" in goal_lower or "muscle" in goal_lower:
            if r_p > 30.0:
                verdict = f"High protein demand for muscle hypertrophy: {int(r_p)}g protein needed to hit your {int(target_p)}g daily target."
                tips.append("Include paneer, boiled eggs, tofu, or a protein shake as an evening post-workout snack.")
            else:
                verdict = f"Excellent protein pacing ({int(c_p)}g consumed)! Keep surplus steady for optimal muscle recovery."
            tips.append("Distribute protein evenly across 3-4 meals (aim for 25-35g per sitting) to maximize muscle protein synthesis.")

        else:  # Stay Fit / Maintenance
            if abs(c_kcal - target_kcal) < 200:
                verdict = "Perfect energy balance achieved for your maintenance targets."
            else:
                verdict = f"Balanced nutritional pacing. {int(r_kcal)} kcal remaining for today's meals."
            tips.append("Aim for a colorful plate with at least 2 portions of fresh vegetables or fruit daily.")

        # If analyzing a specific meal right now, add meal-level feedback
        if current_meal:
            meal_p = current_meal.get("protein_g", 0.0)
            meal_c = current_meal.get("carbs_g", 0.0)
            meal_f = current_meal.get("fat_g", 0.0)
            if meal_p >= 20.0:
                tips.append("This meal delivered high-quality protein (>20g) — ideal for satiety and recovery.")
            if meal_c > 60.0 and "diabetes" in conditions_lower:
                tips.append("High carbohydrate load in this meal. Take a 15-minute brisk walk post-meal to blunt glucose rise.")

        # 5. Generate Suggested Meals matching Diet Preference & Remaining Macros
        diet_type = (profile.dietary_preference or "Vegetarian").lower()
        suggested_meals = self._build_meal_suggestions(diet_type, r_kcal, r_p, conditions_lower)

        return DietRecommendationResponse(
            user_goal=goal,
            health_conditions=conditions_list if conditions_list else ["None"],
            daily_target=MacroSummary(
                kcal=target_kcal,
                protein_g=target_p,
                carbs_g=target_c,
                fat_g=target_f,
                fiber_g=target_fib,
            ),
            consumed_today=MacroSummary(
                kcal=c_kcal,
                protein_g=c_p,
                carbs_g=c_c,
                fat_g=c_f,
                fiber_g=c_fib,
            ),
            remaining_today=MacroSummary(
                kcal=r_kcal,
                protein_g=r_p,
                carbs_g=r_c,
                fat_g=r_f,
                fiber_g=r_fib,
            ),
            calorie_progress_pct=pct_cal,
            protein_progress_pct=pct_p,
            carbs_progress_pct=pct_c,
            fat_progress_pct=pct_f,
            verdict=verdict,
            tips=tips[:4],  # Top 4 most relevant tips
            condition_warnings=warnings,
            suggested_meals=suggested_meals,
        )

    def _build_meal_suggestions(
        self, diet_type: str, remaining_kcal: float, remaining_protein: float, conditions: str
    ) -> List[MealCardItem]:
        """Generates 4 structured meal cards matching frontend MEALS structure."""
        is_vegan = "vegan" in diet_type
        is_non_veg = "non" in diet_type
        is_diabetic = "diabetes" in conditions

        # Breakfast
        if is_diabetic:
            bf_food = "Moong Dal Chilla & Mint Chutney"
            bf_kcal, bf_p, bf_c, bf_f = 260, 12, 32, 6
        elif is_vegan:
            bf_food = "Oats Bowl with Almond Milk & Berries"
            bf_kcal, bf_p, bf_c, bf_f = 310, 10, 48, 6
        else:
            bf_food = "2 Steamed Idlis + Sambar + 1 Boiled Egg" if not is_vegan and is_non_veg else "2 Steamed Idlis + Vegetable Sambar"
            bf_kcal, bf_p, bf_c, bf_f = (320, 14, 46, 5) if is_non_veg else (240, 8, 44, 2)

        # Lunch
        if is_non_veg:
            lu_food = "Grilled Chicken Curry + Brown Rice + Salad"
            lu_kcal, lu_p, lu_c, lu_f = 480, 32, 54, 12
        elif is_vegan:
            lu_food = "Tofu Palak + 2 Whole Wheat Chapatis + Dal"
            lu_kcal, lu_p, lu_c, lu_f = 460, 22, 60, 10
        else:
            lu_food = "Palak Paneer + 2 Chapatis + Cucumber Salad"
            lu_kcal, lu_p, lu_c, lu_f = 490, 24, 52, 18

        # Snack
        if is_diabetic or remaining_protein > 20:
            sn_food = "Spiced Moong Sprouts Salad + Buttermilk"
            sn_kcal, sn_p, sn_c, sn_f = 160, 10, 18, 2
        else:
            sn_food = "Roasted Makhana & Green Tea"
            sn_kcal, sn_p, sn_c, sn_f = 140, 4, 24, 2

        # Dinner
        if is_diabetic:
            di_food = "Clear Vegetable Soup + Paneer Tikka / Tofu"
            di_kcal, di_p, di_c, di_f = 340, 20, 22, 14
        elif is_non_veg:
            di_food = "Egg Curry (2 eggs) + 2 Chapatis + Salad"
            di_kcal, di_p, di_c, di_f = 410, 22, 46, 14
        else:
            di_food = "Yellow Dal Tadka + 2 Chapatis + Mixed Veg"
            di_kcal, di_p, di_c, di_f = 420, 16, 62, 9

        return [
            MealCardItem(
                id="breakfast",
                title="Breakfast",
                food=bf_food,
                kcal=bf_kcal,
                time="8:30 AM",
                macros={"p": bf_p, "c": bf_c, "f": bf_f},
                dietary_type=diet_type,
            ),
            MealCardItem(
                id="lunch",
                title="Lunch",
                food=lu_food,
                kcal=lu_kcal,
                time="1:00 PM",
                macros={"p": lu_p, "c": lu_c, "f": lu_f},
                dietary_type=diet_type,
            ),
            MealCardItem(
                id="snack",
                title="Snack",
                food=sn_food,
                kcal=sn_kcal,
                time="5:00 PM",
                macros={"p": sn_p, "c": sn_c, "f": sn_f},
                dietary_type=diet_type,
            ),
            MealCardItem(
                id="dinner",
                title="Dinner",
                food=di_food,
                kcal=di_kcal,
                time="8:00 PM",
                macros={"p": di_p, "c": di_c, "f": di_f},
                dietary_type=diet_type,
            ),
        ]
