"""
Alerts and flags endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import Alert, Flag, Account, Asset
from app.schemas.alert_schemas import (
    AlertResponse,
    ManualFlagCreate,
    FlagResponse
)
from app.schemas.responses import MessageResponse, PaginatedResponse, PaginationMetadata
from app.services.ingestion_service import IngestionService
from app.services.horizon_client import AccountNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/alerts", response_model=PaginatedResponse[AlertResponse], tags=["alerts"])
def list_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: info, warning, error, critical"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of alerts per page"),
    db: Session = Depends(get_db)
) -> PaginatedResponse[AlertResponse]:
    """
    List alerts with optional filtering
    
    Returns paginated list of alerts. Can be filtered by severity and
    acknowledgment status.
    """
    # Build query
    query = db.query(Alert, Account, Asset).outerjoin(
        Account,
        Alert.account_id == Account.id
    ).outerjoin(
        Asset,
        Alert.asset_id == Asset.id
    )
    
    # Apply filters
    if severity:
        query = query.filter(Alert.severity == severity)
    
    if acknowledged is not None:
        if acknowledged:
            query = query.filter(Alert.acknowledged_at.isnot(None))
        else:
            query = query.filter(Alert.acknowledged_at.is_(None))
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    offset = (page - 1) * limit
    total_pages = (total + limit - 1) // limit
    
    # Get alerts
    alerts = query.order_by(
        Alert.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    # Format responses
    alert_responses = []
    for alert, account, asset in alerts:
        alert_responses.append(
            AlertResponse(
                id=alert.id,
                account_id=alert.account_id,
                account_address=account.address if account else None,
                asset_id=alert.asset_id,
                asset_code=asset.asset_code if asset else None,
                alert_type=alert.alert_type,
                severity=alert.severity,
                payload=alert.payload,
                created_at=alert.created_at,
                acknowledged_at=alert.acknowledged_at
            )
        )
    
    return PaginatedResponse(
        data=alert_responses,
        pagination=PaginationMetadata(
            total=total,
            page=page,
            page_size=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    )


@router.post("/alerts/{alert_id}/ack", response_model=MessageResponse, tags=["alerts"])
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Acknowledge an alert
    
    Marks an alert as acknowledged with the current timestamp.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found"
        )
    
    if alert.acknowledged_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alert {alert_id} is already acknowledged"
        )
    
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Alert acknowledged", extra={"alert_id": alert_id})
    
    return MessageResponse(
        success=True,
        message=f"Alert {alert_id} acknowledged successfully",
        data={"alert_id": alert_id, "acknowledged_at": alert.acknowledged_at}
    )


@router.post("/flags/manual", response_model=FlagResponse, status_code=status.HTTP_201_CREATED, tags=["flags"])
def create_manual_flag(
    flag_data: ManualFlagCreate,
    db: Session = Depends(get_db)
) -> FlagResponse:
    """
    Create a manual flag for an account
    
    Creates a risk flag for the specified account. If the account doesn't
    exist locally, it will be ingested from Horizon API on demand.
    
    Valid severity levels: low, medium, high, critical
    """
    # Validate severity
    valid_severities = ['low', 'medium', 'high', 'critical']
    if flag_data.severity not in valid_severities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity. Must be one of: {', '.join(valid_severities)}"
        )
    
    # Get or ingest account
    account = db.query(Account).filter(Account.address == flag_data.address).first()
    
    if not account:
        logger.info(f"Account not found locally, ingesting from Horizon", extra={"address": flag_data.address})
        try:
            with IngestionService(db) as service:
                account, _, _ = service.ingest_account(flag_data.address)
        except AccountNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {flag_data.address} not found on Stellar network"
            )
        except Exception as e:
            logger.error(f"Failed to ingest account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch account: {str(e)}"
            )
    
    # Create flag
    flag = Flag(
        account_id=account.id,
        flag_type=flag_data.flag_type,
        severity=flag_data.severity,
        reason=flag_data.reason,
        evidence=flag_data.evidence
    )
    db.add(flag)
    
    # Update account risk score based on severity
    severity_scores = {
        'low': 10,
        'medium': 25,
        'high': 50,
        'critical': 75
    }
    account.risk_score = min(100.0, account.risk_score + severity_scores[flag_data.severity])
    
    db.commit()
    db.refresh(flag)
    
    logger.info(
        f"Manual flag created",
        extra={
            "flag_id": flag.id,
            "account_id": account.id,
            "address": flag_data.address,
            "severity": flag_data.severity
        }
    )
    
    return FlagResponse(
        id=flag.id,
        account_id=account.id,
        account_address=account.address,
        flag_type=flag.flag_type,
        severity=flag.severity,
        reason=flag.reason,
        evidence=flag.evidence,
        created_at=flag.created_at,
        resolved_at=flag.resolved_at
    )
