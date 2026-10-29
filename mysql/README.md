# SmartFin — MySQL Fraud Analytics

**Use MySQL Workbench for this version.** The project is SQL-first and analyzes the synthetic transaction dataset through seven relational tables.

## Setup order

1. Run `01_schema.sql` or the root `Fraud_Intelligence_Project.sql` in MySQL Workbench.
2. Rebuild large CSVs with `python Datasets/assemble_large_csvs.py`.
3. Follow `02_import_data.md` to import the seven CSVs into the existing tables in the specified order.
4. Run `04_data_quality_checks.sql`.
5. Execute `02_analysis_queries.sql` section by section.
6. Optionally run `03_generate_fraud_alerts.sql` for example rule-generated alerts.

## Tables

`locations`, `devices`, `customers`, `merchants`, `transactions`, `chargebacks`, and `fraud_alerts`.

## SQL skills

Primary and foreign keys, checks, indexes, joins, `GROUP BY`/`HAVING`, conditional aggregation, CTEs, window functions (`ROW_NUMBER`, `DENSE_RANK`, `LAG`), and rule-based inserts.

## Scope limits

The dataset is synthetic/demo data. Fraud rules are illustrative indicators for human review, not proof of fraud. The app/frontend and machine learning are intentionally not part of this SQL-focused milestone. Source attribution is documented in `Datasets/README.md`; verify permission before redistributing the data publicly.
