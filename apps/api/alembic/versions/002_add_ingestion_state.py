"""Add ingestion_state table for durable checkpoints

Revision ID: 002_add_ingestion_state
Revises: 001_initial_schema
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_ingestion_state'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ingestion_state',
        sa.Column('stream_name', sa.String(length=255), primary_key=True),
        sa.Column('last_paging_token', sa.Text(), nullable=False),
        sa.Column('last_ledger', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
    )

    # Initialize default streams
    op.execute("""
        INSERT INTO ingestion_state (stream_name, last_paging_token, last_ledger)
        VALUES 
            ('transactions_global', 'now', NULL),
            ('operations_global', 'now', NULL)
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('ingestion_state')
