"""
Account endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional

from app.db.database import get_db
from app.db.models import Account, AccountBalance, Asset, Transaction, CounterpartyEdge
from app.schemas.account_schemas import (
    AccountDetailResponse,
    AccountBalanceResponse,
    AccountActivityResponse,
    CounterpartyResponse
)
from app.schemas.responses import PaginatedResponse, PaginationMetadata
from app.services.ingestion_service import IngestionService
from app.services.horizon_client import AccountNotFoundError
from decimal import Decimal

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/accounts/{address}", response_model=AccountDetailResponse, tags=["accounts"])
def get_account(
    address: str,
    db: Session = Depends(get_db)
) -> AccountDetailResponse:
    """
    Get account details
    
    Returns detailed account information including balances. If the account
    doesn't exist locally, it will be ingested from Horizon API on demand.
    """
    # Try to find account locally
    account = db.query(Account).filter(Account.address == address).first()
    
    if not account:
        # Ingest account on demand
        logger.info(f"Account not found locally, ingesting from Horizon", extra={"address": address})
        try:
            with IngestionService(db) as service:
                account, _, _ = service.ingest_account(address)
        except AccountNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {address} not found on Stellar network"
            )
        except Exception as e:
            logger.error(f"Failed to ingest account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch account: {str(e)}"
            )
    
    # Get latest balances (most recent snapshot per asset)
    latest_balances = db.query(AccountBalance, Asset).outerjoin(
        Asset,
        AccountBalance.asset_id == Asset.id
    ).filter(
        AccountBalance.account_id == account.id
    ).order_by(
        AccountBalance.snapshot_at.desc()
    ).all()
    
    # Group by asset and take most recent
    balance_map = {}
    for balance, asset in latest_balances:
        key = balance.asset_id or 'native'
        if key not in balance_map:
            balance_map[key] = (balance, asset)
    
    balance_responses = []
    for balance, asset in balance_map.values():
        balance_responses.append(
            AccountBalanceResponse(
                asset_code=asset.asset_code if asset else None,
                asset_issuer=asset.asset_issuer if asset else None,
                asset_type=asset.asset_type if asset else "native",
                balance=balance.balance,
                limit=balance.limit,
                buying_liabilities=balance.buying_liabilities,
                selling_liabilities=balance.selling_liabilities
            )
        )
    
    return AccountDetailResponse(
        id=account.id,
        address=account.address,
        label=account.label,
        risk_score=account.risk_score,
        first_seen=account.first_seen,
        last_seen=account.last_seen,
        metadata=account.meta_data,
        balances=balance_responses
    )


@router.get("/accounts/{address}/activity", response_model=PaginatedResponse[AccountActivityResponse], tags=["accounts"])
def get_account_activity(
    address: str,
    limit: int = Query(default=50, ge=1, le=200, description="Number of transactions to return"),
    page: int = Query(default=1, ge=1, description="Page number"),
    db: Session = Depends(get_db)
) -> PaginatedResponse[AccountActivityResponse]:
    """
    Get account activity (transactions)
    
    Returns paginated list of transactions for the account. If the account
    doesn't exist locally, it will be ingested from Horizon API on demand.
    """
    # Get or ingest account
    account = db.query(Account).filter(Account.address == address).first()
    
    if not account:
        logger.info(f"Account not found locally, ingesting from Horizon", extra={"address": address})
        try:
            with IngestionService(db) as service:
                account, _, _ = service.ingest_account(address)
        except AccountNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {address} not found on Stellar network"
            )
        except Exception as e:
            logger.error(f"Failed to ingest account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch account: {str(e)}"
            )
    
    # Get total count
    total = db.query(Transaction).filter(
        Transaction.source_account_id == account.id
    ).count()
    
    # Calculate pagination
    offset = (page - 1) * limit
    total_pages = (total + limit - 1) // limit
    
    # Get transactions
    transactions = db.query(Transaction).filter(
        Transaction.source_account_id == account.id
    ).order_by(
        Transaction.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    activity_responses = [
        AccountActivityResponse(
            tx_hash=tx.tx_hash,
            ledger=tx.ledger,
            created_at=tx.created_at,
            operation_count=tx.operation_count,
            successful=tx.successful,
            fee_charged=tx.fee_charged,
            memo=tx.memo
        )
        for tx in transactions
    ]
    
    return PaginatedResponse(
        data=activity_responses,
        pagination=PaginationMetadata(
            total=total,
            page=page,
            page_size=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    )


@router.get("/accounts/{address}/counterparties", response_model=list[CounterpartyResponse], tags=["accounts"])
def get_account_counterparties(
    address: str,
    limit: int = Query(default=50, ge=1, le=200, description="Number of counterparties to return"),
    db: Session = Depends(get_db)
) -> list[CounterpartyResponse]:
    """
    Get account counterparties
    
    Returns accounts that have transacted with this account, sorted by
    transaction count. Includes both sent and received relationships.
    """
    # Get or ingest account
    account = db.query(Account).filter(Account.address == address).first()
    
    if not account:
        logger.info(f"Account not found locally, ingesting from Horizon", extra={"address": address})
        try:
            with IngestionService(db) as service:
                account, _, _ = service.ingest_account(address)
        except AccountNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {address} not found on Stellar network"
            )
        except Exception as e:
            logger.error(f"Failed to ingest account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch account: {str(e)}"
            )
    
    # Get outgoing edges (sent)
    outgoing = db.query(
        CounterpartyEdge,
        Account,
        Asset
    ).join(
        Account,
        CounterpartyEdge.to_account_id == Account.id
    ).outerjoin(
        Asset,
        CounterpartyEdge.asset_id == Asset.id
    ).filter(
        CounterpartyEdge.from_account_id == account.id
    ).order_by(
        CounterpartyEdge.tx_count.desc()
    ).limit(limit).all()
    
    # Get incoming edges (received)
    incoming = db.query(
        CounterpartyEdge,
        Account,
        Asset
    ).join(
        Account,
        CounterpartyEdge.from_account_id == Account.id
    ).outerjoin(
        Asset,
        CounterpartyEdge.asset_id == Asset.id
    ).filter(
        CounterpartyEdge.to_account_id == account.id
    ).order_by(
        CounterpartyEdge.tx_count.desc()
    ).limit(limit).all()
    
    # Combine and format responses
    counterparties = []
    
    for edge, counterparty_account, asset in outgoing:
        counterparties.append(
            CounterpartyResponse(
                account_id=counterparty_account.id,
                account_address=counterparty_account.address,
                account_label=counterparty_account.label,
                asset_code=asset.asset_code if asset else None,
                asset_issuer=asset.asset_issuer if asset else None,
                tx_count=edge.tx_count,
                total_amount=edge.total_amount,
                last_seen=edge.last_seen,
                direction="sent"
            )
        )
    
    for edge, counterparty_account, asset in incoming:
        counterparties.append(
            CounterpartyResponse(
                account_id=counterparty_account.id,
                account_address=counterparty_account.address,
                account_label=counterparty_account.label,
                asset_code=asset.asset_code if asset else None,
                asset_issuer=asset.asset_issuer if asset else None,
                tx_count=edge.tx_count,
                total_amount=edge.total_amount,
                last_seen=edge.last_seen,
                direction="received"
            )
        )
    
    # Sort by transaction count
    counterparties.sort(key=lambda x: x.tx_count, reverse=True)
    
    return counterparties[:limit]
