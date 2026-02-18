# Stellar Horizon Ingestion Module

## Overview

The ingestion module provides a robust, production-ready system for fetching data from the Stellar Horizon API and storing it in the PostgreSQL database. It features retry logic, structured logging, idempotent operations, and comprehensive test coverage.

## Architecture

```
┌─────────────────┐
│  API Endpoints  │
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Ingestion       │
│ Service         │
│ (Business Logic)│
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌─────────────┐  ┌──────────┐
│   Horizon   │  │PostgreSQL│
│   Client    │  │ Database │
│ (API Calls) │  │          │
└─────────────┘  └──────────┘
```

## Components

### 1. Horizon Client (`horizon_client.py`)

Low-level client for interacting with Stellar Horizon API.

**Features:**
- Automatic retry with exponential backoff
- Structured logging
- Error handling and custom exceptions
- Connection pooling
- Context manager support

**Methods:**
- `fetch_account(address)` - Get account data
- `fetch_transactions(limit, cursor, order)` - Get transactions
- `fetch_transaction_operations(tx_hash)` - Get operations for a transaction
- `fetch_account_transactions(address, limit, cursor)` - Get account transactions

**Retry Configuration:**
- Max attempts: 3
- Wait strategy: Exponential (2s, 4s, 8s)
- Retries on: Connection errors, timeouts, bad responses

**Example:**
```python
from app.services.horizon_client import HorizonClient

with HorizonClient() as client:
    account_data = client.fetch_account("GXXXXXXX...")
    print(f"Balance: {account_data['balances']}")
```

### 2. Ingestion Service (`ingestion_service.py`)

High-level service for data ingestion with business logic.

**Features:**
- Idempotent operations (safe to run multiple times)
- Automatic account/asset creation
- Counterparty edge tracking
- JSONB metadata storage
- Transaction management (commit/rollback)

**Methods:**

#### `ingest_account(address)`
Fetches and stores account data including balances and trustlines.

**Returns:** `(Account, balances_created, assets_created)`

**Idempotency:** Updates existing accounts, creates new ones

**Example:**
```python
from app.services.ingestion_service import IngestionService

with IngestionService(db) as service:
    account, balances, assets = service.ingest_account("GXXXXXXX...")
    print(f"Created {balances} balances and {assets} assets")
```

#### `ingest_latest_transactions(limit)`
Fetches and stores latest transactions with operations.

**Returns:** `(transactions_created, operations_created)`

**Idempotency:** Skips transactions that already exist

**Example:**
```python
with IngestionService(db) as service:
    txs, ops = service.ingest_latest_transactions(limit=100)
    print(f"Ingested {txs} transactions with {ops} operations")
```

#### `ingest_watchlist_accounts()`
Refreshes data for all accounts in watchlists.

**Returns:** Summary dictionary with counts

**Example:**
```python
with IngestionService(db) as service:
    summary = service.ingest_watchlist_accounts()
    print(f"Updated {summary['successful']} accounts")
```

### 3. API Endpoints (`endpoints/ingestion.py`)

RESTful API endpoints for triggering ingestion.

**Endpoints:**

#### `POST /api/v1/ingest/account/{address}`
Ingest single account data.

**Response:**
```json
{
  "success": true,
  "account": {
    "id": 1,
    "address": "GXXXXXXX...",
    "risk_score": 0.0
  },
  "balances_created": 2,
  "assets_created": 1
}
```

**Errors:**
- 404: Account not found on network
- 500: API or database error

#### `POST /api/v1/ingest/transactions/latest?limit=100`
Ingest latest transactions.

**Query Parameters:**
- `limit` (int): Number of transactions (1-200, default 100)

**Response:**
```json
{
  "success": true,
  "transactions_created": 50,
  "operations_created": 150,
  "limit": 100
}
```

#### `POST /api/v1/ingest/watchlist/refresh`
Refresh all watchlist accounts (synchronous).

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

#### `POST /api/v1/ingest/watchlist/refresh-async`
Refresh watchlist accounts in background.

**Response:**
```json
{
  "success": true,
  "message": "Watchlist refresh queued for background processing"
}
```

