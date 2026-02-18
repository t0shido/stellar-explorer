# Rule Engine - Implementation Summary

## ✅ All Requirements Implemented

### 5 MVP Rules Created

| Rule | Description | Severity | Output |
|------|-------------|----------|--------|
| **1. Large Transfer** | Detects transfers > threshold from watched accounts | Medium | Alert |
| **2. New Counterparty** | Detects first transaction with new counterparty > threshold | Medium | Alert |
| **3. Dormant Reactivation** | Detects dormant accounts (>X days) with large transactions | High | Flag |
| **4. Rapid Outflow** | Detects >= N outgoing transfers in M minutes | High | Alert |
| **5. Asset Concentration** | Detects top 10 holders controlling > X% of asset | Low | Alert |

### ✅ Configuration

All rules fully configurable via environment variables:
- Enable/disable per rule
- Adjustable thresholds
- Configurable severity levels
- Global dry-run mode
- Configurable execution interval

### ✅ Deduplication

- Hash-based deduplication keys
- Configurable time window (default: 24 hours)
- Prevents alert spam
- Rule-specific dedup logic

### ✅ Evidence Payloads

All alerts/flags include detailed JSON evidence:
- Account addresses
- Transaction hashes
- Amounts and thresholds
- Timestamps
- Asset information
- Rule-specific context

### ✅ Severity Levels

Four severity levels with risk score impact:
- **low**: +10 risk score
- **medium**: +25 risk score
- **high**: +50 risk score
- **critical**: +75 risk score

### ✅ Dry-Run Mode

- Test rules without creating alerts/flags
- Full logging of what would happen
- Safe for production testing
- Configurable via `RULE_ENGINE_DRY_RUN=true`

## 📁 Files Created (15 files)

**Configuration:**
- `apps/worker/app/core/config.py` - Updated with 30+ rule settings

**Rule Engine Core:**
- `apps/worker/app/rules/__init__.py`
- `apps/worker/app/rules/base.py` - Base rule class & result model
- `apps/worker/app/rules/engine.py` - Orchestrator with deduplication

**Individual Rules:**
- `apps/worker/app/rules/large_transfer_rule.py`
- `apps/worker/app/rules/new_counterparty_rule.py`
- `apps/worker/app/rules/dormant_reactivation_rule.py`
- `apps/worker/app/rules/rapid_outflow_rule.py`
- `apps/worker/app/rules/asset_concentration_rule.py`

**Database & Tasks:**
- `apps/worker/app/db/__init__.py`
- `apps/worker/app/db/database.py` - Database connection
- `apps/worker/app/db/models.py` - SQLAlchemy models
- `apps/worker/app/tasks/stellar_tasks.py` - Updated with rule engine task
- `apps/worker/app/celery_app.py` - Updated with periodic schedule

**Documentation:**
- `docs/RULE_ENGINE.md` - Complete documentation (700+ lines)
- `.env.example` - Updated with all rule configurations

## 🚀 Quick Start

### 1. Configure Rules

```bash
# Copy and edit .env
cp .env.example .env

# Enable dry-run mode for testing
RULE_ENGINE_ENABLED=true
RULE_ENGINE_DRY_RUN=true
RULE_ENGINE_INTERVAL_MINUTES=5
```

### 2. Start Services

```bash
make up
```

### 3. Create Watchlist

```bash
# Create watchlist
curl -X POST http://localhost:8000/api/v1/watchlists \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Watchlist", "description": "For testing"}'

# Add account
curl -X POST http://localhost:8000/api/v1/watchlists/1/accounts \
  -H "Content-Type: application/json" \
  -d '{"address": "GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H", "reason": "Test"}'
```

### 4. Monitor Logs

```bash
# Watch rule engine execution
docker-compose logs -f worker | grep "rule engine"

# See dry-run output
docker-compose logs -f worker | grep "DRY RUN"
```

### 5. Enable Production Mode

```bash
# Edit .env
RULE_ENGINE_DRY_RUN=false

# Restart worker
docker-compose restart worker
```

### 6. Check Results

```bash
# View alerts
curl "http://localhost:8000/api/v1/alerts?acknowledged=false"

# View flags
curl "http://localhost:8000/api/v1/accounts/GBRPYHIL2CI3FNQ4BXLFMNDLFJUNPU2HY3ZMFSHONUCEOASW7QC7OX2H"
```

## 📊 Configuration Examples

### Conservative Settings (Low False Positives)

```bash
RULE_LARGE_TRANSFER_THRESHOLD=50000.0
RULE_NEW_COUNTERPARTY_THRESHOLD=25000.0
RULE_DORMANT_DAYS_THRESHOLD=90
RULE_DORMANT_AMOUNT_THRESHOLD=10000.0
RULE_RAPID_OUTFLOW_TX_COUNT=20
RULE_RAPID_OUTFLOW_MINUTES=30
RULE_ASSET_CONCENTRATION_PERCENT=90.0
```

### Aggressive Settings (High Sensitivity)

