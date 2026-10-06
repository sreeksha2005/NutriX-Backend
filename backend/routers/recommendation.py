from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import json

from backend.database import get_db
from backend.models.user import User, HealthProfile, MealLog
from backend.schemas.recommendation import (
    LogMealRequest,
    MealLogResponse,
    DietRecommendationResponse,
)
from backend.services.auth import get_current_user
from backend.services.recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/api/diet", tags=["Diet & Recommendations"])


@router.post(
    "/log",
    response_model=MealLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a detected meal into the user diary",
)
def log_meal(
    req: LogMealRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Saves a meal (with nutrients and detected item details) to user's history."""
    meal_log = MealLog(
        user_id=current_user.id,
        food_name=req.food_name,
        meal_type=req.meal_type,
        image_path=req.image_path or "",
        annotated_image_path=req.annotated_image_path or "",
        total_calories=round(req.total_calories, 1),
        total_protein_g=round(req.total_protein_g, 1),
        total_carbs_g=round(req.total_carbs_g, 1),
        total_fat_g=round(req.total_fat_g, 1),
        total_fiber_g=round(req.total_fiber_g, 1),
        total_weight_g=round(req.total_weight_g, 1),
        serving_description=req.serving_description or f"{int(req.total_weight_g)}g",
        detected_items_json=json.dumps(req.detected_items or []),
        verdict=req.verdict or "",
        tips_json=json.dumps(req.tips or []),
        created_at=datetime.utcnow(),
    )
    db.add(meal_log)
    db.commit()
    db.refresh(meal_log)

    return MealLogResponse(
        id=meal_log.id,
        user_id=meal_log.user_id,
        food_name=meal_log.food_name,
        meal_type=meal_log.meal_type,
        total_calories=meal_log.total_calories,
        total_weight_g=meal_log.total_weight_g,
        total_protein_g=meal_log.total_protein_g,
        total_carbs_g=meal_log.total_carbs_g,
        total_fat_g=meal_log.total_fat_g,
        total_fiber_g=meal_log.total_fiber_g,
        serving_description=meal_log.serving_description,
        verdict=meal_log.verdict,
        created_at=meal_log.created_at.strftime("%Y-%m-%d %H:%M"),
        image_url=meal_log.image_path,
        annotated_image_url=meal_log.annotated_image_path,
    )


@router.get(
    "/plan",
    response_model=DietRecommendationResponse,
    summary="Get personalized diet recommendations, macro gaps, and meal suggestions",
)
def get_diet_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        profile = HealthProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    # Compute today's total consumed intake from database logs
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_logs = (
        db.query(MealLog)
        .filter(MealLog.user_id == current_user.id, MealLog.created_at >= today_start)
        .all()
    )

    consumed_today = {
        "kcal": sum(log.total_calories for log in today_logs),
        "protein_g": sum(log.total_protein_g for log in today_logs),
        "carbs_g": sum(log.total_carbs_g for log in today_logs),
        "fat_g": sum(log.total_fat_g for log in today_logs),
        "fiber_g": sum(log.total_fiber_g for log in today_logs),
    }

    engine = RecommendationEngine.get_instance()
    return engine.generate_recommendation(
        profile=profile,
        consumed_today=consumed_today,
    )


@router.get(
    "/history",
    response_model=List[MealLogResponse],
    summary="Get user meal history logs",
)
def get_meal_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(MealLog)
        .filter(MealLog.user_id == current_user.id)
        .order_by(MealLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        MealLogResponse(
            id=log.id,
            user_id=log.user_id,
            food_name=log.food_name,
            meal_type=log.meal_type,
            total_calories=log.total_calories,
            total_weight_g=log.total_weight_g,
            total_protein_g=log.total_protein_g,
            total_carbs_g=log.total_carbs_g,
            total_fat_g=log.total_fat_g,
            total_fiber_g=log.total_fiber_g,
            serving_description=log.serving_description,
            verdict=log.verdict,
            created_at=log.created_at.strftime("%Y-%m-%d %H:%M"),
            image_url=log.image_path,
            annotated_image_url=log.annotated_image_path,
        )
        for log in logs
    ]


@router.delete(
    "/log/{log_id}",
    summary="Delete a meal log entry",
)
def delete_meal_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = (
        db.query(MealLog)
        .filter(MealLog.id == log_id, MealLog.user_id == current_user.id)
        .first()
    )
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal log entry not found.",
        )
    db.delete(log)
    db.commit()
    return {"success": True, "message": f"Meal log #{log_id} deleted."}
