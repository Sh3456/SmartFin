-- SmartFin Fraud Analytics — MySQL 8.0+ rule-generated alerts.
-- Run after importing the original FRAUD_ALERTS CSV.
-- These are teaching examples, not production fraud rules.
-- Run again safely: NOT EXISTS avoids duplicate transaction/rule pairs.

USE smartfin_fraud_analytics;
START TRANSACTION;

-- Rule 1: high velocity — five or more approved transactions in 10 minutes.
INSERT INTO fraud_alerts
    (alert_id, transaction_id, alert_timestamp, rule_triggered, risk_score, reviewer_status, resolution)
SELECT CONCAT('ALT-GEN-', REPLACE(UUID(), '-', '')),
       v.transaction_id,
       CURRENT_TIMESTAMP,
       'High Velocity',
       LEAST(100, 60 + (v.tx_count_10_min - 5) * 5),
       'Unassigned',
       'Unresolved'
FROM (
    SELECT t.transaction_id, t.customer_id, t.transaction_timestamp,
           COUNT(*) OVER (
             PARTITION BY t.customer_id
             ORDER BY UNIX_TIMESTAMP(t.transaction_timestamp)
             RANGE BETWEEN 600 PRECEDING AND CURRENT ROW
           ) AS tx_count_10_min
    FROM transactions t
    WHERE LOWER(t.status) = 'approved'
      AND t.customer_id IS NOT NULL
) v
WHERE v.tx_count_10_min >= 5
  AND NOT EXISTS (
      SELECT 1
      FROM fraud_alerts a
      WHERE a.transaction_id = v.transaction_id
        AND a.rule_triggered = 'High Velocity'
  );

-- Rule 2: device farming — one device is associated with at least five customers.
INSERT INTO fraud_alerts
    (alert_id, transaction_id, alert_timestamp, rule_triggered, risk_score, reviewer_status, resolution)
SELECT CONCAT('ALT-GEN-', REPLACE(UUID(), '-', '')),
       t.transaction_id,
       CURRENT_TIMESTAMP,
       'Device Farming',
       75,
       'Unassigned',
       'Unresolved'
FROM transactions t
JOIN (
    SELECT device_id
    FROM transactions
    WHERE device_id IS NOT NULL
      AND customer_id IS NOT NULL
    GROUP BY device_id
    HAVING COUNT(DISTINCT customer_id) >= 5
) shared_devices ON shared_devices.device_id = t.device_id
WHERE NOT EXISTS (
    SELECT 1
    FROM fraud_alerts a
    WHERE a.transaction_id = t.transaction_id
      AND a.rule_triggered = 'Device Farming'
);

COMMIT;
