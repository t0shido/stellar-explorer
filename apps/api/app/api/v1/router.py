from fastapi import APIRouter
from app.api.v1.endpoints import (
    accounts,
    transactions,
    stellar,
    ingestion,
    health,
    watchlists,
    accounts_endpoints,
    assets_endpoints,
    alerts_endpoints
)

api_router = APIRouter()

# Health check (no prefix)
api_router.include_router(health.router, tags=["health"])

# Core endpoints (legacy)
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(stellar.router, prefix="/stellar", tags=["stellar"])

# New comprehensive endpoints
api_router.include_router(accounts_endpoints.router, tags=["accounts"])
api_router.include_router(assets_endpoints.router, tags=["assets"])
api_router.include_router(watchlists.router, tags=["watchlists"])
api_router.include_router(alerts_endpoints.router, tags=["alerts", "flags"])

# Ingestion endpoints
api_router.include_router(ingestion.router, prefix="/ingest", tags=["ingestion"])
