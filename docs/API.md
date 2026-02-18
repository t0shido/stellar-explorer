# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### Health Check

```
GET /health
```

Returns the health status of the API.

**Response:**
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "1.0.0"
}
```

---

### Accounts

#### Get All Accounts

```
GET /api/v1/accounts/
```

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100)

**Response:**
```json
[
  {
    "id": 1,
    "account_id": "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "sequence": "12345",
    "balance": 1000.5,
    "num_subentries": 0,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### Get Account by ID

```
GET /api/v1/accounts/{account_id}
```

**Response:**
```json
{
  "id": 1,
  "account_id": "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "sequence": "12345",
  "balance": 1000.5,
  "num_subentries": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Create Account

```
POST /api/v1/accounts/
```

**Request Body:**
```json
{
  "account_id": "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "sequence": "12345",
  "balance": 1000.5,
  "num_subentries": 0
}
```

---

### Transactions

#### Get All Transactions

```
GET /api/v1/transactions/
```

**Query Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum number of records to return (default: 100)

**Response:**
```json
[
  {
    "id": 1,
    "hash": "abc123...",
    "source_account": "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "fee": 100,
    "operation_count": 1,
    "successful": true,
    "ledger": 12345,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### Get Transaction by Hash

```
GET /api/v1/transactions/{tx_hash}
```

**Response:**
```json
{
  "id": 1,
  "hash": "abc123...",
  "source_account": "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "fee": 100,
  "operation_count": 1,
  "successful": true,
  "ledger": 12345,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### Stellar Network

#### Get Network Info

```
GET /api/v1/stellar/network
```

**Response:**
```json
{
  "network": "testnet",
  "horizon_url": "https://horizon-testnet.stellar.org",
  "status": "connected"
}
```

#### Get Stellar Account

```
GET /api/v1/stellar/account/{account_id}
```

Fetches account data directly from the Stellar network.

**Response:**
```json
{
  "id": "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "account_id": "GXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  "sequence": "12345",
  "balances": [...],
  ...
}
```

#### Get Recent Transactions

```
GET /api/v1/stellar/transactions/recent
```

**Query Parameters:**
- `limit` (int, optional): Number of transactions to return (default: 10)

**Response:**
```json
{
  "_embedded": {
    "records": [...]
  }
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Error message"
}
```

---

## Interactive Documentation

Visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI.

Visit `http://localhost:8000/redoc` for alternative API documentation powered by ReDoc.
