# Database Quick Reference

## Table Overview

| Table | Purpose | Key Columns | Indexes |
|-------|---------|-------------|---------|
| `accounts` | Account tracking | address, risk_score, label | address, risk_score, last_seen |
| `assets` | Asset registry | asset_code, asset_issuer | (asset_code, asset_issuer) |
| `account_balances` | Balance snapshots | account_id, asset_id, balance | account_id, snapshot_at |
| `transactions` | Transaction records | tx_hash, ledger, source_account_id | tx_hash, ledger, created_at |
| `operations` | Operation details | op_id, tx_id, type | op_id, type, from/to accounts |
| `counterparty_edges` | Transaction graph | from/to account_id, tx_count | from/to accounts, last_seen |
| `watchlists` | Monitoring lists | name, description | name |
| `watchlist_members` | List memberships | watchlist_id, account_id | (watchlist_id, account_id) |
| `flags` | Risk flags | account_id, severity, flag_type | severity, resolved_at |
| `alerts` | System alerts | alert_type, severity | severity, acknowledged_at |

## Common Queries

### Account Queries

```sql
-- Get account by address
SELECT * FROM accounts WHERE address = 'G...';

-- High-risk accounts
SELECT * FROM accounts WHERE risk_score > 75 ORDER BY risk_score DESC;

-- Recently active accounts
SELECT * FROM accounts WHERE last_seen > NOW() - INTERVAL '24 hours';
```

### Transaction Queries

```sql
-- Get transaction by hash
SELECT * FROM transactions WHERE tx_hash = 'abc123...';

-- Recent transactions
SELECT * FROM transactions ORDER BY created_at DESC LIMIT 100;

-- Transactions by ledger
SELECT * FROM transactions WHERE ledger = 12345;
```

### Operation Queries

```sql
-- Operations by type
SELECT * FROM operations WHERE type = 'payment' ORDER BY created_at DESC;

-- Operations between accounts
SELECT * FROM operations 
WHERE from_account_id = 1 AND to_account_id = 2;

-- Large operations
SELECT * FROM operations WHERE amount > 10000 ORDER BY amount DESC;
```

### Risk Queries

```sql
-- Unresolved flags
SELECT * FROM flags WHERE resolved_at IS NULL ORDER BY severity;

-- Accounts with multiple flags
SELECT account_id, COUNT(*) as flag_count 
FROM flags 
WHERE resolved_at IS NULL 
GROUP BY account_id 
HAVING COUNT(*) > 1;

-- Recent alerts
SELECT * FROM alerts 
WHERE created_at > NOW() - INTERVAL '1 hour' 
ORDER BY severity, created_at DESC;
```

## Python ORM Examples

### Query Accounts

```python
from app.db.models import Account
from sqlalchemy.orm import Session

# Get by address
account = session.query(Account).filter(
    Account.address == "G..."
).first()

# High risk accounts
high_risk = session.query(Account).filter(
    Account.risk_score > 75
).order_by(Account.risk_score.desc()).all()

# With relationships
account = session.query(Account).filter(
    Account.id == 1
).first()
balances = account.balances
flags = account.flags
```

### Create Records

```python
from app.db.models import Account, Transaction, Flag

# Create account
account = Account(
    address="GXXXXXXX...",
    label="Exchange",
    risk_score=25.0,
    metadata={"verified": True}
)
session.add(account)

# Create transaction
tx = Transaction(
    tx_hash="abc123...",
    ledger=12345,
    source_account_id=account.id,
    fee_charged=100,
    operation_count=1,
    successful=True
)
session.add(tx)

# Create flag
flag = Flag(
    account_id=account.id,
    flag_type="high_volume",
    severity="medium",
    reason="Unusual activity",
    evidence={"tx_count": 1000}
)
session.add(flag)

session.commit()
```

### Update Records

```python
# Update account
account = session.query(Account).filter(
    Account.address == "G..."
).first()
account.risk_score = 85.0
account.label = "High Risk Exchange"
session.commit()

# Resolve flag
flag = session.query(Flag).filter(Flag.id == 1).first()
flag.resolved_at = datetime.now()
session.commit()
```

### Complex Queries

```python
from sqlalchemy import func, and_

# Count operations by type
op_counts = session.query(
    Operation.type,
    func.count(Operation.id)
).group_by(Operation.type).all()

# Accounts with unresolved flags
accounts_with_flags = session.query(Account).join(Flag).filter(
    Flag.resolved_at.is_(None)
).distinct().all()

# Top counterparty relationships
top_edges = session.query(CounterpartyEdge).order_by(
    CounterpartyEdge.tx_count.desc()
).limit(10).all()
```

