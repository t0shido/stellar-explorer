"""
Ingestion API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.database import get_db
from app.services.ingestion_service import IngestionService
from app.services.horizon_client import AccountNotFoundError, HorizonClientError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/account/{address}", response_model=Dict[str, Any])
def ingest_account(
    address: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ingest account data from Stellar network
    
    Fetches account balances, trustlines, and metadata from Horizon API
    and stores in database. Idempotent - safe to call multiple times.
    
    Args:
        address: Stellar account address (G...)
        
    Returns:
        Summary of ingestion results
        
    Raises:
        404: Account not found on network
        500: API or database error
    """
    try:
        with IngestionService(db) as service:
            account, balances_created, assets_created = service.ingest_account(address)
            
            return {
                "success": True,
                "account": {
                    "id": account.id,
                    "address": account.address,
                    "risk_score": account.risk_score
                },
                "balances_created": balances_created,
                "assets_created": assets_created
            }
            
    except AccountNotFoundError as e:
        logger.warning(f"Account not found: {address}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except HorizonClientError as e:
        logger.error(f"Horizon API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Horizon API error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error ingesting account: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/transactions/latest", response_model=Dict[str, Any])
def ingest_latest_transactions(
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ingest latest transactions from Stellar network
    
    Fetches recent transactions and their operations from Horizon API.
    Idempotent - skips transactions that already exist.
    
    Args:
        limit: Number of transactions to fetch (max 200)
        
    Returns:
        Summary of ingestion results
        
    Raises:
        400: Invalid limit parameter
        500: API or database error
    """
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 200"
        )
    
    try:
        with IngestionService(db) as service:
            transactions_created, operations_created = service.ingest_latest_transactions(limit)
            
            return {
                "success": True,
                "transactions_created": transactions_created,
                "operations_created": operations_created,
                "limit": limit
            }
            
    except HorizonClientError as e:
        logger.error(f"Horizon API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Horizon API error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error ingesting transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/watchlist/refresh", response_model=Dict[str, Any])
def refresh_watchlist_accounts(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Refresh data for all watchlist accounts
    
    Updates balances and recent activity for all accounts in watchlists.
    Can be run as background task for large watchlists.
    
    Returns:
        Summary of refresh operation
        
    Raises:
        500: API or database error
    """
    try:
        with IngestionService(db) as service:
            summary = service.ingest_watchlist_accounts()
            
            return {
                "success": True,
                **summary
            }
            
    except Exception as e:
        logger.error(f"Unexpected error refreshing watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/watchlist/refresh-async")
def refresh_watchlist_accounts_async(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Refresh watchlist accounts in background
    
    Queues refresh operation to run asynchronously.
    Useful for large watchlists that take time to process.
    
    Returns:
        Acknowledgment that task was queued
    """
    from app.db.database import SessionLocal

    def refresh_task():
        task_db = SessionLocal()
        try:
            with IngestionService(task_db) as service:
                summary = service.ingest_watchlist_accounts()
                logger.info("Background watchlist refresh completed", extra=summary)
        except Exception as e:
            logger.error("Background watchlist refresh failed", extra={"error": str(e)})
        finally:
            task_db.close()
    
    background_tasks.add_task(refresh_task)
    
    return {
        "success": True,
        "message": "Watchlist refresh queued for background processing"
    }


@router.post("/operations/stream", response_model=Dict[str, Any])
def ingest_operations_stream(
    limit: int = 200,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ingest operations using durable cursor (operations-first ingestion)
    """
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 200")

    try:
        with IngestionService(db) as service:
            tx_created, ops_created = service.ingest_operations_stream(limit=limit)

            return {
                "success": True,
                "transactions_created": tx_created,
                "operations_created": ops_created,
                "limit": limit
            }
    except HorizonClientError as e:
        logger.error("Horizon API error during operations ingestion", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Horizon API error: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error ingesting operations", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