## Configuration

### Environment Variables

```bash
# Stellar Network
STELLAR_NETWORK=testnet  # or 'public'
STELLAR_HORIZON_URL=https://horizon-testnet.stellar.org

# Database
DATABASE_URL=postgresql://user:pass@host:5432/stellar_explorer

# Logging
LOG_LEVEL=INFO
```

### Logging Configuration

The module uses structured logging with contextual information:

```python
logger.info(
    "Account ingestion completed",
    extra={
        "address": address,
        "balances_created": balances_created,
        "assets_created": assets_created
    }
)
```

**Log Levels:**
- `DEBUG`: Detailed operation logs
- `INFO`: Normal operations
- `WARNING`: Retry attempts, non-critical issues
- `ERROR`: Failed operations

## Data Flow

### Account Ingestion Flow

```
1. API receives request → /ingest/account/{address}
2. Service calls Horizon client → fetch_account(address)
3. Horizon client fetches data (with retry)
4. Service upserts account record
5. Service processes each balance:
   a. Upsert asset (if not native)
   b. Create balance snapshot
6. Service commits transaction
7. API returns summary
```

### Transaction Ingestion Flow

```
1. API receives request → /ingest/transactions/latest
2. Service calls Horizon client → fetch_transactions(limit)
3. For each transaction:
   a. Check if exists (idempotency)
   b. Upsert source account
   c. Create transaction record
   d. Fetch operations → fetch_transaction_operations(hash)
   e. For each operation:
      - Upsert from/to accounts
      - Upsert assets
      - Create operation record
      - Update counterparty edge
4. Service commits transaction
5. API returns summary
```

## Idempotency

All ingestion operations are idempotent and safe to run multiple times:

### Account Ingestion
- **Existing accounts**: Updates `last_seen` and metadata
- **New accounts**: Creates with `first_seen` timestamp
- **Balances**: Always creates new snapshot (for history)
- **Assets**: Reuses existing, creates if new

### Transaction Ingestion
- **Existing transactions**: Skipped entirely
- **New transactions**: Created with all operations
- **Counterparty edges**: Updates counts and amounts if exists

### Watchlist Refresh
- Updates all accounts atomically
- Continues on individual failures
- Returns summary with success/failure counts

## Error Handling

### Custom Exceptions

```python
class HorizonClientError(Exception):
    """Base exception for Horizon client errors"""
    pass

class AccountNotFoundError(HorizonClientError):
    """Account not found on Stellar network"""
    pass
```

### Retry Logic

