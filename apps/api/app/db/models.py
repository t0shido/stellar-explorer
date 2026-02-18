from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean, Text,
    ForeignKey, Numeric, Index, UniqueConstraint, BigInteger
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Account(Base):
    """Stellar account model with risk tracking"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(56), unique=True, nullable=False, index=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_seen = Column(DateTime(timezone=True), onupdate=func.now(), index=True)
    label = Column(String(255))
    risk_score = Column(Float, default=0.0, index=True)
    meta_data = Column(JSONB, default=dict)
    
    # Relationships
    balances = relationship("AccountBalance", back_populates="account", cascade="all, delete-orphan")
    transactions_sent = relationship("Transaction", foreign_keys="Transaction.source_account_id", back_populates="source_account")
    operations_from = relationship("Operation", foreign_keys="Operation.from_account_id", back_populates="from_account")
    operations_to = relationship("Operation", foreign_keys="Operation.to_account_id", back_populates="to_account")
    edges_from = relationship("CounterpartyEdge", foreign_keys="CounterpartyEdge.from_account_id", back_populates="from_account")
    edges_to = relationship("CounterpartyEdge", foreign_keys="CounterpartyEdge.to_account_id", back_populates="to_account")
    watchlist_memberships = relationship("WatchlistMember", back_populates="account", cascade="all, delete-orphan")
    flags = relationship("Flag", back_populates="account", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="account")

    __table_args__ = (
        Index('idx_accounts_risk_score', 'risk_score'),
        Index('idx_accounts_last_seen', 'last_seen'),
    )

class IngestionState(Base):
    """Durable ingestion checkpoints"""
    __tablename__ = "ingestion_state"

    stream_name = Column(String(255), primary_key=True)
    last_paging_token = Column(Text, nullable=False)
    last_ledger = Column(BigInteger)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    error_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text)


class Asset(Base):
    """Stellar asset model"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(12), nullable=False, index=True)
    asset_issuer = Column(String(56), index=True)
    asset_type = Column(String(20))  # native, credit_alphanum4, credit_alphanum12
    meta_data = Column(JSONB, default=dict)
    
    # Relationships
    balances = relationship("AccountBalance", back_populates="asset")
    operations = relationship("Operation", back_populates="asset")
    edges = relationship("CounterpartyEdge", back_populates="asset")
    alerts = relationship("Alert", back_populates="asset")
    
    __table_args__ = (
        UniqueConstraint('asset_code', 'asset_issuer', name='uq_asset_code_issuer'),
    )


class AccountBalance(Base):
    """Account balance snapshot for specific asset"""
    __tablename__ = "account_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id', ondelete='CASCADE'), nullable=True, index=True)  # NULL for native XLM
    balance = Column(Numeric(20, 7), nullable=False, default=0)
    limit = Column(Numeric(20, 7))
    buying_liabilities = Column(Numeric(20, 7), default=0)
    selling_liabilities = Column(Numeric(20, 7), default=0)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    account = relationship("Account", back_populates="balances")
    asset = relationship("Asset", back_populates="balances")
    
    __table_args__ = (
        Index('idx_account_balances_snapshot', 'account_id', 'snapshot_at'),
    )


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
    
    # Relationships
    source_account = relationship("Account", foreign_keys=[source_account_id], back_populates="transactions_sent")
    operations = relationship("Operation", back_populates="transaction", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_transactions_ledger_created', 'ledger', 'created_at'),
        Index('idx_transactions_source_created', 'source_account_id', 'created_at'),
    )


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
    
    # Relationships
    transaction = relationship("Transaction", back_populates="operations")
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="operations_from")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="operations_to")
    asset = relationship("Asset", back_populates="operations")
    
    __table_args__ = (
        Index('idx_operations_type_created', 'type', 'created_at'),
        Index('idx_operations_from_to', 'from_account_id', 'to_account_id'),
    )


class CounterpartyEdge(Base):
    """Graph edge representing transaction relationships between accounts"""
    __tablename__ = "counterparty_edges"
    
    id = Column(Integer, primary_key=True, index=True)
    from_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    to_account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id', ondelete='SET NULL'), nullable=True, index=True)
    tx_count = Column(Integer, default=1, nullable=False)
    total_amount = Column(Numeric(20, 7), default=0)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    
    # Relationships
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="edges_from")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="edges_to")
    asset = relationship("Asset", back_populates="edges")
    
    __table_args__ = (
        UniqueConstraint('from_account_id', 'to_account_id', 'asset_id', name='uq_counterparty_edge'),
        Index('idx_counterparty_edges_last_seen', 'last_seen'),
    )


class Watchlist(Base):
    """Watchlist for monitoring specific accounts"""
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Relationships
    members = relationship("WatchlistMember", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistMember(Base):
    """Account membership in a watchlist"""
    __tablename__ = "watchlist_members"
    
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey('watchlists.id', ondelete='CASCADE'), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    reason = Column(Text)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="members")
    account = relationship("Account", back_populates="watchlist_memberships")
    
    __table_args__ = (
        UniqueConstraint('watchlist_id', 'account_id', name='uq_watchlist_member'),
    )


class Flag(Base):
    """Risk flag for an account"""
    __tablename__ = "flags"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    flag_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    reason = Column(Text, nullable=False)
    evidence = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    account = relationship("Account", back_populates="flags")
    
    __table_args__ = (
        Index('idx_flags_severity_created', 'severity', 'created_at'),
        Index('idx_flags_unresolved', 'account_id', 'resolved_at'),
    )


class Alert(Base):
    """System alert for monitoring and notifications"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id', ondelete='SET NULL'), nullable=True, index=True)
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # info, warning, error, critical
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    account = relationship("Account", back_populates="alerts")
    asset = relationship("Asset", back_populates="alerts")
    
    __table_args__ = (
        Index('idx_alerts_severity_created', 'severity', 'created_at'),
        Index('idx_alerts_unacknowledged', 'acknowledged_at', 'created_at'),
    )
