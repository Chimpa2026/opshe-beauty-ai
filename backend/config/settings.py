"""
Configuration / Settings Module
Reads environment variables from .env file
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings:
    APP_NAME: str = "OPSHE Beauty AI Virtual Skin Analyzer"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/opshe.db")

    # Upload
    MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "webp"}

    # AI Model paths
    MODEL_DIR: Path = BASE_DIR / "models"

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "opshe-secret-key-change-in-production")

    # Railway / deployment
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    def __init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
