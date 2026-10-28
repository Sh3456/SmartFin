# SmartFin datasets

This folder contains the seven synthetic/demo CSV datasets used for SmartFin's fintech fraud analytics project, sourced from the [Fintech-Risk-Analytics Datasets folder](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics/tree/main/Datasets).

## Files

- `locations.csv`
- `devices.csv`
- `customers.csv`
- `merchants.csv`
- `transactions.csv`
- `chargebacks.csv`
- `fraud_alerts.csv`

The upstream `devices.csv` and `transactions.csv` files are large, so their data is stored in numbered text parts under `parts/`. To reconstruct those exact CSV files, run from the SmartFin repository root:

```powershell
python Datasets/assemble_large_csvs.py
```

This creates `Datasets/devices.csv` and `Datasets/transactions.csv` locally. The reconstructed files are ignored by Git so the repository only stores the numbered parts. Use the reconstructed files for Oracle SQL Developer's CSV import wizard.

## Source and reuse note

Source: [Akshay-gurav-31/Fintech-Risk-Analytics](https://github.com/Akshay-gurav-31/Fintech-Risk-Analytics), `Datasets/` folder. The upstream README describes the data as realistic simulated transactions. No LICENSE or COPYING file was found during review. The dataset is included here at the user's request with attribution; confirm permission from the source owner before redistributing it publicly.
