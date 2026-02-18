-- Useful SQL Queries for Stellar Explorer
-- ==========================================

-- ============================================================================
-- Account Queries
-- ============================================================================

-- Get top 10 highest risk accounts
SELECT 
    id,
    address,
    risk_score,
    label,
    last_seen,
    (SELECT COUNT(*) FROM flags WHERE account_id = a.id AND resolved_at IS NULL) as active_flags
FROM accounts a
WHERE risk_score > 0
ORDER BY risk_score DESC
LIMIT 10;

-- Find accounts with recent activity (last 24 hours)
SELECT 
    address,
    label,
    risk_score,
    last_seen,
    EXTRACT(EPOCH FROM (NOW() - last_seen))/3600 as hours_since_activity
FROM accounts
WHERE last_seen > NOW() - INTERVAL '24 hours'
ORDER BY last_seen DESC;

-- Get account activity summary
SELECT 
    a.address,
    a.label,
    COUNT(DISTINCT t.id) as transaction_count,
    COUNT(DISTINCT o.id) as operation_count,
    COUNT(DISTINCT ab.id) as balance_count,
    MAX(t.created_at) as last_transaction
FROM accounts a
LEFT JOIN transactions t ON t.source_account_id = a.id
LEFT JOIN operations o ON o.from_account_id = a.id OR o.to_account_id = a.id
LEFT JOIN account_balances ab ON ab.account_id = a.id
WHERE a.id = 1  -- Replace with specific account ID
GROUP BY a.id, a.address, a.label;


-- ============================================================================
-- Transaction Queries
-- ============================================================================

-- Get recent transactions with details
SELECT 
    t.tx_hash,
    t.ledger,
    t.created_at,
    a.address as source_address,
    t.fee_charged,
    t.operation_count,
    t.successful,
    t.memo
FROM transactions t
LEFT JOIN accounts a ON t.source_account_id = a.id
ORDER BY t.created_at DESC
LIMIT 100;

