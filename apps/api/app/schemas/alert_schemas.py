"""
Alert and flag request/response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class AlertResponse(BaseModel):
    """Alert response"""
    id: int
    account_id: Optional[int] = None
    account_address: Optional[str] = Field(None, description="Related account address")
    asset_id: Optional[int] = None
    asset_code: Optional[str] = Field(None, description="Related asset code")
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    payload: Dict[str, Any] = Field(..., description="Alert details")
    created_at: datetime = Field(..., description="Alert creation time")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgment time")
    
    class Config:
        from_attributes = True


class ManualFlagCreate(BaseModel):
    """Create manual flag request"""
    address: str = Field(..., min_length=56, max_length=56, description="Account address to flag")
    flag_type: str = Field(..., min_length=1, max_length=100, description="Flag type")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    reason: str = Field(..., min_length=1, description="Reason for flagging")
    evidence: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Supporting evidence")
    
    class Config:
        json_schema_extra = {
            "example": {
                "address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
                "flag_type": "suspicious_activity",
                "severity": "high",
                "reason": "Unusual transaction pattern detected",
                "evidence": {
                    "transaction_count": 1000,
                    "time_period": "24h",
                    "pattern": "rapid_movement"
                }
            }
        }


class FlagResponse(BaseModel):
    """Flag response"""
    id: int
    account_id: int
    account_address: str = Field(..., description="Flagged account address")
    flag_type: str = Field(..., description="Flag type")
    severity: str = Field(..., description="Flag severity")
    reason: str = Field(..., description="Flag reason")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")
    created_at: datetime = Field(..., description="Flag creation time")
    resolved_at: Optional[datetime] = Field(None, description="Resolution time")
    
    class Config:
        from_attributes = True
