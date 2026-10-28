-- SmartFin — Fintech Fraud Analytics master setup script
-- Run this file from the SmartFin repository root in Oracle SQL Developer (F5).
-- This creates the schema only. Import the CSV data before running analytics.

SET DEFINE OFF
PROMPT ============================================================
PROMPT SmartFin - Fintech Fraud Analytics
PROMPT Step 1 of 3: creating Oracle tables and indexes
PROMPT ============================================================

@@oracle/01_schema.sql

PROMPT
PROMPT Schema setup finished.
PROMPT Step 2: import the seven CSV files using oracle/02_import_data.md.
PROMPT Import order: LOCATIONS, DEVICES, CUSTOMERS, MERCHANTS,
PROMPT                TRANSACTIONS, CHARGEBACKS, FRAUD_ALERTS.
PROMPT Step 3: after import, run oracle/05_data_quality_checks.sql.
PROMPT Then run oracle/03_analysis_queries.sql section by section.
PROMPT Optional: run oracle/04_generate_fraud_alerts.sql for demo rules.
PROMPT ============================================================