## FastAPI Endpoint Examples

### Account Endpoints

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Account
from app.schemas.schemas import AccountResponse

router = APIRouter()

@router.get("/accounts/{address}", response_model=AccountResponse)
def get_account(address: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(
        Account.address == address
    ).first()
    if not account:
        raise HTTPException(status_code=404)
    return account

@router.get("/accounts/high-risk", response_model=list[AccountResponse])
def get_high_risk_accounts(
    threshold: float = 75.0,
    db: Session = Depends(get_db)
):
    return db.query(Account).filter(
        Account.risk_score > threshold
    ).order_by(Account.risk_score.desc()).all()
```

## Migration Commands

```bash
# Check current version
alembic current

# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Show history
alembic history

# Create new migration
alembic revision --autogenerate -m "add new column"
```

## Useful SQL Functions

### Aggregations

```sql
-- Total transactions per account
SELECT 
    a.address,
    COUNT(t.id) as tx_count
FROM accounts a
LEFT JOIN transactions t ON t.source_account_id = a.id
GROUP BY a.id, a.address;

-- Average risk score
SELECT AVG(risk_score) FROM accounts;

-- Operation type distribution
SELECT type, COUNT(*) FROM operations GROUP BY type;
```

### Time-based Queries

```sql
-- Transactions per day
SELECT 
    DATE_TRUNC('day', created_at) as day,
    COUNT(*) as count
FROM transactions
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY day DESC;

-- Active accounts per hour
SELECT 
    DATE_TRUNC('hour', last_seen) as hour,
    COUNT(*) as active_accounts
FROM accounts
WHERE last_seen > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', last_seen);
```

### JSONB Queries

```sql
-- Query metadata
SELECT * FROM accounts 
WHERE metadata->>'verified' = 'true';

-- Check if key exists
SELECT * FROM accounts 
WHERE metadata ? 'domain';

-- Extract nested values
SELECT 
    address,
    metadata->'social'->>'twitter' as twitter
FROM accounts
WHERE metadata->'social' ? 'twitter';
```

## Index Hints

### Most Important Indexes

1. **accounts.address** - Primary lookup
2. **transactions.tx_hash** - Transaction lookup
3. **operations.op_id** - Operation lookup
4. **accounts.risk_score** - Risk filtering
5. **transactions.ledger** - Ledger sync
6. **operations.type** - Operation filtering
7. **flags.resolved_at** - Active flags
8. **alerts.acknowledged_at** - Active alerts

### Composite Indexes

1. **(ledger, created_at)** - Temporal transaction queries
2. **(type, created_at)** - Operation analysis
3. **(from_account_id, to_account_id)** - Counterparty queries
4. **(account_id, snapshot_at)** - Balance history

## Performance Tips

1. **Use indexes** - All foreign keys are indexed
2. **Limit results** - Always use LIMIT for large tables
3. **Use EXPLAIN** - Check query plans
4. **Batch inserts** - Use bulk operations
5. **Partition tables** - For very large datasets
6. **Vacuum regularly** - Maintain performance
7. **Monitor slow queries** - Use pg_stat_statements

## Data Types

| Column Type | SQL Type | Python Type | Notes |
|-------------|----------|-------------|-------|
| ID | INTEGER | int | Auto-increment |
| Address | VARCHAR(56) | str | Stellar address |
| Hash | VARCHAR(64) | str | Transaction/operation hash |
| Amount | NUMERIC(20,7) | Decimal | Precise amounts |
| Timestamp | TIMESTAMP | datetime | Timezone aware |
| Metadata | JSONB | dict | Flexible storage |
| Risk Score | FLOAT | float | 0-100 range |

## Environment Setup

```bash
# .env file
DATABASE_URL=postgresql://stellar_user:password@postgres:5432/stellar_explorer
REDIS_URL=redis://redis:6379/0

# Initialize
./scripts/init_db.sh

# Or manually
docker-compose exec api alembic upgrade head
```

## Backup & Restore

```bash
# Backup
docker-compose exec postgres pg_dump -U stellar_user stellar_explorer > backup.sql

# Restore
docker-compose exec -T postgres psql -U stellar_user stellar_explorer < backup.sql

# Backup specific table
docker-compose exec postgres pg_dump -U stellar_user -t accounts stellar_explorer > accounts_backup.sql
```

## Monitoring

```sql
-- Table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT 
    indexname,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Active connections
SELECT COUNT(*) FROM pg_stat_activity;
```
