# API Endpoints Documentation

## Overview

Complete API reference for the Stellar Explorer application. All endpoints return JSON responses with consistent structure and proper error handling.

**Base URL**: `http://localhost:8000/api/v1`

**API Documentation**: `http://localhost:8000/docs` (Swagger UI)

## Table of Contents

- [Health](#health)
- [Watchlists](#watchlists)
- [Accounts](#accounts)
- [Assets](#assets)
- [Alerts & Flags](#alerts--flags)
- [Ingestion](#ingestion)

---

## Health

### GET /health

Health check endpoint for monitoring service status.

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2024-02-16T20:00:00Z",
  "database": "healthy",
  "horizon": "healthy",
  "version": "1.0.0"
}
```

**Example**:
```bash
curl http://localhost:8000/api/v1/health
```

---

## Watchlists

### POST /watchlists

Create a new watchlist for monitoring accounts.

**Request Body**:
```json
{
  "name": "High Risk Accounts",
  "description": "Accounts flagged for suspicious activity"
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "name": "High Risk Accounts",
  "description": "Accounts flagged for suspicious activity",
  "member_count": 0,
  "members": []
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/watchlists \
  -H "Content-Type: application/json" \
  -d '{"name": "High Risk Accounts", "description": "Suspicious accounts"}'
```

---

### POST /watchlists/{id}/accounts

Add an account to a watchlist. **On-demand ingestion**: If the account doesn't exist locally, it will be fetched from Horizon API automatically.

**Path Parameters**:
- `id` (integer): Watchlist ID

**Request Body**:
```json
{
  "address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
  "reason": "Unusual transaction pattern"
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Account GBRPYHIL... added to watchlist 'High Risk Accounts'",
  "data": {
    "account_id": 1,
    "watchlist_id": 1
  }
}
```

**Errors**:
- `404`: Watchlist or account not found
- `409`: Account already in watchlist

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/watchlists/1/accounts \
  -H "Content-Type: application/json" \
  -d '{"address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H", "reason": "High volume"}'
```

---

### GET /watchlists

List all watchlists with member counts.

**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "name": "High Risk Accounts",
    "description": "Suspicious accounts",
    "member_count": 5
  },
  {
    "id": 2,
    "name": "Exchanges",
    "description": "Known exchange accounts",
    "member_count": 10
  }
]
```

**Example**:
```bash
curl http://localhost:8000/api/v1/watchlists
```

---

### GET /watchlists/{id}

Get detailed watchlist information including all members.

**Path Parameters**:
- `id` (integer): Watchlist ID

**Response**: `200 OK`
```json
{
  "id": 1,
  "name": "High Risk Accounts",
  "description": "Suspicious accounts",
  "member_count": 2,
  "members": [
    {
      "id": 1,
      "account_id": 1,
      "account_address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
      "reason": "High volume",
      "added_at": "2024-02-16T20:00:00Z"
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/api/v1/watchlists/1
```

---

## Accounts

### GET /accounts/{address}

Get detailed account information including balances. **On-demand ingestion**: If the account doesn't exist locally, it will be fetched from Horizon API automatically.

**Path Parameters**:
- `address` (string): Stellar account address

**Response**: `200 OK`
```json
{
  "id": 1,
  "address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
  "label": "Exchange Wallet",
  "risk_score": 25.5,
  "first_seen": "2024-01-01T00:00:00Z",
  "last_seen": "2024-02-16T20:00:00Z",
  "metadata": {
    "sequence": "123456789",
    "subentry_count": 2
  },
  "balances": [
    {
      "asset_code": null,
      "asset_issuer": null,
      "asset_type": "native",
      "balance": "10000.0000000",
      "limit": null,
      "buying_liabilities": "0.0000000",
      "selling_liabilities": "0.0000000"
    },
    {
      "asset_code": "USD",
      "asset_issuer": "GDUKMGUGDZQK6YHYA5Z6AY2G4XDSZPSZ3SW5UN3ARVMO6QSRDWP5YLEX",
      "asset_type": "credit_alphanum4",
      "balance": "5000.0000000",
      "limit": "10000.0000000",
      "buying_liabilities": "0.0000000",
      "selling_liabilities": "0.0000000"
    }
  ]
}
```

**Errors**:
- `404`: Account not found on Stellar network
- `500`: API or database error

**Example**:
```bash
curl http://localhost:8000/api/v1/accounts/GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H
```

---

### GET /accounts/{address}/activity

Get paginated transaction history for an account. **On-demand ingestion** supported.

**Path Parameters**:
- `address` (string): Stellar account address

**Query Parameters**:
- `limit` (integer, optional): Number of transactions (1-200, default: 50)
- `page` (integer, optional): Page number (default: 1)

**Response**: `200 OK`
```json
{
  "data": [
    {
      "tx_hash": "abc123def456...",
      "ledger": 12345,
      "created_at": "2024-02-16T20:00:00Z",
      "operation_count": 1,
      "successful": true,
      "fee_charged": 100,
      "memo": "Payment"
    }
  ],
  "pagination": {
    "total": 150,
    "page": 1,
    "page_size": 50,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

**Example**:
```bash
curl "http://localhost:8000/api/v1/accounts/GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H/activity?limit=20&page=1"
```

---

### GET /accounts/{address}/counterparties

Get accounts that have transacted with this account. **On-demand ingestion** supported.

**Path Parameters**:
- `address` (string): Stellar account address

**Query Parameters**:
- `limit` (integer, optional): Number of counterparties (1-200, default: 50)

**Response**: `200 OK`
```json
[
  {
    "account_id": 2,
    "account_address": "GDUKMGUGDZQK6YHYA5Z6AY2G4XDSZPSZ3SW5UN3ARVMO6QSRDWP5YLEX",
    "account_label": "Known Exchange",
    "asset_code": null,
    "asset_issuer": null,
    "tx_count": 50,
    "total_amount": "10000.0000000",
    "last_seen": "2024-02-16T20:00:00Z",
    "direction": "sent"
  },
  {
    "account_id": 3,
    "account_address": "GCEXAMPLE...",
    "account_label": null,
    "asset_code": "USD",
    "asset_issuer": "GISSUER...",
    "tx_count": 25,
    "total_amount": "5000.0000000",
    "last_seen": "2024-02-15T18:00:00Z",
    "direction": "received"
  }
]
```

**Example**:
```bash
curl "http://localhost:8000/api/v1/accounts/GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H/counterparties?limit=20"
```

---

## Assets

### GET /assets/top-holders

Get top holders of a specific asset sorted by balance.

**Query Parameters**:
- `asset_code` (string, required): Asset code (e.g., "USD", "XLM")
- `asset_issuer` (string, optional): Asset issuer address (not required for XLM)
- `limit` (integer, optional): Number of holders (1-200, default: 50)

**Response**: `200 OK`
```json
{
  "asset_code": "USD",
  "asset_issuer": "GDUKMGUGDZQK6YHYA5Z6AY2G4XDSZPSZ3SW5UN3ARVMO6QSRDWP5YLEX",
  "asset_type": "credit_alphanum4",
  "total_holders": 1000,
  "total_supply": "1000000.0000000",
  "holders": [
    {
      "account_id": 1,
      "account_address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
      "account_label": "Exchange",
      "balance": "50000.0000000",
      "percentage": 5.0
    },
    {
      "account_id": 2,
      "account_address": "GCEXAMPLE...",
      "account_label": null,
      "balance": "25000.0000000",
      "percentage": 2.5
    }
  ]
}
```

**Errors**:
- `404`: Asset not found

**Example**:
```bash
# Custom asset
curl "http://localhost:8000/api/v1/assets/top-holders?asset_code=USD&asset_issuer=GDUKMGUGDZQK6YHYA5Z6AY2G4XDSZPSZ3SW5UN3ARVMO6QSRDWP5YLEX&limit=10"

# Native XLM
curl "http://localhost:8000/api/v1/assets/top-holders?asset_code=XLM&limit=10"
```

---

## Alerts & Flags

### GET /alerts

List alerts with optional filtering and pagination.

**Query Parameters**:
- `severity` (string, optional): Filter by severity (info, warning, error, critical)
- `acknowledged` (boolean, optional): Filter by acknowledgment status
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (1-200, default: 50)

**Response**: `200 OK`
```json
{
  "data": [
    {
      "id": 1,
      "account_id": 1,
      "account_address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
      "asset_id": null,
      "asset_code": null,
      "alert_type": "large_transaction",
      "severity": "warning",
      "payload": {
        "amount": "100000.0000000",
        "threshold": "50000.0000000"
      },
      "created_at": "2024-02-16T20:00:00Z",
      "acknowledged_at": null
    }
  ],
  "pagination": {
    "total": 25,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**Example**:
```bash
# All unacknowledged critical alerts
curl "http://localhost:8000/api/v1/alerts?severity=critical&acknowledged=false"

# Page 2 of warnings
curl "http://localhost:8000/api/v1/alerts?severity=warning&page=2&limit=20"
```

---

### POST /alerts/{id}/ack

Acknowledge an alert.

**Path Parameters**:
- `id` (integer): Alert ID

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Alert 1 acknowledged successfully",
  "data": {
    "alert_id": 1,
    "acknowledged_at": "2024-02-16T20:00:00Z"
  }
}
```

**Errors**:
- `404`: Alert not found
- `409`: Alert already acknowledged

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/alerts/1/ack
```

---

### POST /flags/manual

Create a manual risk flag for an account. **On-demand ingestion**: If the account doesn't exist locally, it will be fetched from Horizon API automatically.

**Request Body**:
```json
{
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
```

**Valid Severity Levels**: `low`, `medium`, `high`, `critical`

**Response**: `201 Created`
```json
{
  "id": 1,
  "account_id": 1,
  "account_address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
  "flag_type": "suspicious_activity",
  "severity": "high",
  "reason": "Unusual transaction pattern detected",
  "evidence": {
    "transaction_count": 1000,
    "time_period": "24h",
    "pattern": "rapid_movement"
  },
  "created_at": "2024-02-16T20:00:00Z",
  "resolved_at": null
}
```

**Side Effects**:
- Updates account `risk_score` based on severity:
  - `low`: +10
  - `medium`: +25
  - `high`: +50
  - `critical`: +75

**Errors**:
- `400`: Invalid severity level
- `404`: Account not found on Stellar network
- `500`: API or database error

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/flags/manual \
  -H "Content-Type: application/json" \
  -d '{
    "address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H",
    "flag_type": "suspicious_activity",
    "severity": "high",
    "reason": "Unusual transaction pattern",
    "evidence": {"tx_count": 1000}
  }'
```

---

## Ingestion

### POST /ingest/account/{address}

Manually trigger account ingestion from Horizon API.

**Path Parameters**:
- `address` (string): Stellar account address

**Response**: `200 OK`
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

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/ingest/account/GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H
```

---

### POST /ingest/transactions/latest

Ingest latest transactions from Horizon API.

**Query Parameters**:
- `limit` (integer, optional): Number of transactions (1-200, default: 100)

**Response**: `200 OK`
```json
{
  "success": true,
  "transactions_created": 50,
  "operations_created": 150,
  "limit": 100
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/transactions/latest?limit=50"
```

---

### POST /ingest/watchlist/refresh

Refresh data for all accounts in watchlists (synchronous).

**Response**: `200 OK`
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

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/ingest/watchlist/refresh
```

---

### POST /ingest/watchlist/refresh-async

Refresh watchlist accounts in background (asynchronous).

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Watchlist refresh queued for background processing"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/ingest/watchlist/refresh-async
```

---

## Error Responses

All endpoints return consistent error responses:

**Format**:
```json
{
  "detail": "Error message"
}
```

**Common Status Codes**:
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource already exists
- `500 Internal Server Error`: Server error

---

## Pagination

Paginated endpoints return data in this format:

```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 50,
    "total_pages": 2,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## On-Demand Ingestion

The following endpoints support **automatic on-demand ingestion** from Horizon API:

- `GET /accounts/{address}`
- `GET /accounts/{address}/activity`
- `GET /accounts/{address}/counterparties`
- `POST /watchlists/{id}/accounts`
- `POST /flags/manual`

If an account doesn't exist locally, it will be automatically fetched from the Stellar network and stored in the database before returning the response.

---

## OpenAPI Tags

Endpoints are organized with the following tags in Swagger UI:

- **health**: Health check
- **watchlists**: Watchlist management
- **accounts**: Account information and activity
- **assets**: Asset information and holders
- **alerts**: Alert management
- **flags**: Risk flag management
- **ingestion**: Manual data ingestion

---

## Rate Limiting

Currently no rate limiting is implemented. For production use, consider adding rate limiting middleware.

---

## Authentication

Currently no authentication is required. For production use, implement JWT or API key authentication.

---

## Testing

Test all endpoints using the interactive Swagger UI:

```
http://localhost:8000/docs
```

Or use curl/Postman with the examples provided above.
