# SmartFin Project Plan — SQL First

The goal is a small DBMS project: analyze one TCS annual report, review extracted values, save approved values to Oracle, and calculate three liquidity metrics. The UI is only a way to use the database.

## Milestones

1. **Oracle schema:** run `oracle/01_schema.sql` in Oracle SQL Developer. It creates the five financial tables, integrity constraints, indexes, and the liquidity view.
2. **Standard financial items:** run `oracle/02_seed_financial_items.sql` to create the small label dictionary.
3. **Learn and test SQL:** run `oracle/03_analysis_queries.sql` to inspect periods, review pending extraction candidates, query approved values, and calculate ratios.
4. **Validation with PL/SQL:** run `oracle/04_validate_and_save.sql`. Review a candidate before calling `VALIDATE_AND_SAVE_FINANCIAL_VALUE` to promote it into `FINANCIAL_VALUE`.
5. **Python-to-Oracle integration:** configure Oracle connection credentials locally; make the PDF extractor insert candidates into `RAW_FINANCIAL_DATA` and make the review page call the validation procedure.
6. **Connect the small UI:** use Oracle-backed queries for the Dashboard and Company Analysis sections only.

## Scope boundaries

- Keep the core workflow to one TCS annual report for the first milestone.
- Metrics: current ratio, quick ratio, and working capital.
- Quick ratio for this project is defined as (current assets - inventory) / current liabilities.
- Every extracted value must be checked for label, fiscal year, statement scope (standalone/consolidated), and units before approval.
- No machine learning, RAG, LLM, forecasting, or complex dashboard work.

## Current status

The Oracle schema and SQL/PLSQL scripts are in `oracle/`. The Flask web prototype still uses SQLite; milestone 5 is required before the website actually reads and writes Oracle data. The Oracle scripts should be run and tested in an Oracle environment; they have not been executed against the user's database from this repository-editing session.
