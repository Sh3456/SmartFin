# Corporate Risk Manager + Company Financial Analysis

A beginner-friendly Flask and SQLite project combining a corporate risk register with a small financial statement analyzer.

## Features
### Corporate risk register
- Dashboard, risk filters, risk reassessment, mitigation controls, audit log
- Risk score = likelihood × impact (1–25)
- Constraints, foreign keys, indexes, transactions and reporting view

### Company financial analysis
- Upload a text-based annual report PDF
- Extract suggested values for current assets, current liabilities, inventory, revenue, net profit, total debt, equity and operating cash flow
- Review/edit extracted values before saving
- Store companies, financial periods and standardized financial items in normalized tables
- Calculate current ratio, quick ratio, working capital, net profit margin and debt-to-equity
- Display basic rule-based liquidity observations

**Important:** PDF extraction is heuristic, not guaranteed. Check each suggested value against the annual report, especially the correct year, standalone/consolidated statement and unit. Scanned PDFs may require OCR, which is not included. This MVP stores the uploaded filename and values, but does not retain the PDF itself after extraction.

## Run on Windows
Python 3.10+ required.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

To load demo data for the risk register, use a second terminal:
```powershell
python -c "import app; app.seed()"
```

Then select **Company Analysis** in the navigation to upload an annual report.

## Financial formulas
- Current ratio = Current assets / Current liabilities
- Quick ratio = (Current assets − Inventory) / Current liabilities
- Working capital = Current assets − Current liabilities
- Net profit margin = Net profit / Revenue × 100
- Debt-to-equity = Total debt / Equity

Ratios should be compared across years and with industry peers; simple rules are not investment advice.

## Database design
The original risk tables remain. Financial analysis adds:
- `companies`: one row per company
- `financial_periods`: one row per company/year/unit
- `financial_values`: one row per item per period

The composite primary key on financial_values prevents duplicate item codes per period. CHECK constraints limit accepted financial items and non-negative values. SQLite transactions save a company's period and all validated values together.
