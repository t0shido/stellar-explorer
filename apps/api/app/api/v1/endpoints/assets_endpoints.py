"""
Asset endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import Optional
from decimal import Decimal

from app.db.database import get_db
from app.db.models import Asset, AccountBalance, Account
from app.schemas.asset_schemas import AssetTopHoldersResponse, AssetHolderResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/assets/top-holders", response_model=AssetTopHoldersResponse, tags=["assets"])
def get_asset_top_holders(
    asset_code: str = Query(..., description="Asset code"),
    asset_issuer: Optional[str] = Query(None, description="Asset issuer (optional for native XLM)"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of top holders to return"),
    db: Session = Depends(get_db)
) -> AssetTopHoldersResponse:
    """
    Get top holders of an asset
    
    Returns the accounts with the largest balances of the specified asset,
    sorted by balance amount. Includes percentage of total supply.
    """
    # Handle native XLM
    if asset_code.upper() == "XLM" or asset_issuer is None:
        # Native XLM - get balances where asset_id is NULL
        
        # Get latest balances for native XLM
        subquery = db.query(
            AccountBalance.account_id,
            func.max(AccountBalance.snapshot_at).label('max_snapshot')
        ).filter(
            AccountBalance.asset_id.is_(None)
        ).group_by(
            AccountBalance.account_id
        ).subquery()
        
        latest_balances = db.query(
            AccountBalance,
            Account
        ).join(
            subquery,
            and_(
                AccountBalance.account_id == subquery.c.account_id,
                AccountBalance.snapshot_at == subquery.c.max_snapshot
            )
        ).join(
            Account,
            AccountBalance.account_id == Account.id
        ).filter(
            AccountBalance.asset_id.is_(None)
        ).order_by(
            desc(AccountBalance.balance)
        ).limit(limit).all()
        
        # Calculate total supply
        total_supply = db.query(
            func.sum(AccountBalance.balance)
        ).join(
            subquery,
            and_(
                AccountBalance.account_id == subquery.c.account_id,
                AccountBalance.snapshot_at == subquery.c.max_snapshot
            )
        ).filter(
            AccountBalance.asset_id.is_(None)
        ).scalar() or Decimal('0')
        
        total_holders = db.query(
            func.count(func.distinct(AccountBalance.account_id))
        ).filter(
            AccountBalance.asset_id.is_(None)
        ).scalar() or 0
        
        asset_type = "native"
        
    else:
        # Custom asset
        asset = db.query(Asset).filter(
            Asset.asset_code == asset_code,
            Asset.asset_issuer == asset_issuer
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_code}:{asset_issuer} not found"
            )
        
        # Get latest balances for this asset
        subquery = db.query(
            AccountBalance.account_id,
            func.max(AccountBalance.snapshot_at).label('max_snapshot')
        ).filter(
            AccountBalance.asset_id == asset.id
        ).group_by(
            AccountBalance.account_id
        ).subquery()
        
        latest_balances = db.query(
            AccountBalance,
            Account
        ).join(
            subquery,
            and_(
                AccountBalance.account_id == subquery.c.account_id,
                AccountBalance.snapshot_at == subquery.c.max_snapshot
            )
        ).join(
            Account,
            AccountBalance.account_id == Account.id
        ).filter(
            AccountBalance.asset_id == asset.id
        ).order_by(
            desc(AccountBalance.balance)
        ).limit(limit).all()
        
        # Calculate total supply
        total_supply = db.query(
            func.sum(AccountBalance.balance)
        ).join(
            subquery,
            and_(
                AccountBalance.account_id == subquery.c.account_id,
                AccountBalance.snapshot_at == subquery.c.max_snapshot
            )
        ).filter(
            AccountBalance.asset_id == asset.id
        ).scalar() or Decimal('0')
        
        total_holders = db.query(
            func.count(func.distinct(AccountBalance.account_id))
        ).filter(
            AccountBalance.asset_id == asset.id
        ).scalar() or 0
        
        asset_type = asset.asset_type
    
    # Format holder responses
    holders = []
    for balance, account in latest_balances:
        percentage = float((balance.balance / total_supply * 100)) if total_supply > 0 else 0.0
        
        holders.append(
            AssetHolderResponse(
                account_id=account.id,
                account_address=account.address,
                account_label=account.label,
                balance=balance.balance,
                percentage=round(percentage, 4)
            )
        )
    
    return AssetTopHoldersResponse(
        asset_code=asset_code,
        asset_issuer=asset_issuer,
        asset_type=asset_type,
        total_holders=total_holders,
        total_supply=total_supply,
        holders=holders
    )
