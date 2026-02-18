# Ingestion Module - Quick Start Guide

## 🚀 Quick Start

### 1. Start Services

```bash
cd stellar_explorer
make up
./scripts/init_db.sh
```

### 2. Test Ingestion

```bash
# Ingest a test account
curl -X POST "http://localhost:8000/api/v1/ingest/account/GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H"

# Ingest latest transactions
curl -X POST "http://localhost:8000/api/v1/ingest/transactions/latest?limit=10"
```

### 3. View Results

```bash
# Check database
docker-compose exec postgres psql -U stellar_user -d stellar_explorer

# Query accounts
SELECT address, risk_score, last_seen FROM accounts;

# Query transactions
SELECT tx_hash, ledger, successful FROM transactions ORDER BY created_at DESC LIMIT 10;
```

## 📖 API Examples

### Ingest Account

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/account/GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "success": true,
  "account": {
    "id": 1,
    "address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
    "risk_score": 0.0
  },
  "balances_created": 2,
  "assets_created": 1
}
```

### Ingest Transactions

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/transactions/latest?limit=50" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "success": true,
  "transactions_created": 50,
  "operations_created": 150,
  "limit": 50
}
```

### Refresh Watchlist

```bash
# First, create a watchlist and add accounts
curl -X POST "http://localhost:8000/api/v1/ingest/watchlist/refresh" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "success": true,
  "total_accounts": 10,
  "successful": 10,
  "failed": 0,
  "balances_updated": 20,
  "transactions_ingested": 50
}
```

## 🧪 Running Tests

```bash
# Run all tests
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=app.services --cov-report=term-missing

# Run specific test file
docker-compose exec api pytest tests/test_ingestion_service.py -v

# Run with detailed output
docker-compose exec api pytest -vv --tb=short
```

## 🐍 Python Usage

### Using Horizon Client

```python
from app.services.horizon_client import HorizonClient

# Fetch account data
with HorizonClient() as client:
    account = client.fetch_account("GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H")
    print(f"Balances: {len(account['balances'])}")
    
    # Fetch transactions
    txs = client.fetch_transactions(limit=100)
    print(f"Transactions: {len(txs['_embedded']['records'])}")
```

### Using Ingestion Service

```python
from app.services.ingestion_service import IngestionService
from app.db.database import SessionLocal

# Ingest account
db = SessionLocal()
try:
    with IngestionService(db) as service:
        account, balances, assets = service.ingest_account(
            "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H"
        )
        print(f"Created {balances} balances and {assets} assets")
finally:
    db.close()
```

### Batch Ingestion

```python
from app.services.ingestion_service import IngestionService
from app.db.database import SessionLocal

addresses = [
    "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
    "GDUKMGUGDZQK6YHYA5Z6AY2G4XDSZPSZ3SW5UN3ARVMO6QSRDWP5YLEX",
    # ... more addresses
]

db = SessionLocal()
try:
    with IngestionService(db) as service:
        for address in addresses:
            try:
                account, balances, assets = service.ingest_account(address)
                print(f"✓ {address}: {balances} balances")
            except Exception as e:
                print(f"✗ {address}: {e}")
finally:
    db.close()
```

## 🔍 Monitoring

### Check Logs

```bash
# API logs
docker-compose logs -f api

# Filter for ingestion logs
docker-compose logs api | grep "ingestion"

# Check for errors
docker-compose logs api | grep "ERROR"
```

### Database Queries

```sql
-- Recent ingestions
SELECT address, last_seen, risk_score 
FROM accounts 
ORDER BY last_seen DESC 
LIMIT 10;

-- Transaction stats
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as tx_count,
    SUM(CASE WHEN successful THEN 1 ELSE 0 END) as successful
FROM transactions
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- Operation types
SELECT type, COUNT(*) as count
FROM operations
GROUP BY type
ORDER BY count DESC;

-- Asset distribution
SELECT asset_code, COUNT(DISTINCT account_id) as holders
FROM account_balances ab
JOIN assets a ON ab.asset_id = a.id
GROUP BY asset_code
ORDER BY holders DESC;
```

## ⚙️ Configuration

### Environment Variables

