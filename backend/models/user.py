from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    meal_logs = relationship("MealLog", back_populates="user", cascade="all, delete-orphan")


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    age = Column(Integer, default=22)
    gender = Column(String(20), default="Male")  # Male, Female, Other
    height_cm = Column(Float, default=170.0)
    weight_kg = Column(Float, default=65.0)
    goal = Column(String(50), default="Stay Fit")  # Lose Weight, Stay Fit, Gain Muscle
    activity_level = Column(String(50), default="Moderate")  # Sedentary, Light, Moderate, Active, Very Active
    health_conditions = Column(String(255), default="None")  # e.g., "Diabetes, PCOS" or "None"
    dietary_preference = Column(String(50), default="Vegetarian")  # Vegetarian, Vegan, Non-Vegetarian
    profile_image = Column(String(255), default="")

    # Calculated metrics
    bmi = Column(Float, default=22.5)
    bmr = Column(Float, default=1600.0)
    tdee = Column(Float, default=2200.0)
    target_calories = Column(Float, default=2000.0)
    target_protein_g = Column(Float, default=75.0)
    target_carbs_g = Column(Float, default=250.0)
    target_fat_g = Column(Float, default=55.0)
    target_fiber_g = Column(Float, default=30.0)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="profile")


class MealLog(Base):
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    food_name = Column(String(200), nullable=False)
    meal_type = Column(String(50), default="Meal")  # Breakfast, Lunch, Snack, Dinner
    image_path = Column(String(255), default="")
    annotated_image_path = Column(String(255), default="")

    # Macronutrients & Portions
    total_calories = Column(Float, default=0.0)
    total_protein_g = Column(Float, default=0.0)
    total_carbs_g = Column(Float, default=0.0)
    total_fat_g = Column(Float, default=0.0)
    total_fiber_g = Column(Float, default=0.0)
    total_weight_g = Column(Float, default=0.0)
    serving_description = Column(String(100), default="1 serving")

    # Raw JSON data & Recommendations
    detected_items_json = Column(Text, default="[]")  # list of detected items with bbox & metrics
    verdict = Column(Text, default="")
    tips_json = Column(Text, default="[]")

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="meal_logs")
