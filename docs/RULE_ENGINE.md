# Rule Engine Documentation

## Overview

The Rule Engine is an automated monitoring system that evaluates predefined rules against the Stellar Explorer database and creates alerts/flags when suspicious or noteworthy patterns are detected.

## Architecture

```
┌──────────────┐
│ Celery Beat  │ (Scheduler)
└──────┬───────┘
       │ Every N minutes
       ▼
┌──────────────┐
│ Rule Engine  │
│   Task       │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────┐
│  Rule Evaluation                 │
│  ┌────────────────────────────┐  │
│  │ 1. Large Transfer Rule     │  │
│  │ 2. New Counterparty Rule   │  │
│  │ 3. Dormant Reactivation    │  │
│  │ 4. Rapid Outflow Rule      │  │
│  │ 5. Asset Concentration     │  │
│  └────────────────────────────┘  │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────┐
│ Deduplication│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Create       │
│ Alerts/Flags │
└──────────────┘
```

## Rules

### Rule 1: Large Transfer Detection

**Purpose**: Detect large transfers from watched accounts

**Logic**:
- Monitors all accounts in watchlists
- Triggers when outgoing transfer exceeds threshold
- Checks recent operations (last hour)

**Configuration**:
```bash
RULE_LARGE_TRANSFER_ENABLED=true
RULE_LARGE_TRANSFER_THRESHOLD=10000.0
RULE_LARGE_TRANSFER_SEVERITY=medium
```

**Evidence Payload**:
```json
{
  "account_address": "GXXXXXXX...",
  "amount": "15000.0000000",
  "threshold": "10000.0",
  "asset_code": "USD",
  "asset_issuer": "GISSUER...",
  "transaction_hash": "abc123...",
  "ledger": 12345,
  "operation_id": "op123",
  "operation_type": "payment",
  "to_account": 2,
  "timestamp": "2024-02-16T20:00:00Z"
}
```

**Output**: Creates an **Alert**

---

### Rule 2: New Counterparty Detection

**Purpose**: Detect new counterparty relationships with large initial transactions

**Logic**:
- Monitors all watched accounts
- Triggers when first transaction with new counterparty exceeds threshold
- Checks both incoming and outgoing relationships

**Configuration**:
```bash
RULE_NEW_COUNTERPARTY_ENABLED=true
RULE_NEW_COUNTERPARTY_THRESHOLD=5000.0
RULE_NEW_COUNTERPARTY_SEVERITY=medium
```

**Evidence Payload**:
```json
{
  "watched_account": "GXXXXXXX...",
  "counterparty_account": "GYYYYYY...",
  "direction": "outgoing",
  "amount": "7500.0000000",
  "threshold": "5000.0",
  "asset_code": "XLM",
  "asset_issuer": null,
  "first_seen": "2024-02-16T20:00:00Z",
  "tx_count": 1
}
```

**Output**: Creates an **Alert**

---

### Rule 3: Dormant Account Reactivation

**Purpose**: Detect dormant accounts that suddenly become active with large transactions

**Logic**:
- Monitors watched accounts
- Checks if account has been inactive for > X days
- Triggers when large transaction occurs after dormancy

**Configuration**:
```bash
RULE_DORMANT_REACTIVATION_ENABLED=true
RULE_DORMANT_DAYS_THRESHOLD=30
RULE_DORMANT_AMOUNT_THRESHOLD=1000.0
RULE_DORMANT_REACTIVATION_SEVERITY=high
```

**Evidence Payload**:
```json
{
  "account_address": "GXXXXXXX...",
  "dormant_days_threshold": 30,
  "dormant_days_actual": 45,
  "last_activity": "2024-01-01T00:00:00Z",
  "reactivation_time": "2024-02-16T20:00:00Z",
  "amount": "5000.0000000",
  "amount_threshold": "1000.0",
  "asset_code": "XLM",
  "transaction_hash": "abc123...",
  "ledger": 12345,
  "operation_type": "payment"
}
```

**Output**: Creates a **Flag** (updates risk score)

---

### Rule 4: Rapid Outflow Burst

**Purpose**: Detect rapid succession of outgoing transfers

**Logic**:
- Monitors watched accounts
- Counts outgoing operations in time window
- Triggers when count >= threshold

**Configuration**:
```bash
RULE_RAPID_OUTFLOW_ENABLED=true
RULE_RAPID_OUTFLOW_TX_COUNT=10
RULE_RAPID_OUTFLOW_MINUTES=60
RULE_RAPID_OUTFLOW_SEVERITY=high
```

**Evidence Payload**:
```json
{
  "account_address": "GXXXXXXX...",
  "operation_count": 15,
  "threshold": 10,
  "time_window_minutes": 60,
  "total_amount": "50000.0000000",
  "unique_counterparties": 8,
  "asset_breakdown": {
    "XLM": {"count": 10, "total_amount": 30000.0},
    "USD": {"count": 5, "total_amount": 20000.0}
  },
  "window_start": "2024-02-16T19:00:00Z",
  "window_end": "2024-02-16T20:00:00Z",
  "operations_per_minute": 0.25
}
```

