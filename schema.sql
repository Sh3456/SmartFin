PRAGMA foreign_keys = ON;

-- SmartFin user accounts. Passwords are stored as Werkzeug password hashes.
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) BETWEEN 1 AND 100),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);


CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL UNIQUE,
    business_unit TEXT
);

CREATE TABLE IF NOT EXISTS risk_categories (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS risks (
    risk_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    department_id INTEGER NOT NULL REFERENCES departments(department_id),
    category_id INTEGER NOT NULL REFERENCES risk_categories(category_id),
    likelihood_score INTEGER NOT NULL CHECK (likelihood_score BETWEEN 1 AND 5),
    impact_score INTEGER NOT NULL CHECK (impact_score BETWEEN 1 AND 5),
    risk_score INTEGER GENERATED ALWAYS AS (likelihood_score * impact_score) STORED,
    status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Mitigated','Closed')),
    identified_date TEXT NOT NULL DEFAULT (date('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mitigation_controls (
    control_id INTEGER PRIMARY KEY,
    risk_id INTEGER NOT NULL REFERENCES risks(risk_id) ON DELETE CASCADE,
    control_title TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Planned'
        CHECK (status IN ('Planned','In Progress','Completed','Cancelled')),
    due_date TEXT,
    completion_date TEXT,
    CHECK (completion_date IS NULL OR status = 'Completed')
);

CREATE TABLE IF NOT EXISTS risk_audit_logs (
    audit_id INTEGER PRIMARY KEY,
    risk_id INTEGER REFERENCES risks(risk_id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    details TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_risks_department ON risks(department_id);
CREATE INDEX IF NOT EXISTS idx_risks_status ON risks(status);
CREATE INDEX IF NOT EXISTS idx_risks_score ON risks(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_controls_risk_status ON mitigation_controls(risk_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_risk_date ON risk_audit_logs(risk_id, changed_at DESC);

CREATE VIEW IF NOT EXISTS v_department_risk_exposure AS
SELECT d.department_id, d.department_name,
       COUNT(r.risk_id) AS risk_count,
       COALESCE(SUM(r.risk_score), 0) AS total_risk_exposure,
       SUM(CASE WHEN r.risk_score >= 17 THEN 1 ELSE 0 END) AS critical_risks
FROM departments d
LEFT JOIN risks r ON r.department_id = d.department_id AND r.status <> 'Closed'
GROUP BY d.department_id, d.department_name;

 
-- Company financial analysis (separate from the operational risk register)
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS financial_periods (
    period_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    fiscal_year TEXT NOT NULL,
    unit TEXT NOT NULL CHECK (unit IN ('INR crore','INR lakh','INR')),
    source_filename TEXT,
    statement_scope TEXT NOT NULL DEFAULT 'CONSOLIDATED'
        CHECK (statement_scope IN ('STANDALONE','CONSOLIDATED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(company_id, fiscal_year, statement_scope)
);

CREATE TABLE IF NOT EXISTS financial_values (
    period_id INTEGER NOT NULL REFERENCES financial_periods(period_id) ON DELETE CASCADE,
    item_code TEXT NOT NULL CHECK (item_code IN
        ('CURRENT_ASSETS','CURRENT_LIABILITIES','INVENTORY','REVENUE','NET_PROFIT','TOTAL_DEBT','EQUITY','OPERATING_CASH_FLOW')),
    item_value REAL NOT NULL CHECK (
        item_value >= 0 OR item_code IN ('NET_PROFIT','OPERATING_CASH_FLOW')
    ),
    source_page INTEGER CHECK (source_page IS NULL OR source_page > 0),
    source_label TEXT,
    source_snippet TEXT,
    extraction_confidence REAL CHECK (
        extraction_confidence IS NULL OR extraction_confidence BETWEEN 0 AND 1
    ),
    validation_status TEXT NOT NULL DEFAULT 'MANUAL_REVIEWED'
        CHECK (validation_status IN ('VALIDATED','MANUAL_REVIEWED')),
    PRIMARY KEY(period_id, item_code)
);

CREATE INDEX IF NOT EXISTS idx_financial_periods_company_year
    ON financial_periods(company_id, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_financial_values_item
    ON financial_values(item_code, period_id);

CREATE VIEW IF NOT EXISTS v_company_liquidity AS
SELECT c.company_name, p.fiscal_year, p.unit,
       MAX(CASE WHEN v.item_code='CURRENT_ASSETS' THEN v.item_value END) AS current_assets,
       MAX(CASE WHEN v.item_code='CURRENT_LIABILITIES' THEN v.item_value END) AS current_liabilities,
       MAX(CASE WHEN v.item_code='INVENTORY' THEN v.item_value END) AS inventory,
       CASE WHEN MAX(CASE WHEN v.item_code='CURRENT_LIABILITIES' THEN v.item_value END) > 0
         THEN ROUND(MAX(CASE WHEN v.item_code='CURRENT_ASSETS' THEN v.item_value END) /
           MAX(CASE WHEN v.item_code='CURRENT_LIABILITIES' THEN v.item_value END), 2) END AS current_ratio
FROM companies c JOIN financial_periods p USING(company_id)
LEFT JOIN financial_values v USING(period_id)
GROUP BY c.company_id, c.company_name, p.period_id, p.fiscal_year, p.unit;
