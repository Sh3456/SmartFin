# Changelog

## Fintech Fraud Analytics migration

- Changed SmartFin's project focus from annual-report ratios to SQL-first fintech transaction risk analytics.
- Reorganized the Oracle deliverables around seven tables: LOCATIONS, DEVICES, CUSTOMERS, MERCHANTS, TRANSACTIONS, CHARGEBACKS, and FRAUD_ALERTS.
- Added instructions for importing the synthetic transaction dataset, Oracle query examples, rule-generated alert examples, and data-quality checks.
- Added an assembly utility for large CSVs stored as numbered parts so they can be reconstructed locally without storing a single very large file in Git.
- Removed the previous financial-statement application and the obsolete financial-statement Oracle scripts from the simplified project tree.
- Recorded source attribution for the dataset in Datasets/README.md and the main README.
