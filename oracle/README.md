# SmartFin — Fintech Fraud Analytics

SmartFin has pivoted from annual-report analysis to a SQL-first fintech fraud analytics warehouse inspired by the objectives and synthetic dataset in [Fintech-Risk-Analytics](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics). This repository contains its own Oracle-compatible schema and queries rather than copying the source project's SQL wholesale.

## Objective

Analyze payment transactions to identify suspicious transaction patterns, measure chargeback loss, understand merchant risk, and prioritize alerts for human review.

## Seven-table model

- `LOCATIONS`: country, region/state, city, ZIP code, and location risk score.
- `DEVICES`: device/browser/IP details and VPN/proxy indicator.
- `CUSTOMERS`: profile, account status, KYC state, and primary location.
- `MERCHANTS`: merchant/category details and current risk tier.
- `TRANSACTIONS`: central payment fact table.
- `CHARGEBACKS`: disputed transactions, reasons, amounts, outcomes.
- `FRAUD_ALERTS`: rule, risk score, review status, and resolution.

## Run order

1. `01_schema.sql`: create the Oracle tables, foreign keys, checks, and indexes.
2. `02_import_data.md`: download and import CSVs in dependency order.
3. `03_analysis_queries.sql`: start with basic queries, then work through CTEs and window functions.
4. `04_generate_fraud_alerts.sql`: optionally add illustrative High Velocity and Device Farming alerts.

## SQL skills

Joins, PK/FK constraints, indexes, `GROUP BY`/ `HAVING`, conditional aggregation, CTEs, `ROW_NUMBER`, `DENSE_RANK`, `LAG`, rolling analytic windows, and `MERGE`.

## Scope

The database and SQL are the main deliverable. No ML, LLM, forecasting, or live transaction blocking. Rules flag patterns for investigation and do not prove fraud. The source data is synthetic/demo data.

## Current app status

The old Flask prototype still contains financial-statement pages and has not yet been rewritten for fraud analytics. The SQL project is the current priority; update the UI and add Oracle connectivity only after the schema, data import, and queries work. No database credentials should be committed to Git.
