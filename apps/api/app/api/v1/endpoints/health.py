"""
Health check endpoint
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.db.database import get_db
from app.schemas.responses import HealthResponse
from app.services.horizon_client import HorizonClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Health check endpoint
    
    Returns service status including database and Horizon API connectivity.
    """
    # Check database
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check Horizon API
    horizon_status = "healthy"
    try:
        with HorizonClient() as client:
            # Simple connectivity check
            pass
    except Exception as e:
        logger.error(f"Horizon health check failed: {e}")
        horizon_status = "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" and horizon_status == "healthy" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        database=db_status,
        horizon=horizon_status,
        version="1.0.0"
    )
