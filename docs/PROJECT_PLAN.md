# SmartFin Project Plan — Fintech Fraud Analytics

## Goal
Build an SQL-first fintech risk analytics warehouse in Oracle. Import synthetic payment data and use SQL to identify suspicious transaction behavior and measure merchant chargeback exposure.

## Milestones

1. Create the seven-table schema using `oracle/01_schema.sql`.
2. Import CSV data following `oracle/02_import_data.md`, loading parent tables before dependent tables.
3. Run core SQL: approval rates, declined transactions, KYC status, VPN/proxy trends, chargeback losses, and merchant chargeback rates.
4. Demonstrate advanced SQL with CTEs, conditional aggregation, `ROW_NUMBER`, `DENSE_RANK`, `LAG`, and rolling windows.
5. Optionally generate High Velocity and Device Farming alerts with `oracle/04_generate_fraud_alerts.sql`.
6. Validate results, check row counts, and document false positives and limits.
7. Only after SQL works, replace the old financial-statement UI with a small fraud dashboard backed by Oracle.

## Tables
`LOCATIONS`, `DEVICES`, `CUSTOMERS`, `MERCHANTS`, `TRANSACTIONS`, `CHARGEBACKS`, `FRAUD_ALERTS`.

## Scope boundaries
No machine learning, RAG/LLM, forecasting, or complicated frontend. Thresholds are illustrative and alerts require human review.