```bash
RULE_LARGE_TRANSFER_THRESHOLD=1000.0
RULE_NEW_COUNTERPARTY_THRESHOLD=500.0
RULE_DORMANT_DAYS_THRESHOLD=7
RULE_DORMANT_AMOUNT_THRESHOLD=100.0
RULE_RAPID_OUTFLOW_TX_COUNT=5
RULE_RAPID_OUTFLOW_MINUTES=120
RULE_ASSET_CONCENTRATION_PERCENT=50.0
```

### Compliance-Focused

```bash
RULE_LARGE_TRANSFER_ENABLED=true
RULE_LARGE_TRANSFER_THRESHOLD=10000.0
RULE_LARGE_TRANSFER_SEVERITY=high

RULE_DORMANT_REACTIVATION_ENABLED=true
RULE_DORMANT_DAYS_THRESHOLD=30
RULE_DORMANT_REACTIVATION_SEVERITY=critical

RULE_RAPID_OUTFLOW_ENABLED=true
RULE_RAPID_OUTFLOW_TX_COUNT=10
RULE_RAPID_OUTFLOW_SEVERITY=critical
```

## 🎯 Rule Details

### Rule 1: Large Transfer

**Triggers**: Outgoing transfer from watched account > threshold

**Evidence**:
- Account address
- Amount and threshold
- Transaction hash
- Asset details
- Timestamp

**Use Case**: AML compliance, fraud detection

---

### Rule 2: New Counterparty

**Triggers**: First transaction with new account > threshold

**Evidence**:
- Watched account
- Counterparty account
- Direction (incoming/outgoing)
- Amount
- First seen timestamp

**Use Case**: Relationship monitoring, suspicious connections

---

### Rule 3: Dormant Reactivation

**Triggers**: Account inactive > X days, then large transaction

**Evidence**:
- Dormancy period (actual vs threshold)
- Last activity date
- Reactivation transaction
- Amount

**Use Case**: Account takeover detection, fraud

---

### Rule 4: Rapid Outflow

**Triggers**: >= N outgoing transfers in M minutes

**Evidence**:
- Operation count
- Time window
- Total amount
- Unique counterparties
- Asset breakdown
- Operations per minute

**Use Case**: Money laundering detection, account compromise

---

### Rule 5: Asset Concentration

**Triggers**: Top 10 holders control > X% of asset

**Evidence**:
- Concentration percentage
- Total supply
- Top 10 holder details
- Individual percentages

**Use Case**: Market manipulation risk, centralization warnings

## 🔍 Deduplication Logic

### How It Works

1. **Generate Key**: Hash of (rule + account + specific fields)
2. **Check Window**: Look for existing alerts/flags in last N hours
3. **Skip if Found**: Prevent duplicate creation

### Example

```
First Run (10:00 AM):
- Rule: large_transfer
- Account: GXXXXXXX...
- TX: abc123...
- Result: Alert created ✓

Second Run (10:05 AM):
- Rule: large_transfer
- Account: GXXXXXXX...
- TX: abc123... (same transaction)
- Result: Skipped (duplicate within 24h window) ✗

Third Run (Next Day 11:00 AM):
- Rule: large_transfer
- Account: GXXXXXXX...
- TX: def456... (different transaction)
- Result: Alert created ✓
```

## 📈 Monitoring

### Key Metrics

```python
{
  "enabled": true,
  "dry_run": false,
  "rules_evaluated": 5,
  "total_results": 23,
  "fired_results": 8,
  "alerts_created": 6,
  "flags_created": 2,
  "duplicates_skipped": 15
}
```

### Health Checks

```bash
# Check if rule engine is running
docker-compose logs worker | grep "rule engine" | tail -20

# Check last execution time
docker-compose logs worker | grep "Rule engine evaluation completed" | tail -1

# Count alerts created today
curl "http://localhost:8000/api/v1/alerts" | jq '.data | length'
```

## 🛠️ Troubleshooting

### Rules Not Firing

**Check**:
1. `RULE_ENGINE_ENABLED=true`
2. Specific rule enabled
3. Watchlist has accounts (Rules 1-4)
4. Thresholds not too high
5. Worker is running

### Too Many Alerts

**Solutions**:
1. Increase thresholds
2. Enable dry-run temporarily
3. Increase deduplication window
4. Review rule logic

### Performance Issues

**Optimizations**:
1. Increase interval minutes
2. Disable unused rules
3. Limit watchlist size
4. Add database indexes

## 📚 Documentation

- **Complete Guide**: [docs/RULE_ENGINE.md](docs/RULE_ENGINE.md)
- **API Endpoints**: [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md)
- **Database Schema**: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)

## ✨ Features Summary

✅ **5 Production-Ready Rules**  
✅ **Fully Configurable** via environment variables  
✅ **Deduplication** prevents alert spam  
✅ **Evidence Payloads** for auditability  
✅ **Dry-Run Mode** for safe testing  
✅ **Severity Levels** (low/medium/high/critical)  
✅ **Automatic Execution** via Celery Beat  
✅ **Risk Score Updates** for flags  
✅ **Comprehensive Logging** with structured data  
✅ **Database Integration** with alerts & flags tables  

Perfect for compliance, fraud detection, and risk management! 🎉
