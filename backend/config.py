import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Database configuration (SQLite for dev, PostgreSQL-ready)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'nutrix.db'}")

# Security & JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "nutrix_super_secret_jwt_key_development_change_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# CORS Settings (Allow React / Flutter frontend)
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "*",
]

# Model Paths
YOLO_MODEL_PATH = os.getenv(
    "YOLO_MODEL_PATH",
    str(PROJECT_ROOT / "best.pt")
)

# Inference Settings
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.40"))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.45"))
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", str(4096 * 4096)))  # ~16MP

# Upload directory
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