-- Transaction success rate by hour
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN successful THEN 1 ELSE 0 END) as successful_transactions,
    ROUND(100.0 * SUM(CASE WHEN successful THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM transactions
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

-- Top accounts by transaction volume
SELECT 
    a.address,
    a.label,
    COUNT(t.id) as transaction_count,
    SUM(t.fee_charged) as total_fees_paid
FROM accounts a
JOIN transactions t ON t.source_account_id = a.id
WHERE t.created_at > NOW() - INTERVAL '30 days'
GROUP BY a.id, a.address, a.label
ORDER BY transaction_count DESC
LIMIT 20;


-- ============================================================================
-- Operation Queries
-- ============================================================================

-- Operation type distribution
SELECT 
    type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM operations
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY type
ORDER BY count DESC;

-- Payment operations with amounts
SELECT 
    o.op_id,
    o.created_at,
    a1.address as from_address,
    a2.address as to_address,
    o.amount,
    ast.asset_code,
    ast.asset_issuer
FROM operations o
LEFT JOIN accounts a1 ON o.from_account_id = a1.id
LEFT JOIN accounts a2 ON o.to_account_id = a2.id
LEFT JOIN assets ast ON o.asset_id = ast.id
WHERE o.type = 'payment'
ORDER BY o.created_at DESC
LIMIT 100;

-- Large transactions (top 1% by amount)
WITH amount_percentile AS (
    SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY amount) as p99
    FROM operations
    WHERE amount IS NOT NULL
)
SELECT 
    o.op_id,
    o.type,
    o.amount,
    a1.address as from_address,
    a2.address as to_address,
    ast.asset_code,
    o.created_at
FROM operations o
LEFT JOIN accounts a1 ON o.from_account_id = a1.id
LEFT JOIN accounts a2 ON o.to_account_id = a2.id
LEFT JOIN assets ast ON o.asset_id = ast.id
CROSS JOIN amount_percentile
WHERE o.amount >= amount_percentile.p99
ORDER BY o.amount DESC;


-- ============================================================================
-- Network Graph Queries
-- ============================================================================

-- Top counterparty relationships by transaction count
SELECT 
    a1.address as from_address,
    a2.address as to_address,
    ast.asset_code,
    ce.tx_count,
    ce.total_amount,
    ce.last_seen
FROM counterparty_edges ce
JOIN accounts a1 ON ce.from_account_id = a1.id
JOIN accounts a2 ON ce.to_account_id = a2.id
LEFT JOIN assets ast ON ce.asset_id = ast.id
ORDER BY ce.tx_count DESC
LIMIT 50;

-- Find accounts with many counterparties (hubs)
SELECT 
    a.address,
    a.label,
    COUNT(DISTINCT ce.to_account_id) as outgoing_connections,
    COUNT(DISTINCT ce2.from_account_id) as incoming_connections,
    COUNT(DISTINCT ce.to_account_id) + COUNT(DISTINCT ce2.from_account_id) as total_connections
FROM accounts a
LEFT JOIN counterparty_edges ce ON ce.from_account_id = a.id
LEFT JOIN counterparty_edges ce2 ON ce2.to_account_id = a.id
GROUP BY a.id, a.address, a.label
HAVING COUNT(DISTINCT ce.to_account_id) + COUNT(DISTINCT ce2.from_account_id) > 10
ORDER BY total_connections DESC;

-- Find circular transaction patterns (A -> B -> A)
SELECT 
    a1.address as account_a,
    a2.address as account_b,
    ce1.tx_count as a_to_b_count,
    ce2.tx_count as b_to_a_count,
    ce1.total_amount as a_to_b_amount,
    ce2.total_amount as b_to_a_amount
FROM counterparty_edges ce1
JOIN counterparty_edges ce2 ON 
    ce1.from_account_id = ce2.to_account_id AND 
    ce1.to_account_id = ce2.from_account_id
JOIN accounts a1 ON ce1.from_account_id = a1.id
JOIN accounts a2 ON ce1.to_account_id = a2.id
WHERE ce1.from_account_id < ce1.to_account_id  -- Avoid duplicates
ORDER BY ce1.tx_count + ce2.tx_count DESC;


-- ============================================================================
-- Risk & Compliance Queries
-- ============================================================================

-- Unresolved flags by severity
SELECT 
    severity,
    flag_type,
    COUNT(*) as count,
    COUNT(DISTINCT account_id) as unique_accounts
FROM flags
WHERE resolved_at IS NULL
GROUP BY severity, flag_type
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    count DESC;

-- Accounts with multiple unresolved flags
SELECT 
    a.address,
    a.label,
    a.risk_score,
    COUNT(f.id) as flag_count,
    STRING_AGG(DISTINCT f.flag_type, ', ') as flag_types,
    MAX(f.created_at) as latest_flag
FROM accounts a
JOIN flags f ON f.account_id = a.id
WHERE f.resolved_at IS NULL
GROUP BY a.id, a.address, a.label, a.risk_score
HAVING COUNT(f.id) > 1
ORDER BY flag_count DESC, a.risk_score DESC;

-- Recent alerts by severity
SELECT 
    alert_type,
    severity,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE acknowledged_at IS NULL) as unacknowledged
FROM alerts
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY alert_type, severity
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1
        WHEN 'error' THEN 2
        WHEN 'warning' THEN 3
        WHEN 'info' THEN 4
    END,
    count DESC;

-- Watchlist summary
SELECT 
    w.name,
    w.description,
    COUNT(wm.id) as member_count,
    COUNT(wm.id) FILTER (WHERE wm.added_at > NOW() - INTERVAL '7 days') as recent_additions
FROM watchlists w
LEFT JOIN watchlist_members wm ON wm.watchlist_id = w.id
GROUP BY w.id, w.name, w.description
ORDER BY member_count DESC;


-- ============================================================================
-- Asset Queries
-- ============================================================================

