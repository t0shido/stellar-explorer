# Database Schema Documentation

## Overview

The Stellar Explorer database schema is designed for comprehensive blockchain analysis, risk assessment, and transaction monitoring. It uses PostgreSQL with JSONB support for flexible metadata storage.

## Entity Relationship Diagram

```
┌─────────────┐
│  accounts   │◄────┐
└─────┬───────┘     │
      │             │
      │ 1:N         │ N:1
      │             │
┌─────▼───────┐     │
│account_     │     │
│balances     │     │
└─────┬───────┘     │
      │ N:1         │
      │             │
┌─────▼───────┐     │
│   assets    │     │
└─────┬───────┘     │
      │             │
      │ 1:N         │
      │             │
┌─────▼───────┐     │
│ operations  │─────┘
└─────┬───────┘
      │ N:1
      │
┌─────▼───────┐
│transactions │
└─────────────┘
```

## Tables

### 1. accounts

Stores Stellar account information with risk tracking capabilities.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `address` (VARCHAR(56), UNIQUE, NOT NULL): Stellar account address (G...)
- `first_seen` (TIMESTAMP): When account was first observed
- `last_seen` (TIMESTAMP): Last activity timestamp
- `label` (VARCHAR(255)): Human-readable label/name
- `risk_score` (FLOAT): Risk assessment score (0-100)
- `metadata` (JSONB): Flexible metadata storage

**Indexes:**
- `idx_accounts_address` (UNIQUE): Fast account lookups
- `idx_accounts_first_seen`: Time-based queries
- `idx_accounts_last_seen`: Activity tracking
- `idx_accounts_risk_score`: Risk-based filtering

**Relationships:**
- 1:N with `account_balances`
- 1:N with `transactions` (as source)
- 1:N with `operations` (as from/to)
- 1:N with `counterparty_edges` (as from/to)
- 1:N with `watchlist_members`
- 1:N with `flags`
- 1:N with `alerts`

**Use Cases:**
- Account discovery and tracking
- Risk scoring and monitoring
- Label management for known entities
- Activity timeline analysis

---

### 2. assets

Stores Stellar asset definitions.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `asset_code` (VARCHAR(12), NOT NULL): Asset code (e.g., USD, BTC)
- `asset_issuer` (VARCHAR(56)): Issuer account address
- `asset_type` (VARCHAR(20)): native, credit_alphanum4, credit_alphanum12
- `metadata` (JSONB): Asset metadata (domain, description, etc.)

**Indexes:**
- `idx_assets_asset_code`: Fast asset code lookups
- `idx_assets_asset_issuer`: Issuer-based queries
- `uq_asset_code_issuer` (UNIQUE): Ensures unique asset definition

**Relationships:**
- 1:N with `account_balances`
- 1:N with `operations`
- 1:N with `counterparty_edges`
- 1:N with `alerts`

**Use Cases:**
- Asset registry
- Asset metadata management
- Issuer tracking
- Asset-specific analytics

---

### 3. account_balances

Tracks account balance snapshots for each asset over time.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `account_id` (INTEGER, FK → accounts.id, NOT NULL): Account reference
- `asset_id` (INTEGER, FK → assets.id, NULLABLE): Asset reference (NULL for native XLM)
- `balance` (NUMERIC(20,7), NOT NULL): Current balance
- `limit` (NUMERIC(20,7)): Trustline limit
- `buying_liabilities` (NUMERIC(20,7)): Buying liabilities
- `selling_liabilities` (NUMERIC(20,7)): Selling liabilities
- `snapshot_at` (TIMESTAMP): Snapshot timestamp

**Indexes:**
- `idx_account_balances_account_id`: Account-based queries
- `idx_account_balances_asset_id`: Asset-based queries
- `idx_account_balances_snapshot`: Time-series queries
- `idx_account_balances_snapshot_at`: Temporal analysis

**Relationships:**
- N:1 with `accounts`
- N:1 with `assets`

**Use Cases:**
- Balance history tracking
- Portfolio analysis
- Liquidity monitoring
- Trustline management

---

