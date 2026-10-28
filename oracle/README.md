# SmartFin — Fintech Fraud Analytics (Oracle SQL)

This project analyzes synthetic payment transactions using Oracle SQL. The goal is to demonstrate relational design, joins, aggregation, CTEs, window functions and simple rule-generated alerts.

## Run order

1. Run `01_schema.sql` in Oracle SQL Developer with **F5**.
2. Rebuild large local CSV files by running `python Datasets/assemble_large_csvs.py` from the repo root.
3. Follow [`02_import_data.md`](02_import_data.md) to import all seven CSVs in parent-to-child order.
4. Run `03_analysis_queries.sql` section by section.
5. Optionally run `04_generate_fraud_alerts.sql` to add High Velocity and Device Farming alerts.

## Seven-table schema

- `LOCATIONS`: location metadata and a synthetic risk score.
- `DEVICES`: device/browser/IP attributes and VPN/proxy flag.
- `CUSTOMERS`: customer profile and KYC flag.
- `MERCHANTS`: merchant/category metadata and risk tier.
- `TRANSACTIONS`: central fact table for payments.
- `CHARGEBACKS`: disputes, reason codes and outcomes.
- `FRAUD_ALERTS`: generated or imported signals and reviewer resolutions.

## SQL concepts

PK/FK constraints, check constraints, indexes, joins, conditional aggregation, `GROUP BY`/`HAVING`, CTEs, `ROW_NUMBER`, `DENSE_RANK`, `LAG`, rolling analytics, and `MERGE`.

## Interpretation

Risk scores and thresholds are illustrative academic rules. They should be reviewed and tuned; no single signal should be treated as proof of fraud or used to block a real payment. The source CSVs are attributed in `Datasets/README.md`. The upstream repository did not expose a LICENSE file at the time of review, so confirm redistribution permission before publishing another public copy.
