# Corporate Risk Manager

A small DBMS-focused corporate risk register built with Python and SQLite.

## Scope
- Manage departments, risk categories, risks, mitigation controls, and audit history.
- Calculate risk score as likelihood × impact (1–25).
- Filter risks by department, status, and score.
- Run reports using JOINs, GROUP BY, HAVING, and window functions.
- Keep reassessment changes transactional and record them in an audit log.

No financial-statement ingestion, PDF extraction, ML, RAG, or LLM layers are included.

## Run
Requires Python 3.10+; no third-party packages are needed.

```bash
python app.py init
python app.py seed
python app.py risks
python app.py report
```

The local database `corporate_risk.db` is created automatically. Do not commit real corporate risk data.

## Files
- `schema.sql` — tables, constraints, indexes, and views.
- `seed.sql` — small demo dataset.
- `queries.sql` — advanced SQL report examples.
- `app.py` — CLI, CRUD, transactions, and audit logging.

Risk score = likelihood × impact. Demo bands: Low (1–4), Moderate (5–9), High (10–16), Critical (17–25). Adjust thresholds to match your organization's policy.
