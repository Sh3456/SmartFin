PRAGMA foreign_keys = ON;

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
