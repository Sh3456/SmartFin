# SmartFin — Fintech Fraud Analytics

**SmartFin is now an Oracle SQL-focused fintech fraud analytics project.** It analyzes synthetic payment transactions, flags suspicious patterns for review, and measures chargeback loss and merchant risk. The primary deliverable is the database and SQL query library, not a large frontend.

## Data model

Seven related tables:
- `LOCATIONS`
- `DEVICES`
- `CUSTOMERS`
- `MERCHANTS`
- `TRANSACTIONS`
- `CHARGEBACKS`
- `FRAUD_ALERTS`

The transaction table is the central fact table; the other tables supply customer, merchant, device, location, dispute, and review context.

## Get started

1. Open [Oracle SQL setup guide](oracle/README.md).
2. Run [`oracle/01_schema.sql`](oracle/01_schema.sql) in Oracle SQL Developer with **F5 / Run Script**.
3. Open [`Datasets/README.md`](Datasets/README.md). Some large CSVs are stored as parts; assemble them with `python Datasets/assemble_large_csvs.py`.
4. Follow [`oracle/02_import_data.md`](oracle/02_import_data.md) to import the seven datasets in foreign-key order.
5. Run [`oracle/03_analysis_queries.sql`](oracle/03_analysis_queries.sql) a section at a time.
6. Optionally run [`oracle/04_generate_fraud_alerts.sql`](oracle/04_generate_fraud_alerts.sql) to generate demo High Velocity and Device Farming alerts.

## SQL skills demonstrated

Primary/foreign keys, check constraints, indexes, joins, conditional aggregation, `GROUP BY`/`HAVING`, CTEs, `ROW_NUMBER`, `DENSE_RANK`, `LAG`, rolling-window analytics, and `MERGE`.

## Dataset attribution

The dataset files are from the [Fintech-Risk-Analytics repository](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/tree/main/Datasets) and are described by the upstream project as simulated/synthetic practice data. Attribution and source links are recorded in [`Datasets/README.md`](Datasets/README.md). An explicit license file was not found in the upstream repository when reviewed; confirm reuse/redistribution rights with the source owner before redistributing this repository publicly.

## Scope and limitations

This is a student/learning analytics project. Thresholds are illustrative signals, not proof of fraud; results need review. There is no machine learning, LLM, forecasting, or live transaction blocking.

The old Flask financial-statement application has been removed from this simplified SQL-focused project. Oracle SQL is the project core.
