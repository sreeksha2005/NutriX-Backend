from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.user import User, HealthProfile
from backend.schemas.user import ProfileUpdateRequest, ProfileResponse, HealthStatsResponse, MacroTarget
from backend.services.auth import get_current_user
from backend.services.profile_calculator import calculate_health_metrics

router = APIRouter(prefix="/api/profile", tags=["User Profile & Health"])


def _build_profile_response(user: User, profile: HealthProfile) -> ProfileResponse:
    metrics = calculate_health_metrics(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        goal=profile.goal,
        health_conditions=profile.health_conditions,
        dietary_preference=profile.dietary_preference,
    )
    return ProfileResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        goal=profile.goal,
        activity_level=profile.activity_level,
        health_conditions=profile.health_conditions,
        dietary_preference=profile.dietary_preference,
        profile_image=profile.profile_image or "",
        bmi=metrics["bmi"],
        bmi_category=metrics["bmi_category"],
        bmr=metrics["bmr"],
        tdee=metrics["tdee"],
        targets=MacroTarget(
            calories=metrics["target_calories"],
            protein_g=metrics["target_protein_g"],
            carbs_g=metrics["target_carbs_g"],
            fat_g=metrics["target_fat_g"],
            fiber_g=metrics["target_fiber_g"],
        ),
    )


@router.get(
    "",
    response_model=ProfileResponse,
    summary="Get user health profile and nutritional targets",
)
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        # Create default profile if missing
        profile = HealthProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return _build_profile_response(current_user, profile)


@router.put(
    "",
    response_model=ProfileResponse,
    summary="Update user health profile and recalculate daily targets",
)
def update_user_profile(
    req: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        profile = HealthProfile(user_id=current_user.id)
        db.add(profile)

    # Update user name if provided
    if req.name is not None:
        current_user.name = req.name

    # Update profile fields if provided
    if req.age is not None:
        profile.age = req.age
    if req.gender is not None:
        profile.gender = req.gender
    if req.height_cm is not None:
        profile.height_cm = req.height_cm
    if req.weight_kg is not None:
        profile.weight_kg = req.weight_kg
    if req.goal is not None:
        profile.goal = req.goal
    if req.activity_level is not None:
        profile.activity_level = req.activity_level
    if req.health_conditions is not None:
        profile.health_conditions = req.health_conditions
    if req.dietary_preference is not None:
        profile.dietary_preference = req.dietary_preference
    if req.profile_image is not None:
        profile.profile_image = req.profile_image

    # Recalculate metrics
    metrics = calculate_health_metrics(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        goal=profile.goal,
        health_conditions=profile.health_conditions,
        dietary_preference=profile.dietary_preference,
    )

    profile.bmi = metrics["bmi"]
    profile.bmr = metrics["bmr"]
    profile.tdee = metrics["tdee"]
    profile.target_calories = metrics["target_calories"]
    profile.target_protein_g = metrics["target_protein_g"]
    profile.target_carbs_g = metrics["target_carbs_g"]
    profile.target_fat_g = metrics["target_fat_g"]
    profile.target_fiber_g = metrics["target_fiber_g"]

    db.commit()
    db.refresh(current_user)
    db.refresh(profile)

    return _build_profile_response(current_user, profile)


@router.get(
    "/stats",
    response_model=HealthStatsResponse,
    summary="Get user health metrics and BMI classification",
)
def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == current_user.id).first()
    if not profile:
        profile = HealthProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    metrics = calculate_health_metrics(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        goal=profile.goal,
        health_conditions=profile.health_conditions,
        dietary_preference=profile.dietary_preference,
    )

    return HealthStatsResponse(
        bmi=metrics["bmi"],
        bmi_category=metrics["bmi_category"],
        bmr=metrics["bmr"],
        tdee=metrics["tdee"],
        target_calories=metrics["target_calories"],
        target_protein_g=metrics["target_protein_g"],
        target_carbs_g=metrics["target_carbs_g"],
        target_fat_g=metrics["target_fat_g"],
        target_fiber_g=metrics["target_fiber_g"],
        goal=profile.goal,
        health_conditions=profile.health_conditions,
    )
