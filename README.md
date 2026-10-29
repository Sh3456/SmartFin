# SmartFin — Fintech Fraud Analytics

**SmartFin is a MySQL 8.0 SQL-focused fintech fraud analytics project.** It analyzes synthetic payment transactions, flags suspicious patterns for review, and measures chargeback losses and merchant risk. The primary deliverable is the relational database and SQL query library—not a large frontend.

## Data model

Seven related tables:
- `locations`
- `devices`
- `customers`
- `merchants`
- `transactions`
- `chargebacks`
- `fraud_alerts`

`transactions` is the central fact table. The other tables supply customer, merchant, device, location, dispute, and review context.

## Start here in MySQL Workbench

1. Open [`Fraud_Intelligence_Project.sql`](Fraud_Intelligence_Project.sql) and run it using the lightning-bolt button. It creates `smartfin_fraud_analytics` and the seven tables.
2. Read [dataset instructions](Datasets/README.md). Rebuild the two large CSVs from parts by running `python Datasets/assemble_large_csvs.py` in PowerShell from the repo root.
3. Follow [MySQL CSV import instructions](mysql/02_import_data.md) and import tables in foreign-key order.
4. Run [data quality checks](mysql/04_data_quality_checks.sql).
5. Run [analysis queries](mysql/02_analysis_queries.sql) a section at a time.
6. Optionally run [fraud alert rules](mysql/03_generate_fraud_alerts.sql) to add illustrative High Velocity and Device Farming alerts.

The root schema is also available at [`mysql/01_schema.sql`](mysql/01_schema.sql).

## SQL concepts demonstrated

Primary/foreign keys, check constraints, indexes, joins, conditional aggregation, `GROUP BY`/`HAVING`, CTEs, `ROW_NUMBER`, `DENSE_RANK`, `LAG`, rolling-window analytics, and rule-based inserts.

## Dataset attribution and reuse

The synthetic/demo CSV files are attributed to the [Fintech-Risk-Analytics repository](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/tree/main/Datasets). Source links and reuse notes are in [`Datasets/README.md`](Datasets/README.md). An explicit license file was not found in the upstream repository when reviewed, so confirm reuse/redistribution permission with the source owner before redistributing the data publicly.

## Scope and limitations

This is an academic SQL analytics project. Rule thresholds are illustrative signals, not proof of fraud; findings need human review. No machine learning, LLM, forecasting, live payment blocking, or complex frontend is included.

The previous financial-statement prototype was removed from the simplified project tree. **Use MySQL Workbench for this version; the schema is no longer Oracle-specific.**