### 4. transactions

Stores Stellar transaction records.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `tx_hash` (VARCHAR(64), UNIQUE, NOT NULL): Transaction hash
- `ledger` (INTEGER, NOT NULL): Ledger sequence number
- `created_at` (TIMESTAMP): Transaction timestamp
- `source_account_id` (INTEGER, FK → accounts.id): Source account
- `fee_charged` (INTEGER, NOT NULL): Fee in stroops
- `operation_count` (INTEGER, NOT NULL): Number of operations
- `memo` (TEXT): Transaction memo
- `successful` (BOOLEAN): Transaction success status

**Indexes:**
- `idx_transactions_tx_hash` (UNIQUE): Fast transaction lookups
- `idx_transactions_ledger`: Ledger-based queries
- `idx_transactions_created_at`: Time-based queries
- `idx_transactions_ledger_created`: Combined temporal queries
- `idx_transactions_source_account_id`: Source account queries
- `idx_transactions_source_created`: Account activity timeline
- `idx_transactions_successful`: Success/failure filtering

**Relationships:**
- N:1 with `accounts` (source)
- 1:N with `operations`

**Use Cases:**
- Transaction history
- Fee analysis
- Success rate monitoring
- Ledger synchronization

---

### 5. operations

Stores individual operations within transactions.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `op_id` (VARCHAR(64), UNIQUE, NOT NULL): Operation ID
- `tx_id` (INTEGER, FK → transactions.id, NOT NULL): Parent transaction
- `type` (VARCHAR(50), NOT NULL): Operation type (payment, create_account, etc.)
- `from_account_id` (INTEGER, FK → accounts.id, NULLABLE): Source account
- `to_account_id` (INTEGER, FK → accounts.id, NULLABLE): Destination account
- `asset_id` (INTEGER, FK → assets.id, NULLABLE): Asset involved
- `amount` (NUMERIC(20,7)): Operation amount
- `raw` (JSONB, NOT NULL): Complete operation data
- `created_at` (TIMESTAMP): Operation timestamp

**Indexes:**
- `idx_operations_op_id` (UNIQUE): Fast operation lookups
- `idx_operations_tx_id`: Transaction-based queries
- `idx_operations_type`: Operation type filtering
- `idx_operations_type_created`: Type-based temporal queries
- `idx_operations_from_account_id`: Source account queries
- `idx_operations_to_account_id`: Destination account queries
- `idx_operations_from_to`: Counterparty analysis
- `idx_operations_asset_id`: Asset-based queries
- `idx_operations_created_at`: Time-based queries

**Relationships:**
- N:1 with `transactions`
- N:1 with `accounts` (from)
- N:1 with `accounts` (to)
- N:1 with `assets`

**Use Cases:**
- Operation-level analysis
- Payment flow tracking
- Operation type statistics
- Detailed transaction inspection

---

### 6. counterparty_edges

Graph edges representing transaction relationships between accounts.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `from_account_id` (INTEGER, FK → accounts.id, NOT NULL): Source account
- `to_account_id` (INTEGER, FK → accounts.id, NOT NULL): Destination account
- `asset_id` (INTEGER, FK → assets.id, NULLABLE): Asset type (NULL for all)
- `tx_count` (INTEGER, NOT NULL): Number of transactions
- `total_amount` (NUMERIC(20,7)): Cumulative amount transferred
- `last_seen` (TIMESTAMP): Last transaction timestamp

**Indexes:**
- `idx_counterparty_edges_from_account_id`: Source queries
- `idx_counterparty_edges_to_account_id`: Destination queries
- `idx_counterparty_edges_asset_id`: Asset-specific edges
- `idx_counterparty_edges_last_seen`: Activity tracking
- `uq_counterparty_edge` (UNIQUE): Prevents duplicate edges

**Relationships:**
- N:1 with `accounts` (from)
- N:1 with `accounts` (to)
- N:1 with `assets`

**Use Cases:**
- Network graph analysis
- Counterparty risk assessment
- Transaction pattern detection
- Money flow visualization

---

### 7. watchlists

