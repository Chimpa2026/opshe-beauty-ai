"""
OPSHE Beauty AI Virtual Skin Analyzer
Main FastAPI Application Entry Point
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.api.routes import router as api_router
from backend.database.db import init_db
from backend.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log"),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and clean up on shutdown."""
    logger.info("Starting OPSHE Beauty AI Virtual Skin Analyzer...")
    init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down OPSHE application.")


app = FastAPI(
    title="OPSHE Beauty AI Virtual Skin Analyzer",
    description="AI-powered skin analysis and personalized skincare recommendation engine.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Include API routes
app.include_router(api_router)

# Health check at root
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "OPSHE Beauty AI", "version": "1.0.0"}
