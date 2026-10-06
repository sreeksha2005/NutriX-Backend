from typing import Dict, Any


def calculate_health_metrics(
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    activity_level: str = "Moderate",
    goal: str = "Stay Fit",
    health_conditions: str = "None",
    dietary_preference: str = "Vegetarian",
) -> Dict[str, Any]:
    """
    Computes BMI, BMR, TDEE, and daily target calories/macros (Mifflin-St Jeor equation).
    Tailors nutrition recommendations for user goals and health conditions.
    """
    # 1. BMI Calculation
    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m ** 2), 1) if height_m > 0 else 22.0

    if bmi < 18.5:
        bmi_category = "Underweight"
    elif 18.5 <= bmi < 24.9:
        bmi_category = "Normal weight"
    elif 25.0 <= bmi < 29.9:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obese"

    # 2. BMR Calculation (Mifflin-St Jeor Formula)
    gender_norm = gender.strip().lower()
    if gender_norm == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    bmr = round(max(bmr, 1000.0), 1)

    # 3. Activity Level Multiplier -> TDEE
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very active": 1.9,
        "very_active": 1.9,
    }
    multiplier = activity_multipliers.get(activity_level.strip().lower(), 1.55)
    tdee = round(bmr * multiplier, 1)

    # 4. Target Calories based on Goal
    goal_norm = goal.strip().lower()
    if "lose" in goal_norm:
        # 500 kcal deficit for safe ~0.5kg/week loss
        target_calories = max(tdee - 500.0, 1200.0)
        protein_pct = 0.30  # Higher protein to preserve lean muscle
        carbs_pct = 0.40
        fat_pct = 0.30
    elif "gain" in goal_norm or "muscle" in goal_norm:
        # 300 kcal surplus for muscle hyperthrophy
        target_calories = tdee + 300.0
        protein_pct = 0.30
        carbs_pct = 0.45
        fat_pct = 0.25
    else:
        # Maintenance (Stay Fit)
        target_calories = tdee
        protein_pct = 0.25
        carbs_pct = 0.50
        fat_pct = 0.25

    # 5. Health Condition Adjustments
    conditions_lower = health_conditions.lower()
    if "diabetes" in conditions_lower:
        # Lower carbs (35%), higher protein/fiber, complex carbs
        carbs_pct = max(0.30, carbs_pct - 0.10)
        protein_pct = min(0.35, protein_pct + 0.05)
        fat_pct = 1.0 - (carbs_pct + protein_pct)

    if "pcos" in conditions_lower:
        # Lower glycemic load, balanced fat and protein
        carbs_pct = min(0.38, carbs_pct)
        protein_pct = max(0.28, protein_pct)
        fat_pct = 1.0 - (carbs_pct + protein_pct)

    # Calculate Macro Grams: Protein (4 kcal/g), Carbs (4 kcal/g), Fat (9 kcal/g)
    target_protein_g = round((target_calories * protein_pct) / 4.0, 1)
    target_carbs_g = round((target_calories * carbs_pct) / 4.0, 1)
    target_fat_g = round((target_calories * fat_pct) / 9.0, 1)
    target_fiber_g = round(max(25.0, (target_calories / 1000.0) * 14.0), 1)  # 14g fiber per 1000 kcal

    return {
        "bmi": bmi,
        "bmi_category": bmi_category,
        "bmr": bmr,
        "tdee": tdee,
        "target_calories": round(target_calories, 1),
        "target_protein_g": target_protein_g,
        "target_carbs_g": target_carbs_g,
        "target_fat_g": target_fat_g,
        "target_fiber_g": target_fiber_g,
    }