Named collections for monitoring specific accounts.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `name` (VARCHAR(255), UNIQUE, NOT NULL): Watchlist name
- `description` (TEXT): Watchlist description

**Indexes:**
- `idx_watchlists_name` (UNIQUE): Fast watchlist lookups

**Relationships:**
- 1:N with `watchlist_members`

**Use Cases:**
- Organized account monitoring
- Compliance tracking
- Investigation management
- Custom alert groups

---

### 8. watchlist_members

Association between watchlists and accounts.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `watchlist_id` (INTEGER, FK → watchlists.id, NOT NULL): Watchlist reference
- `account_id` (INTEGER, FK → accounts.id, NOT NULL): Account reference
- `reason` (TEXT): Reason for inclusion
- `added_at` (TIMESTAMP): When added to watchlist

**Indexes:**
- `idx_watchlist_members_watchlist_id`: Watchlist-based queries
- `idx_watchlist_members_account_id`: Account-based queries
- `idx_watchlist_members_added_at`: Temporal queries
- `uq_watchlist_member` (UNIQUE): Prevents duplicate memberships

**Relationships:**
- N:1 with `watchlists`
- N:1 with `accounts`

**Use Cases:**
- Watchlist membership management
- Account categorization
- Audit trail for monitoring

---

### 9. flags

Risk flags and compliance markers for accounts.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `account_id` (INTEGER, FK → accounts.id, NOT NULL): Flagged account
- `flag_type` (VARCHAR(100), NOT NULL): Flag category
- `severity` (VARCHAR(20), NOT NULL): low, medium, high, critical
- `reason` (TEXT, NOT NULL): Flag justification
- `evidence` (JSONB): Supporting evidence
- `created_at` (TIMESTAMP): Flag creation time
- `resolved_at` (TIMESTAMP, NULLABLE): Resolution timestamp

**Indexes:**
- `idx_flags_account_id`: Account-based queries
- `idx_flags_flag_type`: Type-based filtering
- `idx_flags_severity`: Severity-based filtering
- `idx_flags_severity_created`: Priority sorting
- `idx_flags_created_at`: Temporal queries
- `idx_flags_resolved_at`: Resolution tracking
- `idx_flags_unresolved`: Active flags queries

**Relationships:**
- N:1 with `accounts`

**Use Cases:**
- Risk flagging
- Compliance tracking
- Investigation workflow
- Audit trail

**Flag Types Examples:**
- `suspicious_activity`
- `high_volume`
- `sanctioned_entity`
- `mixer_interaction`
- `rapid_movement`

---

### 10. alerts

System-generated alerts for monitoring and notifications.

**Columns:**
- `id` (INTEGER, PK): Auto-incrementing primary key
- `account_id` (INTEGER, FK → accounts.id, NULLABLE): Related account
- `asset_id` (INTEGER, FK → assets.id, NULLABLE): Related asset
- `alert_type` (VARCHAR(100), NOT NULL): Alert category
- `severity` (VARCHAR(20), NOT NULL): info, warning, error, critical
- `payload` (JSONB, NOT NULL): Alert details
- `created_at` (TIMESTAMP): Alert creation time
- `acknowledged_at` (TIMESTAMP, NULLABLE): Acknowledgment timestamp

**Indexes:**
- `idx_alerts_account_id`: Account-based queries
- `idx_alerts_asset_id`: Asset-based queries
- `idx_alerts_alert_type`: Type-based filtering
- `idx_alerts_severity`: Severity-based filtering
- `idx_alerts_severity_created`: Priority sorting
- `idx_alerts_created_at`: Temporal queries
- `idx_alerts_acknowledged_at`: Acknowledgment tracking
- `idx_alerts_unacknowledged`: Active alerts queries

**Relationships:**
- N:1 with `accounts`
- N:1 with `assets`

**Use Cases:**
- Real-time monitoring
- Notification system
- Alert management dashboard
- Incident response

**Alert Types Examples:**
- `large_transaction`
- `new_trustline`
- `account_created`
- `threshold_exceeded`
- `pattern_detected`

---