```bash
# .env file
STELLAR_NETWORK=testnet
STELLAR_HORIZON_URL=https://horizon-testnet.stellar.org
DATABASE_URL=postgresql://stellar_user:stellar_password@postgres:5432/stellar_explorer
LOG_LEVEL=INFO
```

### Switch to Public Network

```bash
# Update .env
STELLAR_NETWORK=public
STELLAR_HORIZON_URL=https://horizon.stellar.org

# Restart services
make restart
```

## 🐛 Troubleshooting

### Account Not Found (404)

```bash
# Verify account exists
curl "https://horizon-testnet.stellar.org/accounts/GXXXXXXX"

# Check network configuration
docker-compose exec api env | grep STELLAR
```

### Connection Errors

```bash
# Check Horizon status
curl "https://horizon-testnet.stellar.org/"

# Test connectivity
docker-compose exec api ping horizon-testnet.stellar.org

# Check logs
docker-compose logs api | grep "HorizonClient"
```

### Database Errors

```bash
# Check database connection
docker-compose exec postgres psql -U stellar_user -d stellar_explorer -c "SELECT 1;"

# Check migrations
docker-compose exec api alembic current

# Run migrations
docker-compose exec api alembic upgrade head
```

### Slow Performance

```bash
# Check database indexes
docker-compose exec postgres psql -U stellar_user -d stellar_explorer -c "\di"

# Analyze query performance
docker-compose exec postgres psql -U stellar_user -d stellar_explorer -c "EXPLAIN ANALYZE SELECT * FROM accounts WHERE address = 'GXXX';"

# Check table sizes
docker-compose exec postgres psql -U stellar_user -d stellar_explorer -c "SELECT pg_size_pretty(pg_total_relation_size('transactions'));"
```

## 📊 Example Workflows

### 1. Initial Data Load

```bash
# Ingest recent transactions
curl -X POST "http://localhost:8000/api/v1/ingest/transactions/latest?limit=200"

# Check results
docker-compose exec postgres psql -U stellar_user -d stellar_explorer -c "SELECT COUNT(*) FROM transactions;"
```

### 2. Monitor Specific Accounts

```bash
# Create watchlist (via SQL or API)
docker-compose exec postgres psql -U stellar_user -d stellar_explorer << EOF
INSERT INTO watchlists (name, description) VALUES ('High Value', 'High value accounts');
INSERT INTO watchlist_members (watchlist_id, account_id, reason) 
SELECT 1, id, 'High value' FROM accounts WHERE risk_score > 50;
EOF

# Refresh watchlist
curl -X POST "http://localhost:8000/api/v1/ingest/watchlist/refresh"
```

### 3. Continuous Ingestion

```bash
# Create a simple ingestion script
cat > ingest_loop.sh << 'EOF'
#!/bin/bash
while true; do
    echo "Ingesting transactions..."
    curl -X POST "http://localhost:8000/api/v1/ingest/transactions/latest?limit=100"
    echo ""
    sleep 60
done
EOF

chmod +x ingest_loop.sh
./ingest_loop.sh
```

## 📚 Additional Resources

- **Full Documentation**: [docs/INGESTION_MODULE.md](docs/INGESTION_MODULE.md)
- **Database Schema**: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)
- **API Reference**: http://localhost:8000/docs
- **Stellar Documentation**: https://developers.stellar.org/

## ✅ Verification Checklist

- [ ] Services running: `docker-compose ps`
- [ ] Database initialized: `./scripts/init_db.sh`
- [ ] API accessible: `curl http://localhost:8000/health`
- [ ] Tests passing: `docker-compose exec api pytest`
- [ ] Account ingestion works
- [ ] Transaction ingestion works
- [ ] Logs show no errors

## 🎯 Next Steps

1. **Set up monitoring**: Add Grafana dashboards
2. **Schedule ingestion**: Use Celery beat for periodic tasks
3. **Add alerts**: Configure alerts for failed ingestions
4. **Optimize queries**: Add indexes for common queries
5. **Scale up**: Increase worker count for higher throughput

## 💡 Tips

- Use `limit=200` for maximum efficiency (Horizon API limit)
- Run ingestion during off-peak hours for large batches
- Monitor retry rates to detect API issues early
- Use background tasks for watchlist refresh with many accounts
- Store raw payloads in JSONB for debugging and auditing
- Test with testnet before switching to public network
