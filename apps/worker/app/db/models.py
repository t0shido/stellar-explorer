"""
Database models for worker (imported from API)
"""
# Import models from API to avoid duplication
# These should match the API models exactly

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean, Text,
    ForeignKey, Numeric, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Account(Base):
    """Stellar account model"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(56), unique=True, nullable=False, index=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_seen = Column(DateTime(timezone=True), onupdate=func.now(), index=True)
    label = Column(String(255))
    risk_score = Column(Float, default=0.0, index=True)
    meta_data = Column(JSONB, default=dict)


class Asset(Base):
    """Stellar asset model"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(12), nullable=False, index=True)
    asset_issuer = Column(String(56), index=True)
    asset_type = Column(String(20))
    meta_data = Column(JSONB, default=dict)


class AccountBalance(Base):
    """Account balance snapshot"""
    __tablename__ = "account_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id', ondelete='CASCADE'), nullable=True, index=True)
    balance = Column(Numeric(20, 7), nullable=False, default=0)
    limit = Column(Numeric(20, 7))
    buying_liabilities = Column(Numeric(20, 7), default=0)
    selling_liabilities = Column(Numeric(20, 7), default=0)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Transaction(Base):
    """Stellar transaction model"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    tx_hash = Column(String(64), unique=True, nullable=False, index=True)
    ledger = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    source_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), index=True)
    fee_charged = Column(Integer, nullable=False)
    operation_count = Column(Integer, nullable=False, default=1)
    memo = Column(Text)
    successful = Column(Boolean, default=True, index=True)


class Operation(Base):
    """Stellar operation model"""
    __tablename__ = "operations"
    
    id = Column(Integer, primary_key=True, index=True)
    op_id = Column(String(64), unique=True, nullable=False, index=True)
    tx_id = Column(Integer, ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    from_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True, index=True)
    to_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id', ondelete='SET NULL'), nullable=True, index=True)
    amount = Column(Numeric(20, 7))
    raw = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class CounterpartyEdge(Base):
    """Transaction graph edge"""
    __tablename__ = "counterparty_edges"
    
    id = Column(Integer, primary_key=True, index=True)
    from_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    to_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id', ondelete='SET NULL'), nullable=True, index=True)
    tx_count = Column(Integer, default=1, nullable=False)
    total_amount = Column(Numeric(20, 7), default=0)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)


class Watchlist(Base):
    """Watchlist for monitoring"""
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)


class WatchlistMember(Base):
    """Watchlist membership"""
    __tablename__ = "watchlist_members"
    
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey('watchlists.id', ondelete='CASCADE'), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    reason = Column(Text)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Flag(Base):
    """Risk flag"""
    __tablename__ = "flags"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    flag_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    evidence = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True, index=True)


class Alert(Base):
    """System alert"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id', ondelete='SET NULL'), nullable=True, index=True)
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True, index=True)
