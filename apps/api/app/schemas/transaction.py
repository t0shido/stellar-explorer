from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TransactionBase(BaseModel):
    tx_hash: str
    ledger: int
    source_account_id: Optional[int] = None
    fee_charged: int
    operation_count: int
    successful: bool = True
    memo: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
