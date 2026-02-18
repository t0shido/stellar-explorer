"""
Account request/response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


class AccountBalanceResponse(BaseModel):
    """Account balance response"""
    asset_code: Optional[str] = Field(None, description="Asset code (null for XLM)")
    asset_issuer: Optional[str] = Field(None, description="Asset issuer")
    asset_type: Optional[str] = Field(None, description="Asset type")
    balance: Decimal = Field(..., description="Balance amount")
    limit: Optional[Decimal] = Field(None, description="Trustline limit")
    buying_liabilities: Decimal = Field(default=Decimal('0'), description="Buying liabilities")
    selling_liabilities: Decimal = Field(default=Decimal('0'), description="Selling liabilities")
    
    class Config:
        from_attributes = True


class AccountDetailResponse(BaseModel):
    """Detailed account response"""
    id: int
    address: str = Field(..., description="Stellar account address")
    label: Optional[str] = Field(None, description="Account label")
    risk_score: float = Field(..., description="Risk score (0-100)")
    first_seen: datetime = Field(..., description="First seen timestamp")
    last_seen: Optional[datetime] = Field(None, description="Last activity timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Account metadata")
    balances: list[AccountBalanceResponse] = Field(default_factory=list, description="Account balances")
    
    class Config:
        from_attributes = True


class AccountActivityResponse(BaseModel):
    """Account activity (transaction) response"""
    tx_hash: str = Field(..., description="Transaction hash")
    ledger: int = Field(..., description="Ledger number")
    created_at: datetime = Field(..., description="Transaction timestamp")
    operation_count: int = Field(..., description="Number of operations")
    successful: bool = Field(..., description="Transaction success status")
    fee_charged: int = Field(..., description="Fee charged in stroops")
    memo: Optional[str] = Field(None, description="Transaction memo")
    
    class Config:
        from_attributes = True


class CounterpartyResponse(BaseModel):
    """Counterparty relationship response"""
    account_id: int
    account_address: str = Field(..., description="Counterparty account address")
    account_label: Optional[str] = Field(None, description="Counterparty label")
    asset_code: Optional[str] = Field(None, description="Asset code (null for XLM)")
    asset_issuer: Optional[str] = Field(None, description="Asset issuer")
    tx_count: int = Field(..., description="Number of transactions")
    total_amount: Decimal = Field(..., description="Total amount transferred")
    last_seen: datetime = Field(..., description="Last transaction timestamp")
    direction: str = Field(..., description="Direction: 'sent' or 'received'")
    
    class Config:
        from_attributes = True
