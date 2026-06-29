"""
Database Module
SQLite (dev) / PostgreSQL (prod) via SQLAlchemy
"""

import logging
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text,
    DateTime, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from backend.config.settings import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AnalysisResult(Base):
    """Stores skin analysis results."""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Skin metrics
    skin_type = Column(String(20))
    skin_type_confidence = Column(Float)
    oil_level = Column(Float)
    dryness = Column(Float)
    pore_visibility = Column(Float)
    skin_texture = Column(String(20))

    # Acne metrics
    acne_count = Column(Integer, default=0)
    whitehead_count = Column(Integer, default=0)
    blackhead_count = Column(Integer, default=0)
    acne_scar_count = Column(Integer, default=0)

    # Other metrics
    redness = Column(Float)
    pigmentation = Column(Float)
    dark_spot_count = Column(Integer, default=0)
    dark_circle_level = Column(String(20))
    fine_lines_level = Column(String(20))
    skin_tone = Column(String(20))
    undertone = Column(String(20))

    # Scores
    overall_score = Column(Float)

    # Full result & recommendations as JSON
    full_result = Column(JSON)
    recommendations = Column(JSON)


def init_db():
    """Create all tables."""
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
