"""Initial schema with comprehensive Stellar tracking

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-02-16 21:16:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create accounts table
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(length=56), nullable=False),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_accounts_address', 'accounts', ['address'], unique=True)
    op.create_index('idx_accounts_first_seen', 'accounts', ['first_seen'], unique=False)
    op.create_index('idx_accounts_last_seen', 'accounts', ['last_seen'], unique=False)
    op.create_index('idx_accounts_risk_score', 'accounts', ['risk_score'], unique=False)
    op.create_index(op.f('ix_accounts_id'), 'accounts', ['id'], unique=False)

    # Create assets table
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_code', sa.String(length=12), nullable=False),
        sa.Column('asset_issuer', sa.String(length=56), nullable=True),
        sa.Column('asset_type', sa.String(length=20), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_code', 'asset_issuer', name='uq_asset_code_issuer')
    )
    op.create_index('idx_assets_asset_code', 'assets', ['asset_code'], unique=False)
    op.create_index('idx_assets_asset_issuer', 'assets', ['asset_issuer'], unique=False)
    op.create_index(op.f('ix_assets_id'), 'assets', ['id'], unique=False)

    # Create watchlists table
    op.create_table(
        'watchlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_watchlists_name', 'watchlists', ['name'], unique=True)
    op.create_index(op.f('ix_watchlists_id'), 'watchlists', ['id'], unique=False)

    # Create account_balances table
    op.create_table(
        'account_balances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('balance', sa.Numeric(precision=20, scale=7), nullable=False),
        sa.Column('limit', sa.Numeric(precision=20, scale=7), nullable=True),
        sa.Column('buying_liabilities', sa.Numeric(precision=20, scale=7), nullable=True),
        sa.Column('selling_liabilities', sa.Numeric(precision=20, scale=7), nullable=True),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_account_balances_account_id', 'account_balances', ['account_id'], unique=False)
    op.create_index('idx_account_balances_asset_id', 'account_balances', ['asset_id'], unique=False)
    op.create_index('idx_account_balances_snapshot', 'account_balances', ['account_id', 'snapshot_at'], unique=False)
    op.create_index('idx_account_balances_snapshot_at', 'account_balances', ['snapshot_at'], unique=False)
    op.create_index(op.f('ix_account_balances_id'), 'account_balances', ['id'], unique=False)

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tx_hash', sa.String(length=64), nullable=False),
        sa.Column('ledger', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('source_account_id', sa.Integer(), nullable=True),
        sa.Column('fee_charged', sa.Integer(), nullable=False),
        sa.Column('operation_count', sa.Integer(), nullable=False),
        sa.Column('memo', sa.Text(), nullable=True),
        sa.Column('successful', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['source_account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tx_hash')
    )
    op.create_index('idx_transactions_created_at', 'transactions', ['created_at'], unique=False)
    op.create_index('idx_transactions_ledger', 'transactions', ['ledger'], unique=False)
    op.create_index('idx_transactions_ledger_created', 'transactions', ['ledger', 'created_at'], unique=False)
    op.create_index('idx_transactions_source_account_id', 'transactions', ['source_account_id'], unique=False)
    op.create_index('idx_transactions_source_created', 'transactions', ['source_account_id', 'created_at'], unique=False)
    op.create_index('idx_transactions_successful', 'transactions', ['successful'], unique=False)
    op.create_index('idx_transactions_tx_hash', 'transactions', ['tx_hash'], unique=True)
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)

    # Create counterparty_edges table
    op.create_table(
        'counterparty_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_account_id', sa.Integer(), nullable=False),
        sa.Column('to_account_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('tx_count', sa.Integer(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=20, scale=7), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['from_account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_account_id', 'to_account_id', 'asset_id', name='uq_counterparty_edge')
    )
    op.create_index('idx_counterparty_edges_asset_id', 'counterparty_edges', ['asset_id'], unique=False)
    op.create_index('idx_counterparty_edges_from_account_id', 'counterparty_edges', ['from_account_id'], unique=False)
    op.create_index('idx_counterparty_edges_last_seen', 'counterparty_edges', ['last_seen'], unique=False)
    op.create_index('idx_counterparty_edges_to_account_id', 'counterparty_edges', ['to_account_id'], unique=False)
    op.create_index(op.f('ix_counterparty_edges_id'), 'counterparty_edges', ['id'], unique=False)

    # Create flags table
    op.create_table(
        'flags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('flag_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_flags_account_id', 'flags', ['account_id'], unique=False)
    op.create_index('idx_flags_created_at', 'flags', ['created_at'], unique=False)
    op.create_index('idx_flags_flag_type', 'flags', ['flag_type'], unique=False)
    op.create_index('idx_flags_resolved_at', 'flags', ['resolved_at'], unique=False)
    op.create_index('idx_flags_severity', 'flags', ['severity'], unique=False)
    op.create_index('idx_flags_severity_created', 'flags', ['severity', 'created_at'], unique=False)
    op.create_index('idx_flags_unresolved', 'flags', ['account_id', 'resolved_at'], unique=False)
    op.create_index(op.f('ix_flags_id'), 'flags', ['id'], unique=False)

    # Create watchlist_members table
    op.create_table(
        'watchlist_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('watchlist_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['watchlist_id'], ['watchlists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('watchlist_id', 'account_id', name='uq_watchlist_member')
    )
    op.create_index('idx_watchlist_members_account_id', 'watchlist_members', ['account_id'], unique=False)
    op.create_index('idx_watchlist_members_added_at', 'watchlist_members', ['added_at'], unique=False)
    op.create_index('idx_watchlist_members_watchlist_id', 'watchlist_members', ['watchlist_id'], unique=False)
    op.create_index(op.f('ix_watchlist_members_id'), 'watchlist_members', ['id'], unique=False)

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('alert_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alerts_account_id', 'alerts', ['account_id'], unique=False)
    op.create_index('idx_alerts_acknowledged_at', 'alerts', ['acknowledged_at'], unique=False)
    op.create_index('idx_alerts_alert_type', 'alerts', ['alert_type'], unique=False)
    op.create_index('idx_alerts_asset_id', 'alerts', ['asset_id'], unique=False)
    op.create_index('idx_alerts_created_at', 'alerts', ['created_at'], unique=False)
    op.create_index('idx_alerts_severity', 'alerts', ['severity'], unique=False)
    op.create_index('idx_alerts_severity_created', 'alerts', ['severity', 'created_at'], unique=False)
    op.create_index('idx_alerts_unacknowledged', 'alerts', ['acknowledged_at', 'created_at'], unique=False)
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)

    # Create operations table
    op.create_table(
        'operations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('op_id', sa.String(length=64), nullable=False),
        sa.Column('tx_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('from_account_id', sa.Integer(), nullable=True),
        sa.Column('to_account_id', sa.Integer(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=20, scale=7), nullable=True),
        sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['from_account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['to_account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tx_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('op_id')
    )
    op.create_index('idx_operations_asset_id', 'operations', ['asset_id'], unique=False)
    op.create_index('idx_operations_created_at', 'operations', ['created_at'], unique=False)
    op.create_index('idx_operations_from_account_id', 'operations', ['from_account_id'], unique=False)
    op.create_index('idx_operations_from_to', 'operations', ['from_account_id', 'to_account_id'], unique=False)
    op.create_index('idx_operations_op_id', 'operations', ['op_id'], unique=True)
    op.create_index('idx_operations_to_account_id', 'operations', ['to_account_id'], unique=False)
    op.create_index('idx_operations_tx_id', 'operations', ['tx_id'], unique=False)
    op.create_index('idx_operations_type', 'operations', ['type'], unique=False)
    op.create_index('idx_operations_type_created', 'operations', ['type', 'created_at'], unique=False)
    op.create_index(op.f('ix_operations_id'), 'operations', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('operations')
    op.drop_table('alerts')
    op.drop_table('watchlist_members')
    op.drop_table('flags')
    op.drop_table('counterparty_edges')
    op.drop_table('transactions')
    op.drop_table('account_balances')
    op.drop_table('watchlists')
    op.drop_table('assets')
    op.drop_table('accounts')
