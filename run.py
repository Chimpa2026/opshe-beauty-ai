"""
OPSHE Beauty AI Virtual Skin Analyzer
Application entry point — run with: python run.py
"""

import uvicorn
from backend.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
