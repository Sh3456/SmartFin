# SmartFin — Fintech Fraud Analytics

An SQL-first DBMS project focused on analyzing synthetic fintech payment transactions, identifying suspicious patterns, measuring chargeback exposure, and reviewing fraud alerts. The core deliverable is Oracle SQL, not a large frontend.

## Project idea

Build a relational fraud analytics warehouse inspired by [Fintech-Risk-Analytics](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics). The project uses seven related tables:

- `LOCATIONS`
- `DEVICES`
- `CUSTOMERS`
- `MERCHANTS`
- `TRANSACTIONS`
- `CHARGEBACKS`
- `FRAUD_ALERTS`

## SQL deliverables

- Oracle DDL with primary keys, foreign keys, check constraints, and indexes
- CSV import instructions and row-count checks
- Queries for approval rates, decline patterns, KYC, VPN/proxy usage, chargeback losses and merchant risk
- CTEs, GROUP BY/HAVING, conditional aggregation, window functions (`ROW_NUMBER`, `DENSE_RANK`, `LAG`, rolling windows)
- Rule-based High Velocity and Device Farming alert generation with Oracle `MERGE`

## Start here

1. Read [Oracle project instructions](oracle/README.md).
2. Run [schema](oracle/01_schema.sql) in Oracle SQL Developer with F5.
3. Follow [CSV import guide](oracle/02_import_data.md).
4. Execute [analysis queries](oracle/03_analysis_queries.sql) section by section.
5. Try [fraud alert rules](oracle/04_generate_fraud_alerts.sql) after importing the source alert data.

The CSV dataset linked by the reference repository is synthetic/demo data. The thresholds in this project are for learning and flag patterns for review; they are not proof of fraud.

## Scope

- SQL and relational database design are the main focus.
- No machine learning, LLM/RAG, forecasting, or complex web app.
- Python/frontend integration is a later step once Oracle SQL is working.

## Existing prototype

The current `app.py` is still an older Flask prototype for financial-statement analysis and SQLite. It has not yet been rewritten or connected to Oracle for fraud analytics. Use the `oracle/` SQL project as the current source of truth for the new idea; do not assume the old website is already using the new schema.
