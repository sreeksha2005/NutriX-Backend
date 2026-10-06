from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from backend.config import CORS_ORIGINS, UPLOAD_DIR
from backend.database import Base, engine
import backend.models  # Ensure all ORM models are registered

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure SQLite database tables exist
    Base.metadata.create_all(bind=engine)
    print("[NutriX API] Database initialized.")
    yield
    print("[NutriX API] Shutdown.")


app = FastAPI(
    title="NutriX API — AI Nutrition & Diet Recommendation",
    description="Backend API for food detection, portion estimation, nutrition calculation, and personalized diet recommendations.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static uploads directory for uploaded and annotated images
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include routers
from backend.routers.food import router as food_router
from backend.routers.auth import router as auth_router
from backend.routers.user import router as user_router
from backend.routers.nutrition import router as nutrition_router
from backend.routers.recommendation import router as recommendation_router

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(food_router)
app.include_router(nutrition_router)
app.include_router(recommendation_router)


@app.get("/")
def root():
    return {
        "app": "NutriX API",
        "status": "healthy",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "nutrix-backend"}