-- Most traded assets
SELECT 
    ast.asset_code,
    ast.asset_issuer,
    ast.asset_type,
    COUNT(o.id) as operation_count,
    SUM(o.amount) as total_volume
FROM assets ast
JOIN operations o ON o.asset_id = ast.id
WHERE o.created_at > NOW() - INTERVAL '30 days'
GROUP BY ast.id, ast.asset_code, ast.asset_issuer, ast.asset_type
ORDER BY operation_count DESC
LIMIT 20;

-- Assets by holder count
SELECT 
    ast.asset_code,
    ast.asset_issuer,
    COUNT(DISTINCT ab.account_id) as holder_count,
    SUM(ab.balance) as total_supply
FROM assets ast
JOIN account_balances ab ON ab.asset_id = ast.id
GROUP BY ast.id, ast.asset_code, ast.asset_issuer
ORDER BY holder_count DESC;


-- ============================================================================
-- Balance Queries
-- ============================================================================

-- Account portfolio (latest balances)
WITH latest_balances AS (
    SELECT DISTINCT ON (account_id, asset_id)
        account_id,
        asset_id,
        balance,
        snapshot_at
    FROM account_balances
    WHERE account_id = 1  -- Replace with specific account ID
    ORDER BY account_id, asset_id, snapshot_at DESC
)
SELECT 
    a.address,
    COALESCE(ast.asset_code, 'XLM') as asset,
    COALESCE(ast.asset_issuer, 'native') as issuer,
    lb.balance,
    lb.snapshot_at
FROM latest_balances lb
JOIN accounts a ON lb.account_id = a.id
LEFT JOIN assets ast ON lb.asset_id = ast.id
ORDER BY lb.balance DESC;

-- Balance changes over time
SELECT 
    DATE_TRUNC('day', snapshot_at) as day,
    COALESCE(ast.asset_code, 'XLM') as asset,
    AVG(balance) as avg_balance,
    MIN(balance) as min_balance,
    MAX(balance) as max_balance
FROM account_balances ab
LEFT JOIN assets ast ON ab.asset_id = ast.id
WHERE ab.account_id = 1  -- Replace with specific account ID
GROUP BY DATE_TRUNC('day', snapshot_at), ast.asset_code
ORDER BY day DESC;


-- ============================================================================
-- Performance & Maintenance Queries
-- ============================================================================

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Slow queries (requires pg_stat_statements extension)
-- SELECT 
--     query,
--     calls,
--     total_time,
--     mean_time,
--     max_time
-- FROM pg_stat_statements
-- WHERE query LIKE '%accounts%' OR query LIKE '%transactions%'
-- ORDER BY mean_time DESC
-- LIMIT 20;


-- ============================================================================
-- Data Quality Checks
-- ============================================================================

-- Find orphaned records
SELECT 'account_balances without accounts' as issue, COUNT(*) as count
FROM account_balances ab
LEFT JOIN accounts a ON ab.account_id = a.id
WHERE a.id IS NULL
UNION ALL
SELECT 'operations without transactions', COUNT(*)
FROM operations o
LEFT JOIN transactions t ON o.tx_id = t.id
WHERE t.id IS NULL
UNION ALL
SELECT 'transactions without source accounts', COUNT(*)
FROM transactions t
LEFT JOIN accounts a ON t.source_account_id = a.id
WHERE t.source_account_id IS NOT NULL AND a.id IS NULL;

-- Find duplicate edges (should be 0 with unique constraint)
SELECT 
    from_account_id,
    to_account_id,
    asset_id,
    COUNT(*) as duplicate_count
FROM counterparty_edges
GROUP BY from_account_id, to_account_id, asset_id
HAVING COUNT(*) > 1;

-- Check for accounts with no activity
SELECT 
    COUNT(*) as inactive_accounts
FROM accounts a
WHERE NOT EXISTS (
    SELECT 1 FROM transactions t WHERE t.source_account_id = a.id
)
AND NOT EXISTS (
    SELECT 1 FROM operations o WHERE o.from_account_id = a.id OR o.to_account_id = a.id
);
