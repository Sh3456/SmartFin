# SmartFin Oracle SQL Track

This directory is the SQL-first database implementation for SmartFin. It keeps the first milestone deliberately small: one company's annual-report values, a human review step, and three liquidity calculations.

## Run scripts in this order

Use Oracle SQL Developer and connect to your own project schema. Open each script and run it with **F5 (Run Script)**.

1. `01_schema.sql` — creates the five core tables, indexes, and a liquidity input view.
2. `02_seed_financial_items.sql` — inserts/updates the small standard financial-item dictionary. It is safe to run again.
3. `03_analysis_queries.sql` — example SELECTs for the review queue, stored values, ratios, and year-over-year comparison.
4. `04_validate_and_save.sql` — creates a PL/SQL procedure to approve an extracted candidate after review.

## Core database flow

`PDF text extractor (Python)` → `RAW_FINANCIAL_DATA (PENDING)` → reviewer calls `VALIDATE_AND_SAVE_FINANCIAL_VALUE` → `FINANCIAL_VALUE` → analysis queries.

- `COMPANY`: company master record.
- `FINANCIAL_PERIOD`: fiscal year, statement scope, currency and unit.
- `FINANCIAL_ITEM`: small set of standard financial labels/metric definitions.
- `RAW_FINANCIAL_DATA`: proposed extracted numbers plus source label/page/evidence and status.
- `FINANCIAL_VALUE`: approved, standardized values used for calculations.

The unique constraint on `FINANCIAL_PERIOD (COMPANY_ID, FISCAL_YEAR, STATEMENT_SCOPE)` prevents duplicate reporting periods. The unique constraint on `FINANCIAL_VALUE (PERIOD_ID, ITEM_ID)` prevents two approved values for the same item in one period. Foreign keys maintain relationships, and check constraints validate report scope, units, confidence scores, and review status.

## Project formulas

- Current ratio = Current assets / Current liabilities
- Quick ratio = (Current assets − Inventory) / Current liabilities
- Working capital = Current assets − Current liabilities

The quick-ratio formula above is the project's simplified MVP definition. Every extracted candidate must be checked against the PDF for year, standalone/consolidated scope, units, and source label before approval.

## Important current status

The existing Flask prototype still uses SQLite. These files create the Oracle schema and SQL/PLSQL layer, but they do **not** silently switch the website to Oracle. Python-to-Oracle connection and extractor inserts are a separate next step, requiring an Oracle connection string and credentials configured locally, not committed to GitHub.

Do not commit database passwords or session secrets to the repository.
