# Import SmartFin datasets into Oracle

The seven CSV datasets are stored in the repository's `Datasets/` folder and attributed to the [Fintech-Risk-Analytics source repository](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/tree/main/Datasets).

## 1. Rebuild the two large CSVs

From the SmartFin root folder, run:

```powershell
python Datasets/assemble_large_csvs.py
```

This creates `Datasets/devices.csv` and `Datasets/transactions.csv` from the numbered parts. The other five CSV files are already present directly in `Datasets/`.

## 2. Create tables

Open `oracle/01_schema.sql` in Oracle SQL Developer and run it with **F5 / Run Script**. Run it only once for a new schema.

## 3. Import CSVs in this order

Use SQL Developer's table import wizard. Select the CSV and map columns by name to the existing table:

1. `Datasets/locations.csv` → `LOCATIONS`
2. `Datasets/devices.csv` → `DEVICES`
3. `Datasets/customers.csv` → `CUSTOMERS`
4. `Datasets/merchants.csv` → `MERCHANTS`
5. `Datasets/transactions.csv` → `TRANSACTIONS`
6. `Datasets/chargebacks.csv` → `CHARGEBACKS`
7. `Datasets/fraud_alerts.csv` → `FRAUD_ALERTS`

The order matters because foreign keys in child tables refer to rows in parent tables.

## 4. Date and Boolean-like columns

- For timestamp columns, use `YYYY-MM-DD HH24:MI:SS`.
- For `MERCHANTS.ONBOARDING_DATE`, use `YYYY-MM-DD`.
- Keep `IS_VPN_PROXY`, `KYC_VERIFIED`, `CVV_MATCH`, and `AVS_MATCH` as text values such as `True` and `False` during import.

## 5. Verify row counts

```sql
SELECT 'LOCATIONS' TABLE_NAME, COUNT(*) ROW_COUNT FROM LOCATIONS
UNION ALL SELECT 'DEVICES', COUNT(*) FROM DEVICES
UNION ALL SELECT 'CUSTOMERS', COUNT(*) FROM CUSTOMERS
UNION ALL SELECT 'MERCHANTS', COUNT(*) FROM MERCHANTS
UNION ALL SELECT 'TRANSACTIONS', COUNT(*) FROM TRANSACTIONS
UNION ALL SELECT 'CHARGEBACKS', COUNT(*) FROM CHARGEBACKS
UNION ALL SELECT 'FRAUD_ALERTS', COUNT(*) FROM FRAUD_ALERTS;
```

If a foreign-key error occurs, verify that the parent tables were imported first and that IDs match exactly.

The dataset is synthetic/demo data. Fraud-rule hits indicate patterns that deserve investigation; they do not prove fraud.
