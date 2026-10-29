-- SmartFin Fintech Fraud Analytics — MySQL 8.0+ queries.
-- Run after importing the seven CSVs into smartfin_fraud_analytics.

USE smartfin_fraud_analytics;

-- 1. Transaction KPIs for a chosen date range.
SET @start_date = '2025-01-01';
SET @end_date   = '2025-12-31';

SELECT COUNT(*) AS total_transactions,
       SUM(CASE WHEN LOWER(status) = 'approved' THEN 1 ELSE 0 END) AS approved_transactions,
       SUM(CASE WHEN LOWER(status) = 'declined' THEN 1 ELSE 0 END) AS declined_transactions,
       ROUND(SUM(CASE WHEN LOWER(status) = 'approved' THEN amount ELSE 0 END), 2) AS approved_value,
       ROUND(100.0 * SUM(CASE WHEN LOWER(status) = 'approved' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 2) AS approval_rate_pct
FROM transactions
WHERE transaction_timestamp >= CAST(@start_date AS DATETIME)
  AND transaction_timestamp < DATE_ADD(CAST(@end_date AS DATETIME), INTERVAL 1 DAY);

-- 2. Payment status distribution.
SELECT status, COUNT(*) AS transaction_count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage_of_all
FROM transactions
GROUP BY status
ORDER BY transaction_count DESC;

-- 3. Merchants with most declined payments (possible card-testing signal).
SELECT m.merchant_id, m.merchant_name, COUNT(*) AS declined_count
FROM transactions t
JOIN merchants m ON m.merchant_id = t.merchant_id
WHERE LOWER(t.status) = 'declined'
GROUP BY m.merchant_id, m.merchant_name
ORDER BY declined_count DESC
LIMIT 10;

-- 4. Compare approval rate by VPN/proxy usage.
SELECT CASE
         WHEN LOWER(d.is_vpn_proxy) IN ('true','1','yes') THEN 'VPN/Proxy'
         WHEN LOWER(d.is_vpn_proxy) IN ('false','0','no') THEN 'No VPN/Proxy'
         ELSE 'Unknown'
       END AS connection_type,
       COUNT(*) AS total_transactions,
       SUM(CASE WHEN LOWER(t.status) = 'approved' THEN 1 ELSE 0 END) AS approved_transactions,
       ROUND(100.0 * SUM(CASE WHEN LOWER(t.status) = 'approved' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 2) AS approval_rate_pct
FROM transactions t
JOIN devices d ON d.device_id = t.device_id
GROUP BY connection_type
ORDER BY total_transactions DESC;

-- 5. Unverified customers with high approved lifetime spend.
SELECT c.customer_id, c.first_name, c.last_name,
       ROUND(SUM(t.amount), 2) AS approved_lifetime_spend,
       COUNT(*) AS approved_transaction_count
FROM customers c
JOIN transactions t ON t.customer_id = c.customer_id
WHERE LOWER(c.kyc_verified) IN ('false','0','no')
  AND LOWER(t.status) = 'approved'
GROUP BY c.customer_id, c.first_name, c.last_name
HAVING SUM(t.amount) > 10000
ORDER BY approved_lifetime_spend DESC;

-- 6. Monthly chargeback losses (cases marked Lost).
SELECT DATE_FORMAT(chargeback_date, '%Y-%m') AS loss_month,
       COUNT(*) AS lost_chargebacks,
       ROUND(SUM(chargeback_amount), 2) AS total_loss
FROM chargebacks
WHERE LOWER(status) = 'lost'
GROUP BY DATE_FORMAT(chargeback_date, '%Y-%m')
ORDER BY loss_month;

-- 7. Chargebacks by reason code.
SELECT reason_code, COUNT(*) AS incident_count,
       ROUND(SUM(chargeback_amount), 2) AS disputed_value
FROM chargebacks
GROUP BY reason_code
ORDER BY disputed_value DESC;

-- 8. Merchant chargeback ratio. Separate aggregates prevent join fan-out
-- from inflating the denominator when multiple dispute rows exist.
WITH tx_counts AS (
    SELECT merchant_id, COUNT(*) AS transaction_count
    FROM transactions
    GROUP BY merchant_id
),
cb_counts AS (
    SELECT t.merchant_id,
           COUNT(DISTINCT c.transaction_id) AS chargeback_transactions,
           SUM(CASE WHEN LOWER(c.status) = 'lost' THEN c.chargeback_amount ELSE 0 END) AS lost_amount
    FROM transactions t
    JOIN chargebacks c ON c.transaction_id = t.transaction_id
    GROUP BY t.merchant_id
)
SELECT m.merchant_id, m.merchant_name, tx.transaction_count,
       COALESCE(cb.chargeback_transactions, 0) AS chargeback_transactions,
       ROUND(100.0 * COALESCE(cb.chargeback_transactions, 0)
             / NULLIF(tx.transaction_count, 0), 3) AS chargeback_rate_pct,
       ROUND(COALESCE(cb.lost_amount, 0), 2) AS lost_amount,
       CASE
         WHEN 100.0 * COALESCE(cb.chargeback_transactions, 0) / NULLIF(tx.transaction_count, 0) >= 2 THEN 'HIGH - REVIEW'
         WHEN 100.0 * COALESCE(cb.chargeback_transactions, 0) / NULLIF(tx.transaction_count, 0) >= 1 THEN 'MEDIUM - MONITOR'
         ELSE 'LOWER - MONITOR'
       END AS suggested_risk_tier
FROM merchants m
JOIN tx_counts tx ON tx.merchant_id = m.merchant_id
LEFT JOIN cb_counts cb ON cb.merchant_id = m.merchant_id
WHERE tx.transaction_count >= 100
ORDER BY chargeback_rate_pct DESC;

-- 9. Precision of reviewed fraud-alert rules.
SELECT rule_triggered, COUNT(*) AS reviewed_alerts,
       SUM(CASE WHEN LOWER(resolution) = 'true positive (fraud)' THEN 1 ELSE 0 END) AS confirmed_fraud,
       ROUND(100.0 * SUM(CASE WHEN LOWER(resolution) = 'true positive (fraud)' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0), 2) AS precision_pct
FROM fraud_alerts
WHERE LOWER(reviewer_status) = 'closed'
GROUP BY rule_triggered
ORDER BY reviewed_alerts DESC;

-- 10. AVS mismatch on declined payments.
SELECT c.customer_id, c.email, COUNT(*) AS declined_avs_mismatches
FROM transactions t
JOIN customers c ON c.customer_id = t.customer_id
WHERE LOWER(t.avs_match) IN ('false','0','no')
  AND LOWER(t.status) = 'declined'
GROUP BY c.customer_id, c.email
ORDER BY declined_avs_mismatches DESC
LIMIT 20;

-- 11. Latest transaction for each customer: ROW_NUMBER.
WITH ranked_transactions AS (
    SELECT t.*,
           ROW_NUMBER() OVER (
             PARTITION BY customer_id
             ORDER BY transaction_timestamp DESC, transaction_id
           ) AS row_num
    FROM transactions t
    WHERE customer_id IS NOT NULL
)
SELECT customer_id, transaction_id, amount, status, transaction_timestamp
FROM ranked_transactions
WHERE row_num = 1;

-- 12. Top three approved transaction amounts per merchant: DENSE_RANK.
WITH ranked_transactions AS (
    SELECT t.merchant_id, t.transaction_id, t.customer_id, t.amount,
           DENSE_RANK() OVER (PARTITION BY t.merchant_id ORDER BY t.amount DESC) AS amount_rank
    FROM transactions t
    WHERE LOWER(t.status) = 'approved'
)
SELECT m.merchant_name, r.transaction_id, r.customer_id, r.amount, r.amount_rank
FROM ranked_transactions r
JOIN merchants m ON m.merchant_id = r.merchant_id
WHERE r.amount_rank <= 3
ORDER BY m.merchant_name, r.amount_rank;

-- 13. Cumulative monthly chargeback loss: SUM OVER.
WITH monthly_losses AS (
    SELECT DATE_FORMAT(chargeback_date, '%Y-%m-01') AS loss_month,
           SUM(chargeback_amount) AS monthly_loss
    FROM chargebacks
    WHERE LOWER(status) = 'lost'
    GROUP BY DATE_FORMAT(chargeback_date, '%Y-%m-01')
)
SELECT loss_month, monthly_loss,
       SUM(monthly_loss) OVER (ORDER BY loss_month) AS cumulative_loss
FROM monthly_losses
ORDER BY loss_month;

-- 14. High-velocity candidates: >= 5 approved transactions in ten minutes.
-- UNIX_TIMESTAMP makes the RANGE frame numeric for MySQL 8 window functions.
WITH velocity AS (
    SELECT t.customer_id, t.transaction_id, t.amount, t.transaction_timestamp,
           COUNT(*) OVER (
             PARTITION BY t.customer_id
             ORDER BY UNIX_TIMESTAMP(t.transaction_timestamp)
             RANGE BETWEEN 600 PRECEDING AND CURRENT ROW
           ) AS transactions_last_10_min,
           SUM(t.amount) OVER (
             PARTITION BY t.customer_id
             ORDER BY UNIX_TIMESTAMP(t.transaction_timestamp)
             RANGE BETWEEN 600 PRECEDING AND CURRENT ROW
           ) AS amount_last_10_min
    FROM transactions t
    WHERE LOWER(t.status) = 'approved'
      AND t.customer_id IS NOT NULL
)
SELECT customer_id, transaction_id, amount, transaction_timestamp,
       transactions_last_10_min, amount_last_10_min
FROM velocity
WHERE transactions_last_10_min >= 5
ORDER BY customer_id, transaction_timestamp;

-- 15. Device sharing: devices linked to five or more customers.
SELECT d.device_id, d.device_type, d.ip_address,
       COUNT(DISTINCT t.customer_id) AS distinct_customers,
       COUNT(*) AS transaction_count
FROM devices d
JOIN transactions t ON t.device_id = d.device_id
GROUP BY d.device_id, d.device_type, d.ip_address
HAVING COUNT(DISTINCT t.customer_id) >= 5
ORDER BY distinct_customers DESC, transaction_count DESC;

-- 16. Possible rapid country changes within one hour (heuristic only).
WITH customer_travel AS (
    SELECT t.customer_id, t.transaction_id, t.transaction_timestamp, l.country,
           LAG(l.country) OVER (
             PARTITION BY t.customer_id ORDER BY t.transaction_timestamp
           ) AS previous_country,
           LAG(t.transaction_timestamp) OVER (
             PARTITION BY t.customer_id ORDER BY t.transaction_timestamp
           ) AS previous_timestamp
    FROM transactions t
    JOIN devices d ON d.device_id = t.device_id
    JOIN locations l ON l.location_id = d.location_id
    WHERE t.customer_id IS NOT NULL
)
SELECT customer_id, transaction_id, previous_country, country,
       previous_timestamp, transaction_timestamp
FROM customer_travel
WHERE previous_country IS NOT NULL
  AND country <> previous_country
  AND TIMESTAMPDIFF(MINUTE, previous_timestamp, transaction_timestamp) BETWEEN 0 AND 60
ORDER BY customer_id, transaction_timestamp;
