# SmartFin — Fintech Fraud Analytics

**SmartFin is an Oracle SQL-focused fintech fraud analytics project.** It analyzes synthetic payment transactions, flags suspicious patterns for human review, and measures chargeback losses and merchant risk. SQL and relational database design are the main deliverables; the large frontend has been removed.

## Data model

Seven related tables:
- `LOCATIONS`
- `DEVICES`
- `CUSTOMERS`
- `MERCHANTS`
- `TRANSACTIONS`
- `CHARGEBACKS`
- `FRAUD_ALERTS`

`TRANSACTIONS` is the central fact table. The other tables provide customer, merchant, device, location, dispute and review context.

## Get started

1. Read the [Oracle setup guide](oracle/README.md).
2. From the repository root, run [`Fraud_Intelligence_Project.sql`](Fraud_Intelligence_Project.sql) in Oracle SQL Developer with **F5 / Run Script**. It creates the schema only.
3. Open [`Datasets/README.md`](Datasets/README.md) and run `python Datasets/assemble_large_csvs.py` to reconstruct the two large CSV files locally.
4. Follow [the data import guide](oracle/02_import_data.md) to load all seven CSVs in foreign-key order.
5. Run [data quality checks](oracle/05_data_quality_checks.sql) to verify row counts and inspect the imported data.
6. Run [analysis queries](oracle/03_analysis_queries.sql) a section at a time.
7. Optionally run [rule-generated alerts](oracle/04_generate_fraud_alerts.sql) to add demo High Velocity and Device Farming alerts.

## SQL concepts demonstrated

Primary/foreign keys, check constraints, indexes, joins, conditional aggregation, `GROUP BY`/`HAVING`, CTEs, `ROW_NUMBER`, `DENSE_RANK`, `LAG`, rolling-window analytics, and `MERGE`.

## Dataset attribution and reuse

The synthetic/demo CSV files are attributed to the [Fintech-Risk-Analytics repository](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/tree/main/Datasets). See [`Datasets/README.md`](Datasets/README.md) for details and source links. An explicit license file was not found in the upstream repository when reviewed, so confirm reuse/redistribution rights with the source owner before redistributing this repository publicly.

## Scope and limitations

This is an academic SQL analytics project. Thresholds are illustrative signals, not proof of fraud; findings need review. The project does not include machine learning, LLMs, forecasting, or live payment blocking. The previous financial-statement app has been removed from this simplified SQL-focused repo; Oracle SQL is the project core.
