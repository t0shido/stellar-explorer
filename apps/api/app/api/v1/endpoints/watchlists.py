"""
Watchlist management endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.db.models import Watchlist, WatchlistMember, Account
from app.schemas.watchlist_schemas import (
    WatchlistCreate,
    WatchlistMemberAdd,
    WatchlistDetailResponse,
    WatchlistListResponse,
    WatchlistMemberResponse
)
from app.schemas.responses import MessageResponse
from app.services.ingestion_service import IngestionService
from app.services.horizon_client import AccountNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/watchlists", response_model=WatchlistDetailResponse, status_code=status.HTTP_201_CREATED, tags=["watchlists"])
def create_watchlist(
    watchlist_data: WatchlistCreate,
    db: Session = Depends(get_db)
) -> WatchlistDetailResponse:
    """
    Create a new watchlist
    
    Creates a new watchlist for monitoring specific accounts.
    """
    # Check if watchlist with same name exists
    existing = db.query(Watchlist).filter(Watchlist.name == watchlist_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Watchlist with name '{watchlist_data.name}' already exists"
        )
    
    # Create watchlist
    watchlist = Watchlist(
        name=watchlist_data.name,
        description=watchlist_data.description
    )
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    
    logger.info(f"Created watchlist", extra={"watchlist_id": watchlist.id, "name": watchlist.name})
    
    return WatchlistDetailResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        member_count=0,
        members=[]
    )


@router.post("/watchlists/{watchlist_id}/accounts", response_model=MessageResponse, tags=["watchlists"])
def add_account_to_watchlist(
    watchlist_id: int,
    member_data: WatchlistMemberAdd,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Add account to watchlist
    
    Adds an account to the specified watchlist. If the account doesn't exist
    locally, it will be ingested from Horizon API on demand.
    """
    # Check if watchlist exists
    watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist with ID {watchlist_id} not found"
        )
    
    # Get or ingest account
    account = db.query(Account).filter(Account.address == member_data.address).first()
    
    if not account:
        # Ingest account on demand
        logger.info(f"Account not found locally, ingesting from Horizon", extra={"address": member_data.address})
        try:
            with IngestionService(db) as service:
                account, _, _ = service.ingest_account(member_data.address)
        except AccountNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {member_data.address} not found on Stellar network"
            )
        except Exception as e:
            logger.error(f"Failed to ingest account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to ingest account: {str(e)}"
            )
    
    # Check if already a member
    existing_member = db.query(WatchlistMember).filter(
        WatchlistMember.watchlist_id == watchlist_id,
        WatchlistMember.account_id == account.id
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account {member_data.address} is already in this watchlist"
        )
    
    # Add to watchlist
    member = WatchlistMember(
        watchlist_id=watchlist_id,
        account_id=account.id,
        reason=member_data.reason
    )
    db.add(member)
    db.commit()
    
    logger.info(
        f"Added account to watchlist",
        extra={
            "watchlist_id": watchlist_id,
            "account_id": account.id,
            "address": member_data.address
        }
    )
    
    return MessageResponse(
        success=True,
        message=f"Account {member_data.address} added to watchlist '{watchlist.name}'",
        data={"account_id": account.id, "watchlist_id": watchlist_id}
    )


@router.get("/watchlists", response_model=list[WatchlistListResponse], tags=["watchlists"])
def list_watchlists(db: Session = Depends(get_db)) -> list[WatchlistListResponse]:
    """
    List all watchlists
    
    Returns a list of all watchlists with member counts.
    """
    watchlists = db.query(
        Watchlist,
        func.count(WatchlistMember.id).label('member_count')
    ).outerjoin(
        WatchlistMember,
        Watchlist.id == WatchlistMember.watchlist_id
    ).group_by(Watchlist.id).all()
    
    return [
        WatchlistListResponse(
            id=wl.id,
            name=wl.name,
            description=wl.description,
            member_count=count
        )
        for wl, count in watchlists
    ]


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistDetailResponse, tags=["watchlists"])
def get_watchlist(
    watchlist_id: int,
    db: Session = Depends(get_db)
) -> WatchlistDetailResponse:
    """
    Get watchlist details
    
    Returns detailed information about a watchlist including all members.
    """
    watchlist = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist with ID {watchlist_id} not found"
        )
    
    # Get members with account details
    members = db.query(WatchlistMember, Account).join(
        Account,
        WatchlistMember.account_id == Account.id
    ).filter(
        WatchlistMember.watchlist_id == watchlist_id
    ).all()
    
    member_responses = [
        WatchlistMemberResponse(
            id=member.id,
            account_id=member.account_id,
            account_address=account.address,
            reason=member.reason,
            added_at=member.added_at
        )
        for member, account in members
    ]
    
    return WatchlistDetailResponse(
        id=watchlist.id,
        name=watchlist.name,
        description=watchlist.description,
        member_count=len(member_responses),
        members=member_responses
    )