**Output**: Creates an **Alert**

---

### Rule 5: Asset Concentration Warning

**Purpose**: Detect high concentration of asset ownership

**Logic**:
- Analyzes all assets in database
- Calculates top 10 holders' percentage
- Triggers when concentration exceeds threshold

**Configuration**:
```bash
RULE_ASSET_CONCENTRATION_ENABLED=true
RULE_ASSET_CONCENTRATION_PERCENT=80.0
RULE_ASSET_CONCENTRATION_SEVERITY=low
```

**Evidence Payload**:
```json
{
  "asset_code": "USD",
  "asset_issuer": "GISSUER...",
  "concentration_percent": 85.5,
  "threshold_percent": 80.0,
  "total_supply": "1000000.0000000",
  "top_10_total": "855000.0000000",
  "holder_count": 10,
  "top_holders": [
    {
      "account_address": "GXXXXXXX...",
      "account_label": "Exchange",
      "balance": "500000.0000000",
      "percentage": 50.0
    }
  ]
}
```

**Output**: Creates an **Alert**

---

## Configuration

### Global Settings

```bash
# Enable/disable entire rule engine
RULE_ENGINE_ENABLED=true

# Dry-run mode (logs but doesn't create alerts/flags)
RULE_ENGINE_DRY_RUN=false

# How often to run (in minutes)
RULE_ENGINE_INTERVAL_MINUTES=5

# Deduplication window (in hours)
ALERT_DEDUP_WINDOW_HOURS=24
```

### Per-Rule Configuration

Each rule can be individually:
- **Enabled/Disabled**: `RULE_*_ENABLED`
- **Configured**: Thresholds, time windows, etc.
- **Severity Set**: `low`, `medium`, `high`, `critical`

## Deduplication

### How It Works

1. **Dedup Key Generation**: Creates a unique hash from:
   - Rule name
   - Account ID
   - Asset ID (if applicable)
   - Rule-specific fields (e.g., transaction hash, counterparty)

2. **Window Check**: Looks for existing alerts/flags within deduplication window (default: 24 hours)

3. **Skip if Duplicate**: If matching alert/flag exists, skips creation

### Example

```python
# First evaluation
Rule: large_transfer
Account: GXXXXXXX...
TX Hash: abc123...
Result: Alert created ✓

# Second evaluation (within 24 hours)
Rule: large_transfer
Account: GXXXXXXX...
TX Hash: abc123...
Result: Skipped (duplicate) ✗
```

## Dry-Run Mode

### Purpose

Test rules without creating actual alerts/flags in the database.

### Activation

```bash
RULE_ENGINE_DRY_RUN=true
```

### Behavior

- All rules evaluate normally
- Results are logged with `[DRY RUN]` prefix
- **No** alerts/flags created
- **No** risk scores updated
- Full evidence payloads logged

### Example Log Output

```
[INFO] [DRY RUN] Would create alert/flag
  rule: large_transfer
  severity: medium
  account_id: 1
  evidence: {"account_address": "GXXXXXXX...", "amount": "15000.0"}
```

## Severity Levels

### Impact on Risk Scores

When flags are created, account risk scores are updated:

| Severity | Risk Score Increase |
|----------|---------------------|
| low      | +10                 |
| medium   | +25                 |
| high     | +50                 |
| critical | +75                 |

**Note**: Risk scores are capped at 100.0

### Recommended Usage

- **low**: Informational, no immediate action
- **medium**: Worth investigating
- **high**: Requires attention
- **critical**: Immediate action required

## Running the Rule Engine

### Automatic (Celery Beat)

The rule engine runs automatically via Celery Beat:

```bash
# Starts automatically with worker
docker-compose up worker
```

**Schedule**: Every `RULE_ENGINE_INTERVAL_MINUTES` minutes

### Manual Execution

```python
from app.db.database import SessionLocal
from app.rules.engine import RuleEngine

db = SessionLocal()
try:
    engine = RuleEngine(db, dry_run=True)  # Optional dry-run
    summary = engine.run()
    print(summary)
finally:
    db.close()
```

### Via Celery Task

```bash
# Trigger manually
docker-compose exec worker celery -A app.celery_app call app.tasks.stellar_tasks.run_rule_engine
```

## Monitoring

### Check Rule Engine Status

```bash
# View worker logs
docker-compose logs -f worker | grep "rule engine"

# Check recent alerts
curl "http://localhost:8000/api/v1/alerts?acknowledged=false"

# Check recent flags
# (Via database query)
docker-compose exec postgres psql -U stellar_user -d stellar_explorer \
  -c "SELECT * FROM flags WHERE resolved_at IS NULL ORDER BY created_at DESC LIMIT 10;"
```

### Metrics to Track

