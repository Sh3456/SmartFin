# SmartFin — Fintech Fraud Analytics (Oracle SQL)

This project uses Oracle SQL to analyze synthetic payment transactions, chargebacks, merchant risk, and rule-generated fraud alerts.

## Recommended run order

1. From the repository root, run `Fraud_Intelligence_Project.sql` in Oracle SQL Developer with **F5**. It creates the tables and indexes.
2. Rebuild the two large local CSVs with `python Datasets/assemble_large_csvs.py`.
3. Follow `02_import_data.md` to import all seven CSV files in parent-to-child order.
4. Run `05_data_quality_checks.sql` to confirm data was loaded and inspect ranges/status values.
5. Run `03_analysis_queries.sql` section by section.
6. Optionally run `04_generate_fraud_alerts.sql` to create illustrative High Velocity and Device Farming alerts.

## Seven-table schema

- `LOCATIONS`: location metadata and a synthetic risk score.
- `DEVICES`: device/browser/IP attributes and VPN/proxy flag.
- `CUSTOMERS`: customer profile and KYC flag.
- `MERCHANTS`: merchant/category metadata and risk tier.
- `TRANSACTIONS`: central fact table for payments.
- `CHARGEBACKS`: disputes, reason codes, amounts and outcomes.
- `FRAUD_ALERTS`: generated/imported signals and reviewer resolutions.

## SQL concepts

PK/FK constraints, check constraints, indexes, joins, conditional aggregation, `GROUP BY`/`HAVING`, CTEs, `ROW_NUMBER`, `DENSE_RANK`, `LAG`, rolling analytics, and `MERGE`.

## Interpretation

Risk scores and thresholds are illustrative academic rules. They should be reviewed and tuned; no single signal proves fraud or should be used to block a real payment. Dataset attribution is recorded in `Datasets/README.md`. The upstream repository did not expose a LICENSE file at the time of review, so confirm redistribution permission before publishing another public copy.
