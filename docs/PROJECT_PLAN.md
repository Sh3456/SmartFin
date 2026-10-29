# SmartFin Project Plan — MySQL Fintech Fraud Analytics

## Goal
Build a SQL-first fintech risk analytics warehouse using MySQL 8.0. Import synthetic payment data and use SQL to identify suspicious transaction patterns and measure merchant chargeback exposure.

## Milestones

1. Create the seven-table MySQL schema by running `Fraud_Intelligence_Project.sql` in MySQL Workbench.
2. Rebuild the large CSV files with `python Datasets/assemble_large_csvs.py`.
3. Import CSVs following `mysql/02_import_data.md`, loading parent tables before child tables.
4. Run data-quality checks and compare imported row counts.
5. Run SQL for approval rates, declined transactions, KYC, VPN/proxy trends, chargeback losses, and merchant chargeback ratios.
6. Demonstrate advanced SQL with CTEs, conditional aggregation, `ROW_NUMBER`, `DENSE_RANK`, `LAG`, and rolling windows.
7. Optionally generate High Velocity and Device Farming alerts with `mysql/03_generate_fraud_alerts.sql`.

## Tables
`locations`, `devices`, `customers`, `merchants`, `transactions`, `chargebacks`, and `fraud_alerts`.

## Scope boundaries
No machine learning, RAG/LLM, forecasting, or complicated frontend. Thresholds are illustrative indicators and alerts require human review.
