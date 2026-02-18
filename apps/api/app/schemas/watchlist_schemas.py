"""
Watchlist request/response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WatchlistCreate(BaseModel):
    """Create watchlist request"""
    name: str = Field(..., min_length=1, max_length=255, description="Watchlist name")
    description: Optional[str] = Field(None, description="Watchlist description")


class WatchlistMemberAdd(BaseModel):
    """Add account to watchlist request"""
    address: str = Field(..., min_length=56, max_length=56, description="Stellar account address")
    reason: Optional[str] = Field(None, description="Reason for adding to watchlist")


class WatchlistMemberResponse(BaseModel):
    """Watchlist member response"""
    id: int
    account_id: int
    account_address: str = Field(..., description="Account address")
    reason: Optional[str] = None
    added_at: datetime
    
    class Config:
        from_attributes = True


class WatchlistDetailResponse(BaseModel):
    """Detailed watchlist response with members"""
    id: int
    name: str
    description: Optional[str] = None
    member_count: int = Field(..., description="Number of accounts in watchlist")
    members: list[WatchlistMemberResponse] = []
    
    class Config:
        from_attributes = True


class WatchlistListResponse(BaseModel):
    """Watchlist list item response"""
    id: int
    name: str
    description: Optional[str] = None
    member_count: int = Field(..., description="Number of accounts in watchlist")
    
    class Config:
        from_attributes = True