## Data Types

### JSONB Fields

All JSONB fields support flexible schema-less data storage:

**accounts.metadata:**
```json
{
  "domain": "example.com",
  "verified": true,
  "tags": ["exchange", "verified"],
  "social": {
    "twitter": "@example"
  }
}
```

**assets.metadata:**
```json
{
  "name": "US Dollar",
  "description": "Tokenized USD",
  "image": "https://...",
  "conditions": "https://..."
}
```

**operations.raw:**
```json
{
  "type": "payment",
  "from": "G...",
  "to": "G...",
  "asset": {"code": "USD", "issuer": "G..."},
  "amount": "100.0000000"
}
```

**flags.evidence:**
```json
{
  "transactions": ["hash1", "hash2"],
  "pattern": "rapid_movement",
  "confidence": 0.85,
  "related_accounts": ["G..."]
}
```

**alerts.payload:**
```json
{
  "threshold": 10000,
  "actual": 15000,
  "transaction_hash": "abc123...",
  "triggered_rule": "large_payment"
}
```

---

## Query Patterns

### Common Queries

**1. Get account with recent activity:**
```sql
SELECT * FROM accounts 
WHERE last_seen > NOW() - INTERVAL '24 hours'
ORDER BY last_seen DESC;
```

**2. Find high-risk accounts:**
```sql
SELECT * FROM accounts 
WHERE risk_score > 75 
ORDER BY risk_score DESC;
```

**3. Get unresolved flags:**
```sql
SELECT f.*, a.address 
FROM flags f
JOIN accounts a ON f.account_id = a.id
WHERE f.resolved_at IS NULL
ORDER BY f.severity DESC, f.created_at DESC;
```

**4. Transaction flow between accounts:**
```sql
SELECT ce.*, 
       a1.address as from_address,
       a2.address as to_address,
       ast.asset_code
FROM counterparty_edges ce
JOIN accounts a1 ON ce.from_account_id = a1.id
JOIN accounts a2 ON ce.to_account_id = a2.id
LEFT JOIN assets ast ON ce.asset_id = ast.id
WHERE ce.tx_count > 10
ORDER BY ce.total_amount DESC;
```

**5. Recent operations by type:**
```sql
SELECT type, COUNT(*), SUM(amount) as total_amount
FROM operations
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY type
ORDER BY COUNT(*) DESC;
```

---

## Performance Considerations

### Index Strategy

1. **Temporal Indexes**: All timestamp columns are indexed for time-range queries
2. **Foreign Keys**: All FK columns have indexes for join performance
3. **Composite Indexes**: Multi-column indexes for common query patterns
4. **Unique Constraints**: Prevent duplicates and provide fast lookups

### Partitioning Recommendations

For high-volume deployments, consider partitioning:

- `transactions`: By ledger range or created_at (monthly)
- `operations`: By created_at (monthly)
- `account_balances`: By snapshot_at (monthly)
- `alerts`: By created_at (monthly, with archival)

### Maintenance

```sql
-- Regular vacuum and analyze
VACUUM ANALYZE accounts;
VACUUM ANALYZE transactions;
VACUUM ANALYZE operations;

-- Reindex for performance
REINDEX TABLE accounts;
REINDEX TABLE transactions;
```

---

## Migration Commands

```bash
# Create initial migration
docker-compose exec api alembic upgrade head

# Check current version
docker-compose exec api alembic current

# Rollback one version
docker-compose exec api alembic downgrade -1

# Show migration history
docker-compose exec api alembic history
```

---

## Security Considerations

1. **Sensitive Data**: Use `metadata` JSONB fields for PII with encryption at rest
2. **Access Control**: Implement row-level security for multi-tenant scenarios
3. **Audit Logging**: Track all modifications to `flags` and `watchlist_members`
4. **Data Retention**: Implement archival strategy for old `alerts` and `operations`

---

## Future Enhancements

- Add full-text search on `accounts.label` and `accounts.metadata`
- Implement TimescaleDB for time-series optimization
- Add materialized views for common aggregations
- Implement graph database integration for network analysis
