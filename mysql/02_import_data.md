# Import SmartFin's CSV data into MySQL Workbench

Use MySQL 8.0+ and MySQL Workbench. Data is from the synthetic/demo dataset in [Akshay-gurav-31/Fintech-Risk-Analytics](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/tree/main/Datasets). Attribution and reuse note: no explicit upstream license was found during review, so confirm permission before redistributing the data publicly.

## 1. Rebuild the two large CSV files

From the SmartFin project root in PowerShell:

```powershell
python Datasets/assemble_large_csvs.py
```

This creates `Datasets/devices.csv` and `Datasets/transactions.csv`. The generated files are ignored by Git to avoid storing duplicate large files.

## 2. Create the database

Open `Fraud_Intelligence_Project.sql` or `mysql/01_schema.sql` in MySQL Workbench and click the lightning bolt to run it. It creates and selects the `smartfin_fraud_analytics` database and creates seven tables. This schema file is for **MySQL**, not Oracle.

## 3. Import each CSV into its existing table

In the left **SCHEMAS** panel, refresh, expand `smartfin_fraud_analytics` → `Tables`. Right-click each table and choose **Table Data Import Wizard**. Select the matching CSV and map the source columns to the table columns by name.

Import in this order because child records reference parent IDs:

1. `Datasets/locations.csv` → `locations`
2. `Datasets/devices.csv` → `devices`
3. `Datasets/customers.csv` → `customers`
4. `Datasets/merchants.csv` → `merchants`
5. `Datasets/transactions.csv` → `transactions`
6. `Datasets/chargebacks.csv` → `chargebacks`
7. `Datasets/fraud_alerts.csv` → `fraud_alerts`

Map columns by their CSV headers. The CSV Boolean-like values such as `True` and `False` are stored as text in `is_vpn_proxy`, `kyc_verified`, `cvv_match`, and `avs_match`.

## 4. Verify data

Run `mysql/04_data_quality_checks.sql`. Make sure row counts are nonzero and check the date range, statuses, and chargeback outcomes.

## 5. Run the analytics

Run `mysql/02_analysis_queries.sql` in sections. It demonstrates joins, aggregations, CTEs, ranking/window functions, chargeback loss tracking, velocity patterns, and device sharing.

Optionally run `mysql/03_generate_fraud_alerts.sql` to add High Velocity and Device Farming examples. Review the results—these rules are illustrative and are not proof of fraud.
