from fastapi import APIRouter, HTTPException
from stellar_sdk import Server
from app.core.config import settings

router = APIRouter()

# Initialize Stellar server
server = Server(horizon_url=settings.STELLAR_HORIZON_URL)


@router.get("/network")
async def get_network_info():
    """Get Stellar network information"""
    try:
        # Get network details
        return {
            "network": settings.STELLAR_NETWORK,
            "horizon_url": settings.STELLAR_HORIZON_URL,
            "status": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account/{account_id}")
async def get_stellar_account(account_id: str):
    """Fetch account data from Stellar network"""
    try:
        account = server.accounts().account_id(account_id).call()
        return account
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Account not found: {str(e)}")


@router.get("/transactions/recent")
async def get_recent_transactions(limit: int = 10):
    """Get recent transactions from Stellar network"""
    try:
        transactions = server.transactions().limit(limit).order(desc=True).call()
        return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
