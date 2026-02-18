"""
Asset request/response schemas
"""
from pydantic import BaseModel, Field
from decimal import Decimal


class AssetHolderResponse(BaseModel):
    """Asset holder response"""
    account_id: int
    account_address: str = Field(..., description="Account address")
    account_label: str | None = Field(None, description="Account label")
    balance: Decimal = Field(..., description="Balance amount")
    percentage: float = Field(..., description="Percentage of total supply")
    
    class Config:
        from_attributes = True


class AssetTopHoldersResponse(BaseModel):
    """Top holders response with asset info"""
    asset_code: str = Field(..., description="Asset code")
    asset_issuer: str | None = Field(None, description="Asset issuer")
    asset_type: str = Field(..., description="Asset type")
    total_holders: int = Field(..., description="Total number of holders")
    total_supply: Decimal = Field(..., description="Total supply")
    holders: list[AssetHolderResponse] = Field(..., description="Top holders list")
    
    class Config:
        from_attributes = True
