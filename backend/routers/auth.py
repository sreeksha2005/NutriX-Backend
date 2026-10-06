from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User, HealthProfile
from backend.schemas.auth import UserRegisterRequest, UserLoginRequest, AuthTokenResponse, UserSummaryResponse
from backend.services.auth import hash_password, verify_password, create_access_token, get_current_user
from backend.services.profile_calculator import calculate_health_metrics

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    # Check if user with email already exists
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered.",
        )

    # Hash password & create user
    hashed_pwd = hash_password(req.password)
    user = User(
        name=req.name,
        email=req.email.lower(),
        hashed_password=hashed_pwd,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default HealthProfile with calculated metrics
    metrics = calculate_health_metrics(
        age=22,
        gender="Male",
        height_cm=170.0,
        weight_kg=65.0,
        goal="Stay Fit",
        activity_level="Moderate",
    )

    profile = HealthProfile(
        user_id=user.id,
        age=22,
        gender="Male",
        height_cm=170.0,
        weight_kg=65.0,
        goal="Stay Fit",
        activity_level="Moderate",
        health_conditions="None",
        dietary_preference="Vegetarian",
        bmi=metrics["bmi"],
        bmr=metrics["bmr"],
        tdee=metrics["tdee"],
        target_calories=metrics["target_calories"],
        target_protein_g=metrics["target_protein_g"],
        target_carbs_g=metrics["target_carbs_g"],
        target_fat_g=metrics["target_fat_g"],
        target_fiber_g=metrics["target_fiber_g"],
    )
    db.add(profile)
    db.commit()

    # Generate access token
    token = create_access_token({"sub": str(user.id), "email": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Authenticate user and obtain JWT token",
)
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": str(user.id), "email": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }


@router.get(
    "/me",
    response_model=UserSummaryResponse,
    summary="Get current logged in user details",
)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
    }
