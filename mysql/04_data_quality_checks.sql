-- Data quality checks for SmartFin — MySQL 8.0+
USE smartfin_fraud_analytics;

-- 1. Row counts: check that every CSV import returned a nonzero count.
SELECT 'locations' AS table_name, COUNT(*) AS row_count FROM locations
UNION ALL SELECT 'devices', COUNT(*) FROM devices
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'merchants', COUNT(*) FROM merchants
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'chargebacks', COUNT(*) FROM chargebacks
UNION ALL SELECT 'fraud_alerts', COUNT(*) FROM fraud_alerts
ORDER BY table_name;

-- 2. Transaction time span and amount distribution.
SELECT MIN(transaction_timestamp) AS first_transaction,
       MAX(transaction_timestamp) AS last_transaction,
       COUNT(*) AS total_transactions,
       ROUND(MIN(amount), 2) AS min_amount,
       ROUND(AVG(amount), 2) AS average_amount,
       ROUND(MAX(amount), 2) AS max_amount
FROM transactions;

-- 3. Status values and counts (helps spot unexpected spelling/case).
SELECT status, COUNT(*) AS row_count
FROM transactions
GROUP BY status
ORDER BY row_count DESC;

-- 4. Chargeback outcomes and amounts.
SELECT status, COUNT(*) AS case_count,
       ROUND(SUM(chargeback_amount), 2) AS total_amount
FROM chargebacks
GROUP BY status
ORDER BY case_count DESC;

-- 5. Alerts by rule and review status.
SELECT rule_triggered, reviewer_status, resolution,
       COUNT(*) AS alert_count,
       ROUND(AVG(risk_score), 2) AS average_risk_score
FROM fraud_alerts
GROUP BY rule_triggered, reviewer_status, resolution
ORDER BY alert_count DESC;

-- 6. Transactions with no imported or generated alert.
SELECT COUNT(*) AS transactions_without_alert
FROM transactions t
WHERE NOT EXISTS (
    SELECT 1 FROM fraud_alerts a
    WHERE a.transaction_id = t.transaction_id
);
