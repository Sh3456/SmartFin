# Corporate Risk Manager

A small working DBMS project using Python, Flask and SQLite.

## Features
- Dashboard: active/critical counts and department exposure
- Risk register: search, department/status filters, add and reassess risks
- Automatic score: likelihood × impact (1–25), calculated by SQLite
- Mitigation controls: assign actions, owners, due dates, and mark completion
- Audit history: changes are logged in the same transaction as the update
- SQL examples: JOIN, GROUP BY, HAVING, RANK window function
- Constraints, foreign keys, indexes, and a reporting view

## Run (Windows PowerShell)
Install Python 3.10+ first, then run in this folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

The database schema is created automatically. To load sample records, open a second terminal in the same folder and run:

```powershell
python -c "import app; app.seed()"
```

Seed IDs use INSERT OR IGNORE, so repeating the seed command will not duplicate demo rows.

## Risk score bands
Low 1–4; Moderate 5–9; High 10–16; Critical 17–25. These are illustrative thresholds.

## Database design
The five tables separate departments, risk categories, risks, mitigation controls and audit events. Foreign keys prevent orphan rows; CHECK constraints restrict valid scores/statuses; the generated score column avoids inconsistent manually entered scores. Indexes help common filters, and each mutation plus its audit event is committed or rolled back together.

This is an educational MVP, not a production security system. Before production, add authentication and authorization, configure a strong secret key, disable debug mode, and implement backups.
