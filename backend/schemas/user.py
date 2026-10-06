from pydantic import BaseModel, Field
from typing import Optional, List


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=10, le=120)
    gender: Optional[str] = Field(None, description="Male, Female, Other")
    height_cm: Optional[float] = Field(None, ge=50, le=250)
    weight_kg: Optional[float] = Field(None, ge=20, le=300)
    goal: Optional[str] = Field(None, description="Lose Weight, Stay Fit, Gain Muscle")
    activity_level: Optional[str] = Field(None, description="Sedentary, Light, Moderate, Active, Very Active")
    health_conditions: Optional[str] = Field(None, description="e.g. Diabetes, PCOS, Heart Disease, or None")
    dietary_preference: Optional[str] = Field(None, description="Vegetarian, Vegan, Non-Vegetarian")
    profile_image: Optional[str] = None


class MacroTarget(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


class ProfileResponse(BaseModel):
    user_id: int
    name: str
    email: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    goal: str
    activity_level: str
    health_conditions: str
    dietary_preference: str
    profile_image: str

    # Health & Nutrition Metrics
    bmi: float
    bmi_category: str
    bmr: float
    tdee: float
    targets: MacroTarget


class HealthStatsResponse(BaseModel):
    bmi: float
    bmi_category: str
    bmr: float
    tdee: float
    target_calories: float
    target_protein_g: float
    target_carbs_g: float
    target_fat_g: float
    target_fiber_g: float
    goal: str
    health_conditions: str
