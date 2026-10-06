from fastapi import APIRouter, File, UploadFile, Query, HTTPException, status
from typing import Optional

from backend.config import CONFIDENCE_THRESHOLD
from backend.schemas.food import MealAnalysisResponse
from backend.services.food_detector import FoodDetectorService

router = APIRouter(prefix="/api", tags=["Food Detection & Analysis"])


@router.post(
    "/detect",
    response_model=MealAnalysisResponse,
    summary="Detect food items and calculate portions & nutrition",
    description="Upload a food image to run YOLOv8 detection, DeepLab segmentation, MiDaS depth portion estimation, and ICMR-NIN nutrition calculations.",
)
async def detect_and_analyze_meal(
    image: UploadFile = File(..., description="Meal image file to analyze"),
    confidence_threshold: Optional[float] = Query(
        None,
        ge=0.05,
        le=1.0,
        description=f"Minimum confidence threshold for detections (server default: {CONFIDENCE_THRESHOLD})",
    ),
    daily_calories: float = Query(
        2000.0,
        description="User's daily caloric target for macro distribution percentage calculations",
    ),
):
    # Validate content type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if image.content_type and image.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{image.content_type}'. Please upload a valid image (JPEG, PNG, WEBP).",
        )

    try:
        image_bytes = await image.read()
        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        if len(image_bytes) > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image file exceeds 20MB size limit.",
            )

        detector = FoodDetectorService.get_instance()
        result = detector.analyze_meal(
            image_bytes=image_bytes,
            confidence_threshold=confidence_threshold,
            user_daily_calories=daily_calories,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Meal analysis failed: {str(e)}",
        )


@router.get(
    "/classes",
    summary="Get list of detectable food classes",
    description="Returns all food classes currently supported by the trained YOLOv8 model.",
)
def get_supported_classes():
    detector = FoodDetectorService.get_instance()
    names = detector.model.names
    return {
        "total_classes": len(names),
        "classes": list(names.values()),
    }
