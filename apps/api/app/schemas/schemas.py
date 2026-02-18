from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal


# ============================================================================
# Account Schemas
# ============================================================================

class AccountBase(BaseModel):
    address: str = Field(..., max_length=56)
    label: Optional[str] = Field(None, max_length=255)
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=255)
    risk_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    metadata: Optional[Dict[str, Any]] = None


class AccountResponse(AccountBase):
    id: int
    first_seen: datetime
    last_seen: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# Asset Schemas
# ============================================================================

class AssetBase(BaseModel):
    asset_code: str = Field(..., max_length=12)
    asset_issuer: Optional[str] = Field(None, max_length=56)
    asset_type: Optional[str] = Field(None, max_length=20)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetCreate(AssetBase):
    pass


class AssetResponse(AssetBase):
    id: int
    
    class Config:
        from_attributes = True


# ============================================================================
# Account Balance Schemas
# ============================================================================

class AccountBalanceBase(BaseModel):
    account_id: int
    asset_id: Optional[int] = None
    balance: Decimal = Field(..., max_digits=20, decimal_places=7)
    limit: Optional[Decimal] = Field(None, max_digits=20, decimal_places=7)
    buying_liabilities: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=7)
    selling_liabilities: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=7)


class AccountBalanceCreate(AccountBalanceBase):
    pass


class AccountBalanceResponse(AccountBalanceBase):
    id: int
    snapshot_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Transaction Schemas
# ============================================================================

class TransactionBase(BaseModel):
    tx_hash: str = Field(..., max_length=64)
    ledger: int
    source_account_id: Optional[int] = None
    fee_charged: int
    operation_count: int = Field(default=1, ge=1)
    memo: Optional[str] = None
    successful: bool = True


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Operation Schemas
# ============================================================================

class OperationBase(BaseModel):
    op_id: str = Field(..., max_length=64)
    tx_id: int
    type: str = Field(..., max_length=50)
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    asset_id: Optional[int] = None
    amount: Optional[Decimal] = Field(None, max_digits=20, decimal_places=7)
    raw: Dict[str, Any] = Field(...)


class OperationCreate(OperationBase):
    pass


class OperationResponse(OperationBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Counterparty Edge Schemas
# ============================================================================

class CounterpartyEdgeBase(BaseModel):
    from_account_id: int
    to_account_id: int
    asset_id: Optional[int] = None
    tx_count: int = Field(default=1, ge=1)
    total_amount: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=7)


class CounterpartyEdgeCreate(CounterpartyEdgeBase):
    pass


class CounterpartyEdgeUpdate(BaseModel):
    tx_count: Optional[int] = Field(None, ge=1)
    total_amount: Optional[Decimal] = Field(None, max_digits=20, decimal_places=7)


class CounterpartyEdgeResponse(CounterpartyEdgeBase):
    id: int
    last_seen: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Watchlist Schemas
# ============================================================================

class WatchlistBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None


class WatchlistCreate(WatchlistBase):
    pass


class WatchlistUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class WatchlistResponse(WatchlistBase):
    id: int
    
    class Config:
        from_attributes = True


# ============================================================================
# Watchlist Member Schemas
# ============================================================================

class WatchlistMemberBase(BaseModel):
    watchlist_id: int
    account_id: int
    reason: Optional[str] = None


class WatchlistMemberCreate(WatchlistMemberBase):
    pass


class WatchlistMemberResponse(WatchlistMemberBase):
    id: int
    added_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Flag Schemas
# ============================================================================

class FlagBase(BaseModel):
    account_id: int
    flag_type: str = Field(..., max_length=100)
    severity: str = Field(..., max_length=20)  # low, medium, high, critical
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class FlagCreate(FlagBase):
    pass


class FlagUpdate(BaseModel):
    severity: Optional[str] = Field(None, max_length=20)
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    resolved_at: Optional[datetime] = None


class FlagResponse(FlagBase):
    id: int
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# Alert Schemas
# ============================================================================

class AlertBase(BaseModel):
    account_id: Optional[int] = None
    asset_id: Optional[int] = None
    alert_type: str = Field(..., max_length=100)
    severity: str = Field(..., max_length=20)  # info, warning, error, critical
    payload: Dict[str, Any] = Field(...)


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    acknowledged_at: Optional[datetime] = None


class AlertResponse(AlertBase):
    id: int
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# Complex Response Schemas with Relationships
# ============================================================================

class AccountWithDetails(AccountResponse):
    """Account with related data"""
    balance_count: Optional[int] = None
    transaction_count: Optional[int] = None
    flag_count: Optional[int] = None
    unresolved_flag_count: Optional[int] = None


class TransactionWithOperations(TransactionResponse):
    """Transaction with operations"""
    operations: list[OperationResponse] = []


class CounterpartyEdgeWithAccounts(CounterpartyEdgeResponse):
    """Edge with account details"""
    from_address: str
    to_address: str
    asset_code: Optional[str] = None


class WatchlistWithMembers(WatchlistResponse):
    """Watchlist with member count"""
    member_count: int = 0


class AccountRiskSummary(BaseModel):
    """Risk summary for an account"""
    account_id: int
    address: str
    risk_score: float
    active_flags: int
    recent_alerts: int
    counterparty_count: int
    total_transactions: int
    
    class Config:
        from_attributes = True
