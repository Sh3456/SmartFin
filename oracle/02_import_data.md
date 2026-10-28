# Load the synthetic fraud dataset into Oracle

Use the synthetic/demo data repository that inspired the project: [Fintech-Risk-Analytics](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics).

CSV files:
- [customers.csv](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/blob/main/Datasets/customers.csv)
- [devices.csv](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/blob/main/Datasets/devices.csv)
- [locations.csv](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/blob/main/Datasets/locations.csv)
- [merchants.csv](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/blob/main/Datasets/merchants.csv)
- [transactions.csv](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/blob/main/Datasets/transactions.csv)
- [chargebacks.csv](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/blob/main/Datasets/chargebacks.csv)
- [fraud_alerts.csv](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/blob/main/Datasets/fraud_alerts.csv)
- [locations.csv](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/blob/main/Datasets/locations.csv)

The data contains synthetic names and values for practice, not actual customer records. Download the CSVs to your computer; this repo does not duplicate the large dataset.

## Import sequence

1. Run `01_schema.sql` in Oracle SQL Developer using **F5 / Run Script**.
2. In SQL Developer, right-click each target table and choose **Import Data** (or use the import wizard). Select the matching CSV and map columns by name.
3. Load data in this order to satisfy foreign keys:
   1. `LOCATIONS` ← `locations.csv`
   2. `DEVICES` ← `devices.csv`
   3. `CUSTOMERS` ← `customers.csv`
   4. `MERCHANTS` ← `merchants.csv`
   5. `TRANSACTIONS` ← `transactions.csv`
   6. `CHARGEBACKS` ← `chargebacks.csv`
   7. `FRAUD_ALERTS` ← `fraud_alerts.csv`
4. For timestamp columns, set the format to `YYYY-MM-DD HH24:MI:SS`. For `ONBOARDING_DATE`, use `YYYY-MM-DD`.
5. Keep `IS_VPN_PROXY`, `KYC_VERIFIED`, `CVV_MATCH`, and `AVS_MATCH` as text values such as `True` and `False`.
6. After importing each CSV, check that the row count is greater than zero before importing child tables.

## Validate row counts

```sql
SELECT 'LOCATIONS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM LOCATIONS
UNION ALL SELECT 'DEVICES', COUNT(*) FROM DEVICES
UNION ALL SELECT 'CUSTOMERS', COUNT(*) FROM CUSTOMERS
UNION ALL SELECT 'MERCHANTS', COUNT(*) FROM MERCHANTS
UNION ALL SELECT 'TRANSACTIONS', COUNT(*) FROM TRANSACTIONS
UNION ALL SELECT 'CHARGEBACKS', COUNT(*) FROM CHARGEBACKS
UNION ALL SELECT 'FRAUD_ALERTS', COUNT(*) FROM FRAUD_ALERTS;
```

For the project, keep the thresholds in the SQL examples clearly labelled as illustrative rules, and describe hits as suspicious patterns requiring human review—not proof of fraud.