Uses `tenacity` library for automatic retries:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((
        StellarConnectionError,
        BadResponseError,
        httpx.TimeoutException
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def fetch_account(self, address: str):
    # Implementation
```

### Database Rollback

All operations use transactions with automatic rollback on error:

```python
try:
    # Ingestion logic
    self.db.commit()
except Exception as e:
    self.db.rollback()
    logger.error(f"Ingestion failed: {e}")
    raise
```

## Testing

### Test Structure

```
tests/
├── conftest.py                    # Fixtures and configuration
├── test_horizon_client.py         # Horizon client tests
├── test_ingestion_service.py      # Service layer tests
└── test_ingestion_endpoints.py    # API endpoint tests
```

### Running Tests

```bash
# Run all tests
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=app --cov-report=html

# Run specific test file
docker-compose exec api pytest tests/test_ingestion_service.py

# Run specific test
docker-compose exec api pytest tests/test_ingestion_service.py::TestIngestionService::test_ingest_account_new

# Run with verbose output
docker-compose exec api pytest -v

# Run only unit tests
docker-compose exec api pytest -m unit
```

### Test Coverage

- **Horizon Client**: 95%+ coverage
  - Success cases
  - Error handling
  - Retry logic
  - Pagination
  
- **Ingestion Service**: 90%+ coverage
  - Account ingestion (new/existing)
  - Transaction ingestion (idempotency)
  - Watchlist refresh
  - Asset/balance upserts
  - Counterparty edges
  - Error rollback

- **API Endpoints**: 85%+ coverage
  - Success responses
  - Error responses (404, 400, 500)
  - Background tasks

### Example Test

```python
def test_ingest_account_new(db_session, sample_account_data):
    """Test ingesting a new account"""
    mock_client = Mock()
    mock_client.fetch_account.return_value = sample_account_data
    
    service = IngestionService(db_session, horizon_client=mock_client)
    account, balances_created, assets_created = service.ingest_account(
        sample_account_data["account_id"]
    )
    
    assert account is not None
    assert balances_created == 2
    assert assets_created == 1
```

## Performance Considerations

### Batch Operations

For large-scale ingestion, use batch operations:

```python
# Ingest multiple accounts
addresses = ["GXXX...", "GYYY...", "GZZZ..."]
for address in addresses:
    try:
        service.ingest_account(address)
    except Exception as e:
        logger.error(f"Failed to ingest {address}: {e}")
```

### Pagination

For transaction ingestion, use pagination:

```python
cursor = None
while True:
    response = client.fetch_transactions(limit=200, cursor=cursor)
    records = response['_embedded']['records']
    
    if not records:
        break
    
    # Process records
    
    cursor = records[-1]['paging_token']
```

### Database Indexes

Ensure proper indexes exist for performance:

```sql
-- Account lookups
CREATE INDEX idx_accounts_address ON accounts(address);

-- Transaction lookups
CREATE INDEX idx_transactions_tx_hash ON transactions(tx_hash);

-- Operation queries
CREATE INDEX idx_operations_type_created ON operations(type, created_at);
```

## Monitoring

### Metrics to Track

1. **Ingestion Rate**: Transactions/operations per minute
2. **Error Rate**: Failed ingestions per hour
3. **Retry Rate**: Retry attempts per request
4. **Latency**: Average ingestion time
5. **Database Growth**: Table sizes over time

### Logging Examples

```python
# Success
logger.info(
    "Account ingestion completed",
    extra={
        "address": address,
        "balances_created": 2,
        "duration_ms": 150
    }
)

# Retry
logger.warning(
    "Retrying request after connection error",
    extra={
        "attempt": 2,
        "max_attempts": 3,
        "wait_seconds": 4
    }
)

# Error
logger.error(
    "Account ingestion failed",
    extra={
        "address": address,
        "error": str(e),
        "error_type": type(e).__name__
    }
)
```

## Best Practices

1. **Always use context managers** for resource cleanup
2. **Handle errors gracefully** with proper logging
3. **Use idempotent operations** for reliability
4. **Store raw payloads** in JSONB for auditability
5. **Monitor retry rates** to detect API issues
6. **Use background tasks** for long-running operations
7. **Test with mocks** to avoid hitting live API
8. **Validate data** before database insertion
9. **Use transactions** for atomic operations
10. **Log with context** for debugging

## Troubleshooting

### Common Issues

**Issue**: Account not found (404)
```
Solution: Verify account exists on network
Check: STELLAR_NETWORK environment variable
```

**Issue**: Connection timeouts
```
Solution: Check Horizon URL and network connectivity
Increase: Retry attempts or timeout duration
```

**Issue**: Duplicate key errors
```
Solution: Check idempotency logic
Verify: Unique constraints in database
```

**Issue**: Slow ingestion
```
Solution: Use batch operations and pagination
Optimize: Database indexes
Consider: Background task processing
```

## Future Enhancements

1. **Streaming Ingestion**: Use Horizon SSE for real-time updates
2. **Bulk Operations**: Batch insert for better performance
3. **Caching Layer**: Redis cache for frequently accessed data
4. **Rate Limiting**: Respect Horizon API rate limits
5. **Metrics Dashboard**: Grafana dashboard for monitoring
6. **Webhook Support**: Trigger ingestion via webhooks
7. **Data Validation**: Schema validation for API responses
8. **Compression**: Compress JSONB payloads
9. **Archival**: Archive old data to separate storage
10. **Multi-Network**: Support multiple Stellar networks

## API Documentation

Full API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support

For issues or questions:
1. Check logs: `docker-compose logs api`
2. Review tests: `pytest -v`
3. Check Horizon status: https://status.stellar.org/
