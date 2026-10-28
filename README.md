# SmartFin — SQL-First Financial Statement Analyzer

A beginner-friendly DBMS project focused on Oracle SQL, data integrity, reviewable financial data, and financial ratio calculations. The current Flask website is still a SQLite prototype; the dedicated Oracle schema and SQL/PLSQL scripts are in [`oracle/`](oracle/README.md). The website will be connected to Oracle as a separate integration step.

## SQL project track (priority)
- Five core Oracle tables: `COMPANY`, `FINANCIAL_PERIOD`, `FINANCIAL_ITEM`, `RAW_FINANCIAL_DATA`, and `FINANCIAL_VALUE`.
- Primary keys, foreign keys, unique constraints, check constraints, and indexes.
- A review queue for extracted candidates so unverified PDF numbers are not treated as authoritative values.
- A PL/SQL procedure to validate and save an approved figure.
- SQL queries and a view for current ratio, quick ratio, working capital, and period comparison.

**Start here:** follow [`oracle/README.md`](oracle/README.md), then run the files in `oracle/` with Oracle SQL Developer.

## Features
### Corporate risk register
- Dashboard, risk filters, risk reassessment, mitigation controls, audit log
- Risk score = likelihood × impact (1–25)
- Constraints, foreign keys, indexes, transactions and reporting view

### Company financial analysis
- Upload a text-based annual report PDF and select the statement scope
- Extract table-aware candidate values for current assets, current liabilities, inventory, revenue, net profit, total debt, equity and operating cash flow
- Review the matched label, source page, evidence row, method, and confidence before saving
- Store companies, financial periods, standardized financial items, and extraction provenance in SQLite
- Calculate current ratio, quick ratio, working capital, net profit margin and debt-to-equity
- Display basic rule-based liquidity observations

**Important:** The extractor is conservative, evidence-first, and not guaranteed. It ranks table/text-row candidates, attempts to align values with the requested fiscal-year column, and shows the original snippet, page, detected scope, method and confidence. The form pre-fills only stronger candidates; all saved values still require user review. Always check the year column, standalone/consolidated scope and unit against the PDF. Scanned PDFs may require OCR, which is not included. The app stores the uploaded filename and per-value provenance, but deletes the temporary PDF after extraction.

## Authentication
- New users can create an account at `/signup`; existing users sign in at `/login`.
- Passwords are stored as Werkzeug password hashes, not as plain text.
- Dashboard and Company Analysis routes require a signed-in session. Use **Sign out** in the top bar to end the session.
- The `users` table is created automatically by `schema.sql` when the app initializes.

For local development, the app generates a temporary session key if `SMARTFIN_SECRET_KEY` is not set. Before deployment, configure a persistent secret key in the environment and enable secure cookies when serving over HTTPS:
```powershell
$env:SMARTFIN_SECRET_KEY = "replace-with-a-long-random-secret"
$env:SMARTFIN_COOKIE_SECURE = "true"
python app.py
```
Keep the secret private. The example value above is only a placeholder.

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

## Current application database status
The existing Flask prototype still uses SQLite and its tables are created from `schema.sql`. The Oracle implementation is maintained separately under `oracle/`; it is not yet the backend used by the website. Do not claim the app stores data in Oracle until the Python connection and upload/review flow have been switched and tested. Avoid putting database credentials or session secrets into Git.