1. **Rules Evaluated**: Number of rules run per cycle
2. **Results Fired**: How many rules triggered
3. **Alerts Created**: New alerts per cycle
4. **Flags Created**: New flags per cycle
5. **Duplicates Skipped**: Deduplication effectiveness
6. **Execution Time**: Performance monitoring

## Best Practices

### 1. Start with Dry-Run

```bash
RULE_ENGINE_DRY_RUN=true
```

Run for 24-48 hours to:
- Verify rules work correctly
- Check for false positives
- Tune thresholds

### 2. Tune Thresholds Gradually

Start conservative, then adjust:

```bash
# Start high
RULE_LARGE_TRANSFER_THRESHOLD=50000.0

# Monitor for a week
# Adjust based on results

# Lower if needed
RULE_LARGE_TRANSFER_THRESHOLD=10000.0
```

### 3. Use Appropriate Severities

- Don't overuse `critical` - reserve for truly urgent cases
- Most rules should be `medium` or `high`
- Use `low` for informational patterns

### 4. Monitor Deduplication

If too many duplicates:
- Increase `ALERT_DEDUP_WINDOW_HOURS`
- Check if rules are too broad

If too few duplicates:
- Decrease window
- Rules might be too specific

### 5. Regular Review

- Weekly: Review unacknowledged alerts
- Monthly: Analyze rule effectiveness
- Quarterly: Adjust thresholds based on data

## Troubleshooting

### Rules Not Firing

**Check**:
1. Is rule engine enabled? `RULE_ENGINE_ENABLED=true`
2. Is specific rule enabled? `RULE_*_ENABLED=true`
3. Are thresholds too high?
4. Are there watched accounts? (Rules 1-4 require watchlists)
5. Check worker logs for errors

### Too Many Alerts

**Solutions**:
1. Increase thresholds
2. Enable dry-run mode temporarily
3. Increase deduplication window
4. Adjust severity levels

### Performance Issues

**Optimizations**:
1. Increase `RULE_ENGINE_INTERVAL_MINUTES`
2. Disable unused rules
3. Add database indexes
4. Limit watchlist size

### Duplicate Alerts

**Check**:
1. Deduplication window setting
2. Rule-specific fields in dedup key
3. Database query performance

## API Integration

### View Alerts

```bash
GET /api/v1/alerts?severity=high&acknowledged=false
```

### Acknowledge Alert

```bash
POST /api/v1/alerts/{id}/ack
```

### Create Manual Flag

```bash
POST /api/v1/flags/manual
{
  "address": "GXXXXXXX...",
  "flag_type": "manual_review",
  "severity": "high",
  "reason": "Suspicious pattern detected",
  "evidence": {"notes": "Requires investigation"}
}
```

## Future Enhancements

1. **Machine Learning Rules**: Anomaly detection
2. **Custom Rules**: User-defined rules via API
3. **Rule Chaining**: Composite rules
4. **Webhooks**: External notifications
5. **Rule Templates**: Pre-configured rule sets
6. **Historical Analysis**: Backtest rules on historical data

## Example Workflow

### 1. Initial Setup

```bash
# Enable rule engine
RULE_ENGINE_ENABLED=true
RULE_ENGINE_DRY_RUN=true  # Start in dry-run

# Configure rules
RULE_LARGE_TRANSFER_THRESHOLD=10000.0
RULE_RAPID_OUTFLOW_TX_COUNT=10
```

### 2. Create Watchlist

```bash
curl -X POST http://localhost:8000/api/v1/watchlists \
  -H "Content-Type: application/json" \
  -d '{"name": "High Value Accounts", "description": "Accounts to monitor"}'

curl -X POST http://localhost:8000/api/v1/watchlists/1/accounts \
  -H "Content-Type: application/json" \
  -d '{"address": "GXXXXXXX...", "reason": "High volume trader"}'
```

### 3. Monitor Dry-Run

```bash
# Watch logs
docker-compose logs -f worker | grep "DRY RUN"

# Review what would be created
# Adjust thresholds if needed
```

### 4. Enable Production Mode

```bash
# Disable dry-run
RULE_ENGINE_DRY_RUN=false

# Restart worker
docker-compose restart worker
```

### 5. Monitor & Respond

```bash
# Check alerts daily
curl "http://localhost:8000/api/v1/alerts?acknowledged=false"

# Investigate and acknowledge
curl -X POST http://localhost:8000/api/v1/alerts/1/ack
```

## Summary

The Rule Engine provides automated, configurable monitoring of Stellar accounts with:

✅ **5 Built-in Rules** covering common risk patterns  
✅ **Configurable Thresholds** via environment variables  
✅ **Deduplication** to prevent alert spam  
✅ **Dry-Run Mode** for safe testing  
✅ **Evidence Payloads** for auditability  
✅ **Severity Levels** for prioritization  
✅ **Automatic Execution** via Celery Beat  

Perfect for compliance monitoring, risk management, and fraud detection!
