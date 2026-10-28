from contextlib import contextmanager
from pathlib import Path
import os
import secrets
import sqlite3
from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "corporate_risk.db"
app = Flask(__name__)
# Set SMARTFIN_SECRET_KEY to a persistent random value before deploying.
app.secret_key = os.environ.get("SMARTFIN_SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SMARTFIN_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}

@contextmanager
def db():
    con = sqlite3.connect(DB_FILE, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def initialize():
    with db() as con:
        con.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        # Add provenance and statement-scope columns to databases created by earlier versions.
        period_columns = {row["name"] for row in con.execute("PRAGMA table_info(financial_periods)")}
        if "statement_scope" not in period_columns:
            con.execute("ALTER TABLE financial_periods ADD COLUMN statement_scope TEXT NOT NULL DEFAULT 'CONSOLIDATED' CHECK (statement_scope IN ('STANDALONE','CONSOLIDATED'))")
        value_columns = {row["name"] for row in con.execute("PRAGMA table_info(financial_values)")}
        for column, definition in (
            ("source_page", "INTEGER"),
            ("source_label", "TEXT"),
            ("source_snippet", "TEXT"),
            ("extraction_confidence", "REAL"),
            ("validation_status", "TEXT NOT NULL DEFAULT 'MANUAL_REVIEWED' CHECK (validation_status IN ('VALIDATED','MANUAL_REVIEWED'))"),
        ):
            if column not in value_columns:
                con.execute(f"ALTER TABLE financial_values ADD COLUMN {column} {definition}")
        con.execute("CREATE INDEX IF NOT EXISTS idx_financial_values_item ON financial_values(item_code, period_id)")
    _migrate_financial_values_allow_losses()
    _migrate_financial_periods_unique_scope()


def _migrate_financial_values_allow_losses():
    """Rebuild the old financial_values table when it rejected losses/cash outflows."""
    con = sqlite3.connect(DB_FILE, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        row = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='financial_values'").fetchone()
        if not row:
            return
        ddl = re.sub(r"\s+", " ", row["sql"] or "").lower()
        if "item_value >= 0" not in ddl or "or item_code in ('net_profit','operating_cash_flow')" in ddl:
            return
        con.execute("BEGIN")
        con.execute("""CREATE TABLE financial_values_new (
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
        )""")
        con.execute("""INSERT INTO financial_values_new
            (period_id,item_code,item_value,source_page,source_label,source_snippet,extraction_confidence,validation_status)
            SELECT period_id,item_code,item_value,source_page,source_label,source_snippet,extraction_confidence,validation_status
            FROM financial_values""")
        con.execute("DROP TABLE financial_values")
        con.execute("ALTER TABLE financial_values_new RENAME TO financial_values")
        con.execute("CREATE INDEX IF NOT EXISTS idx_financial_values_item ON financial_values(item_code, period_id)")
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def _migrate_financial_periods_unique_scope():
    """Let one company/year store standalone and consolidated periods separately."""
    con = sqlite3.connect(DB_FILE, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        row = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='financial_periods'").fetchone()
        if not row:
            return
        ddl = re.sub(r"\s+", " ", row["sql"] or "").lower()
        if "unique(company_id, fiscal_year, statement_scope)" in ddl:
            return
        con.execute("BEGIN")
        con.execute("""CREATE TABLE financial_periods_new (
            period_id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
            fiscal_year TEXT NOT NULL,
            unit TEXT NOT NULL CHECK (unit IN ('INR crore','INR lakh','INR')),
            source_filename TEXT,
            statement_scope TEXT NOT NULL DEFAULT 'CONSOLIDATED'
                CHECK (statement_scope IN ('STANDALONE','CONSOLIDATED')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(company_id, fiscal_year, statement_scope)
        )""")
        con.execute("""INSERT INTO financial_periods_new
            (period_id,company_id,fiscal_year,unit,source_filename,statement_scope,created_at)
            SELECT period_id,company_id,fiscal_year,unit,source_filename,statement_scope,created_at
            FROM financial_periods""")
        con.execute("DROP TABLE financial_periods")
        con.execute("ALTER TABLE financial_periods_new RENAME TO financial_periods")
        con.execute("CREATE INDEX IF NOT EXISTS idx_financial_periods_company_year ON financial_periods(company_id, fiscal_year)")
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def seed():
    with db() as con:
        con.executescript((ROOT / "seed.sql").read_text(encoding="utf-8"))

def query(sql, args=()):
    with db() as con:
        return con.execute(sql, args).fetchall()

def band(score):
    return "Critical" if score >= 17 else "High" if score >= 10 else "Moderate" if score >= 5 else "Low"

AUTH_PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% if mode == 'login' %}Sign in{% else %}Create account{% endif %} · SmartFin</title>
<style>
:root{color-scheme:dark;--bg:#09090b;--panel:#111113;--line:#29292e;--text:#f4f4f5;--muted:#a1a1aa;--blue:#4f46e5;--purple:#a855f7}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 12% 10%,#1c1b43 0,transparent 38%),var(--bg);color:var(--text);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:inherit;text-decoration:none}.layout{min-height:100vh;display:grid;grid-template-columns:minmax(0,1.05fr) minmax(380px,.95fr);max-width:1440px;margin:auto}.story{padding:clamp(28px,6vw,84px);display:flex;flex-direction:column;justify-content:space-between;min-height:100vh}.brand{display:flex;gap:12px;align-items:center;font-size:21px;font-weight:800;letter-spacing:-.5px}.brand-mark{width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#4f46e5,#a855f7);display:grid;place-items:center}.brand small{display:block;color:var(--muted);font-size:11px;font-weight:500;letter-spacing:0;margin-top:-2px}.story-copy{max-width:520px;padding:48px 0}.eyebrow{color:#a5b4fc;text-transform:uppercase;font-weight:800;font-size:11px;letter-spacing:1.5px}.story h1{font-size:clamp(34px,4vw,57px);line-height:1.08;letter-spacing:-2.2px;margin:16px 0}.story p{color:#a1a1aa;font-size:15px;max-width:460px;line-height:1.8}.feature{display:flex;gap:13px;align-items:flex-start;border-top:1px solid #282831;padding:17px 0}.feature-icon{width:38px;height:38px;border:1px solid #30304a;background:#17172a;border-radius:11px;display:grid;place-items:center;color:#c4b5fd;font-size:17px;flex-shrink:0}.feature strong{display:block;font-size:13px}.feature span{color:var(--muted);font-size:12px}
.form-side{display:grid;place-items:center;padding:28px;background:linear-gradient(145deg,rgba(255,255,255,.025),transparent 55%);border-left:1px solid #222229}.form-card{width:min(100%,420px);padding:clamp(22px,4vw,38px);background:rgba(17,17,19,.94);border:1px solid #303036;border-radius:20px;box-shadow:0 24px 90px #0005}.form-card h2{font-size:27px;letter-spacing:-.8px;margin:7px 0 6px}.muted{color:var(--muted);font-size:13px}.form-card label{display:block;font-size:12px;color:#e4e4e7;font-weight:650;margin-top:17px}.form-card input{display:block;width:100%;margin-top:7px;padding:12px 13px;border:1px solid #3f3f46;border-radius:9px;background:#0b0b0d;color:#fff;font:inherit;outline:none}.form-card input:focus{border-color:#818cf8;box-shadow:0 0 0 3px #4f46e526}.submit{width:100%;margin-top:23px;padding:12px 15px;border:0;border-radius:9px;background:linear-gradient(100deg,#4f46e5,#6d4ce8);color:#fff;font:inherit;font-weight:750;cursor:pointer}.submit:hover{filter:brightness(1.1)}.switch{text-align:center;color:var(--muted);font-size:12px;margin:22px 0 0}.switch a{color:#c4b5fd;font-weight:700}.flash{padding:11px 12px;border:1px solid #854d0e;background:#422006;color:#fde68a;border-radius:9px;margin:16px 0 4px;font-size:12px}.flash.error{border-color:#7f1d1d;background:#3b1117;color:#fecaca}.flash.success{border-color:#166534;background:#123326;color:#bbf7d0}.secure-note{display:flex;align-items:center;gap:8px;color:#71717a;font-size:11px;margin-top:24px;justify-content:center}
@media(max-width:820px){.layout{grid-template-columns:1fr}.story{min-height:auto;padding:24px 24px 8px}.story-copy{padding:36px 0 16px}.story h1{font-size:35px}.feature-list{display:none}.form-side{border-left:0;padding:12px 20px 32px}.form-card{max-width:480px}.story p{font-size:13px}}
@media(max-width:420px){.story{padding:22px 18px 0}.form-side{padding:12px 14px 24px}.form-card{padding:24px 20px}.story h1{font-size:31px}}
</style>
</head>
<body><div class="layout">
<section class="story">
  <a class="brand" href="{{ url_for('login') }}"><span class="brand-mark">S</span><span>SmartFin<small>Financial intelligence, made clear</small></span></a>
  <div class="story-copy"><div class="eyebrow">Company financial analysis</div><h1>Understand the numbers. Make clearer decisions.</h1><p>Review annual-report figures and turn verified financial data into useful liquidity and performance insights.</p>
    <div class="feature-list">
      <div class="feature"><span class="feature-icon">↗</span><div><strong>One clear dashboard</strong><span>See your latest financial indicators in one place.</span></div></div>
      <div class="feature"><span class="feature-icon">▤</span><div><strong>PDF-to-insight workflow</strong><span>Upload, verify extracted figures, then calculate ratios.</span></div></div>
      <div class="feature"><span class="feature-icon">✓</span><div><strong>You stay in control</strong><span>Review values before they become saved financial data.</span></div></div>
    </div>
  </div>
  <div class="muted">SmartFin · Financial statement analyzer</div>
</section>
<section class="form-side"><div class="form-card">
  <div class="eyebrow">{% if mode == 'login' %}Welcome back{% else %}Get started{% endif %}</div>
  <h2>{% if mode == 'login' %}Sign in to SmartFin{% else %}Create your account{% endif %}</h2>
  <p class="muted">{% if mode == 'login' %}Enter your account details to continue to your workspace.{% else %}Create an account to save and review your company analyses.{% endif %}</p>
  {% for category, message in get_flashed_messages(with_categories=true) %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}
  {% if mode == 'login' %}
  <form method="post" action="{{ url_for('login') }}">
    <input type="hidden" name="next" value="{{ next_url }}">
    <label for="email">Email address</label><input id="email" name="email" type="email" autocomplete="username" maxlength="254" placeholder="you@company.com" required autofocus>
    <label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" placeholder="Enter your password" required>
    <button class="submit" type="submit">Sign in →</button>
  </form>
  <p class="switch">New to SmartFin? <a href="{{ url_for('signup') }}">Create an account</a></p>
  {% else %}
  <form method="post" action="{{ url_for('signup') }}">
    <label for="full_name">Full name</label><input id="full_name" name="full_name" autocomplete="name" maxlength="100" placeholder="Your name" required autofocus>
    <label for="email">Email address</label><input id="email" name="email" type="email" autocomplete="email" maxlength="254" placeholder="you@company.com" required>
    <label for="password">Password</label><input id="password" name="password" type="password" autocomplete="new-password" minlength="8" placeholder="At least 8 characters" required>
    <label for="confirm_password">Confirm password</label><input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" minlength="8" placeholder="Re-enter your password" required>
    <button class="submit" type="submit">Create account →</button>
  </form>
  <p class="switch">Already have an account? <a href="{{ url_for('login') }}">Sign in</a></p>
  {% endif %}
  <div class="secure-note">▣ &nbsp; Passwords are stored as secure hashes</div>
</div></section>
</div></body></html>
"""

@app.before_request
def require_login():
    # Only authentication pages are public. Keep every workspace endpoint private.
    if request.endpoint is None or request.endpoint in {"login", "signup", "logout", "static"}:
        return None
    if not session.get("user_id"):
        return redirect(url_for("login", next=request.path))

@app.get("/login")
@app.post("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("home"))
    next_url = request.args.get("next", "")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user_rows = query(
            "SELECT user_id, full_name, email, password_hash FROM users WHERE email = ?",
            (email,),
        ) if email else []
        if not user_rows or not check_password_hash(user_rows[0]["password_hash"], password):
            flash("Email or password is incorrect.", "error")
            return redirect(url_for("login"))
        user = user_rows[0]
        session.clear()
        session["user_id"] = user["user_id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]
        target = request.form.get("next", "").strip()
        # Only permit a local absolute path to prevent external redirects.
        if target.startswith("/") and not target.startswith("//") and chr(92) not in target:
            return redirect(target)
        return redirect(url_for("home"))
    return render_template_string(AUTH_PAGE, mode="login", next_url=next_url)

@app.get("/signup")
@app.post("/signup")
def signup():
    if session.get("user_id"):
        return redirect(url_for("home"))
    if request.method == "POST":
        full_name = " ".join(request.form.get("full_name", "").split())
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not full_name or len(full_name) > 100 or "@" not in email or len(email) > 254:
            flash("Enter a valid name and email address.", "error")
            return redirect(url_for("signup"))
        if len(password) < 8:
            flash("Choose a password with at least 8 characters.", "error")
            return redirect(url_for("signup"))
        if password != confirm_password:
            flash("The passwords do not match.", "error")
            return redirect(url_for("signup"))
        try:
            with db() as con:
                con.execute(
                    "INSERT INTO users(full_name, email, password_hash) VALUES (?, ?, ?)",
                    (full_name, email, generate_password_hash(password)),
                )
                user_id = con.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()["user_id"]
            session.clear()
            session["user_id"] = user_id
            session["user_name"] = full_name
            session["user_email"] = email
            flash("Your account is ready. Welcome to SmartFin!", "success")
            return redirect(url_for("home"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists. Please sign in.", "error")
            return redirect(url_for("signup"))
    return render_template_string(AUTH_PAGE, mode="signup", next_url="")

@app.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


BASE = """
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SmartFin — Financial Intelligence</title>
<style>
:root{color-scheme:dark;--bg:#09090b;--panel:#111113;--panel2:#18181b;--line:#29292e;--text:#f4f4f5;--muted:#a1a1aa;--blue:#4f46e5;--green:#55c38e;--purple:#a855f7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:inherit;text-decoration:none}button,.btn{border:1px solid transparent;border-radius:9px;padding:10px 14px;background:var(--blue);color:white;font:inherit;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px}.btn.secondary,button.secondary{background:var(--panel2);border-color:var(--line)}.btn:hover,button:hover{filter:brightness(1.12)}
.app{min-height:100vh}.sidebar{position:fixed;inset:0 auto 0 0;width:238px;background:#0c0c0e;border-right:1px solid var(--line);padding:25px 16px;display:flex;flex-direction:column;gap:28px;z-index:5}
.brand{display:flex;align-items:center;gap:11px;padding:0 8px;font-size:19px;font-weight:750;letter-spacing:-.6px}.brand-mark{width:35px;height:35px;border-radius:11px;background:linear-gradient(140deg,#4f46e5,#8b5cf6);display:grid;place-items:center;font-weight:800}
.nav-label{color:#71717a;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;padding:0 10px;margin-bottom:6px}.nav{display:grid;gap:6px}.nav a{display:flex;align-items:center;gap:12px;padding:11px 12px;border-radius:9px;color:#a1a1aa;font-weight:550}.nav a.active,.nav a:hover{background:#202027;color:white}.nav a.active{box-shadow:inset 2px 0 #818cf8}.nav-icon{width:20px;text-align:center;font-size:16px}
.sidebar-bottom{margin-top:auto;border:1px solid var(--line);background:#121214;border-radius:12px;padding:14px}.sidebar-bottom strong{display:block;font-size:12px}.sidebar-bottom span{font-size:11px;color:var(--muted)}
.main{margin-left:238px;padding:28px clamp(18px,3vw,46px) 48px;max-width:1700px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:30px}.crumb{color:var(--muted);font-size:12px}.top-actions{display:flex;align-items:center;gap:10px}.logout-form{margin:0}.logout-form button{padding:8px 11px;font-size:12px;background:var(--panel2);border-color:var(--line)}.avatar{width:35px;height:35px;border-radius:50%;background:#27272a;display:grid;place-items:center;border:1px solid #3f3f46}.eyebrow{color:#a5b4fc;font-size:11px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase}
h1{font-size:clamp(25px,3vw,34px);letter-spacing:-1.2px;margin:5px 0 6px;line-height:1.2}h2{font-size:17px;letter-spacing:-.3px;margin:0 0 5px}h3{font-size:14px;margin:0 0 12px}.sub{color:var(--muted);margin:0}.page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:25px}.head-actions{display:flex;gap:9px;flex-wrap:wrap}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.card,section{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:20px;min-width:0;margin:0 0 16px;overflow:auto}.metric-label{color:var(--muted);font-size:12px}.num{font-size:clamp(23px,2.3vw,31px);font-weight:750;letter-spacing:-1px;margin:10px 0 7px}.metric-foot{font-size:11px;color:var(--muted)}.metric-icon{float:right;width:34px;height:34px;border-radius:10px;background:#202027;display:grid;place-items:center;color:#a5b4fc}
.content-grid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(280px,1fr);gap:16px;margin-top:3px}.section-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:18px}.section-head p{margin:3px 0 0;color:var(--muted);font-size:12px}
table{width:100%;border-collapse:collapse;min-width:520px}td,th{text-align:left;border-bottom:1px solid #27272a;padding:12px 9px;font-size:12px}td{color:#e4e4e7}th{font-size:10px;color:#a1a1aa;text-transform:uppercase;letter-spacing:.8px;font-weight:650}tr:last-child td{border-bottom:0}
.badge{display:inline-flex;align-items:center;border-radius:99px;padding:4px 8px;background:#27272a;color:#d4d4d8;font-size:10px;font-weight:700}.badge.good{background:#123326;color:#86efac}.badge.warn{background:#3b2b12;color:#fcd34d}.badge.info{background:#24245a;color:#c7d2fe}.badge.bad{background:#431b24;color:#fda4af}
.chart{height:180px;display:flex;align-items:flex-end;gap:clamp(9px,2vw,22px);padding:15px 8px 0;border-bottom:1px solid #34343a;background:repeating-linear-gradient(to bottom,transparent 0,transparent 43px,#222228 44px)}.bar-group{height:100%;flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:9px;min-width:0}.bar{width:min(28px,65%);min-height:5px;border-radius:8px 8px 3px 3px;background:linear-gradient(180deg,#6366f1,#4338ca)}.bar.green{background:linear-gradient(180deg,#6ee7b7,#16a34a)}.bar-label{font-size:10px;color:var(--muted)}
.snapshot{display:grid;gap:14px}.snapshot-row{display:flex;align-items:flex-start;gap:11px}.dot{width:8px;height:8px;border-radius:50%;background:var(--green);margin-top:6px;flex-shrink:0}.dot.amber{background:#fbbf24}.snapshot-row strong{display:block;font-size:12px}.snapshot-row span{font-size:11px;color:var(--muted)}
input,select,textarea{width:100%;padding:11px 12px;border:1px solid #3f3f46;background:#0c0c0e;color:var(--text);border-radius:8px;margin:6px 0 14px;font:inherit}input[type=file]{padding:9px}label{font-weight:600;font-size:12px;color:#d4d4d8}.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.muted{color:var(--muted);font-size:12px}.flash{background:#123326;color:#bbf7d0;border:1px solid #166534;padding:12px 14px;border-radius:9px;margin:0 0 16px}.empty{padding:24px;text-align:center;color:var(--muted);font-size:12px}.form-section{max-width:920px}.divider{height:1px;background:var(--line);margin:18px 0}details{margin-top:8px;font-size:11px;color:#c4b5fd}summary{cursor:pointer}.evidence{white-space:pre-wrap;overflow-wrap:anywhere;max-height:180px;overflow:auto;background:#09090b;border:1px solid #29292e;padding:9px;border-radius:7px;color:#d4d4d8;font:11px/1.5 ui-monospace,monospace}
@media(max-width:1100px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.content-grid{grid-template-columns:1fr}.sidebar{width:205px}.main{margin-left:205px}}
@media(max-width:650px){.sidebar{position:sticky;top:0;width:100%;height:auto;padding:12px 14px;gap:12px;border-right:0;border-bottom:1px solid var(--line)}.brand{font-size:16px}.nav-label,.sidebar-bottom{display:none}.nav{display:flex;gap:6px}.nav a{flex:1;justify-content:center;padding:9px 8px;font-size:12px}.main{margin:0;padding:20px 14px}.topbar{margin-bottom:22px}.page-head{align-items:flex-start;flex-direction:column}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.card,section{padding:15px;border-radius:12px}.num{font-size:23px}.top-actions .btn{padding:8px 10px}}
@media(max-width:390px){.grid{grid-template-columns:1fr}.topbar{align-items:flex-start;flex-direction:column}}
</style></head><body><div class="app">
<aside class="sidebar"><a class="brand" href="/"><span class="brand-mark">S</span><span>SmartFin</span></a>
<div><div class="nav-label">Workspace</div><nav class="nav"><a href="/" class="{% if request.path == '/' %}active{% endif %}"><span class="nav-icon">▦</span>Dashboard</a><a href="/company-analysis" class="{% if request.path.startswith('/company-analysis') %}active{% endif %}"><span class="nav-icon">◫</span>Company Analysis</a></nav></div>
<div class="sidebar-bottom"><strong>Financial Intelligence</strong><span>Annual reports · Ratios · Trends</span></div></aside>
<main class="main"><div class="topbar"><div><div class="crumb">SmartFin <span style="color:#52525b">/</span> {% if request.path.startswith('/company-analysis') %}Company Analysis{% else %}Dashboard{% endif %}</div></div><div class="top-actions"><span class="muted">{{ session.get("user_name", "Financial workspace") }}</span><span class="avatar">{{ session.get("user_name", "S")[:1]|upper }}</span><form class="logout-form" method="post" action="{{ url_for('logout') }}"><button class="secondary" type="submit">Sign out</button></form></div></div>
{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}</main></div></body></html>
"""

def page(body, **ctx):
    return render_template_string(BASE, body=render_template_string(body, **ctx))

@app.get("/")
def home():
    periods = query("""SELECT p.period_id,p.fiscal_year,p.unit,c.company_name,
        COUNT(v.item_code) AS item_count
        FROM financial_periods p JOIN companies c USING(company_id)
        LEFT JOIN financial_values v USING(period_id)
        GROUP BY p.period_id ORDER BY p.period_id DESC""")
    latest = periods[0] if periods else None
    data = {}
    if latest:
        data = {r["item_code"]: r["item_value"] for r in query(
            "SELECT item_code,item_value FROM financial_values WHERE period_id=?", (latest["period_id"],))}
    ca = data.get("CURRENT_ASSETS")
    cl = data.get("CURRENT_LIABILITIES")
    inventory = data.get("INVENTORY", 0)
    current_ratio = ca / cl if ca is not None and cl else None
    quick_ratio = (ca - inventory) / cl if ca is not None and cl else None
    working_capital = ca - cl if ca is not None and cl is not None else None
    revenue = data.get("REVENUE")
    net_profit = data.get("NET_PROFIT")
    margin = net_profit / revenue * 100 if net_profit is not None and revenue else None
    periods_by_year = sorted(periods, key=lambda p: p["fiscal_year"])[-6:]
    return page("""<div class="page-head"><div><div class="eyebrow">Financial intelligence</div><h1>Financial Overview</h1>
      <p class="sub">A clear view of company performance, liquidity and financial trends.</p></div>
      <div class="head-actions"><a class="btn secondary" href="/company-analysis">View analyses</a><a class="btn" href="/company-analysis">＋ Upload annual report</a></div></div>
      {% if latest %}<div class="muted" style="margin:-10px 0 16px">Latest analysis · <b style="color:#e4e4e7">{{latest.company_name}}</b> · {{latest.fiscal_year}} · {{latest.unit}}</div>{% endif %}
      <div class="grid">
      <div class="card"><span class="metric-icon">▤</span><div class="metric-label">Current assets</div><div class="num">{{"%.2f"|format(ca) if ca is not none else "—"}}</div><div class="metric-foot">{{latest.unit if latest else "Upload a report to begin"}}</div></div>
      <div class="card"><span class="metric-icon">↘</span><div class="metric-label">Current liabilities</div><div class="num">{{"%.2f"|format(cl) if cl is not none else "—"}}</div><div class="metric-foot">{{latest.unit if latest else "No financial data yet"}}</div></div>
      <div class="card"><span class="metric-icon">◉</span><div class="metric-label">Current ratio</div><div class="num">{{"%.2f"|format(cr) if cr is not none else "—"}}<span style="font-size:13px;color:#a1a1aa;font-weight:500">x</span></div><div class="metric-foot">Current assets ÷ current liabilities</div></div>
      <div class="card"><span class="metric-icon">＋</span><div class="metric-label">Working capital</div><div class="num">{{"%.2f"|format(wc) if wc is not none else "—"}}</div><div class="metric-foot">{{latest.unit if latest else "Current assets − liabilities"}}</div></div></div>
      <div class="content-grid"><section><div class="section-head"><div><h2>Financial periods</h2><p>Saved company reports and extraction progress</p></div><span class="badge info">{{periods|length}} periods</span></div>
      <table><tr><th>Company</th><th>Financial year</th><th>Figures</th><th>Status</th><th></th></tr>
      {% for p in periods[:6] %}<tr><td><strong>{{p.company_name}}</strong></td><td>{{p.fiscal_year}}</td><td>{{p.item_count}} items</td><td><span class="badge good">Saved</span></td><td><a href="/company-analysis/{{p.period_id}}" style="color:#a5b4fc">Analyze ↗</a></td></tr>{% else %}<tr><td colspan="5"><div class="empty">No financial periods yet. Upload an annual report to start your first analysis.</div></td></tr>{% endfor %}</table></section>
      <section><div class="section-head"><div><h2>Financial health snapshot</h2><p>Rule-based observations from the latest report</p></div></div>
      <div class="snapshot">{% if cr is not none %}<div class="snapshot-row"><span class="dot {{'amber' if cr < 1.5 else ''}}"></span><div><strong>Liquidity coverage · {{'%.2f'|format(cr)}}x</strong><span>{% if cr < 1 %}Current liabilities exceed current assets. Review short-term liquidity.{% elif cr < 1.5 %}Compare short-term coverage with the company’s industry and history.{% else %}Current assets cover current liabilities based on the saved figures.{% endif %}</span></div></div>{% else %}<div class="snapshot-row"><span class="dot amber"></span><div><strong>Liquidity analysis pending</strong><span>Save current assets and current liabilities to calculate coverage.</span></div></div>{% endif %}
      {% if margin is not none %}<div class="snapshot-row"><span class="dot"></span><div><strong>Net profit margin · {{'%.2f'|format(margin)}}%</strong><span>Net profit as a percentage of revenue for the latest saved period.</span></div></div>{% else %}<div class="snapshot-row"><span class="dot amber"></span><div><strong>Profitability data pending</strong><span>Revenue and net profit are needed to calculate margin.</span></div></div>{% endif %}
      <div class="snapshot-row"><span class="dot"></span><div><strong>Figures are reviewable</strong><span>Check units and statement scope before using the results.</span></div></div></div>
      <div class="divider"></div><a class="btn secondary" href="/company-analysis">Open Company Analysis →</a></section></div>
      <section style="margin-top:1px"><div class="section-head"><div><h2>Quick start</h2><p>Three steps from annual report to financial insight</p></div></div><div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
      <div><div class="eyebrow">01 · Upload</div><h3 style="margin-top:8px">Choose a company report</h3><p class="muted">Add the company name, financial year and annual report PDF.</p></div>
      <div><div class="eyebrow">02 · Verify</div><h3 style="margin-top:8px">Review extracted values</h3><p class="muted">Confirm financial labels, units and year columns before saving.</p></div>
      <div><div class="eyebrow">03 · Analyze</div><h3 style="margin-top:8px">Explore the ratios</h3><p class="muted">Calculate liquidity, working capital and profitability indicators.</p></div></div></section>
      """, latest=latest, periods=periods, ca=ca, cl=cl, cr=current_ratio, qr=quick_ratio, wc=working_capital, margin=margin)
@app.get("/risks")
def risks():
    status=request.args.get("status",""); dept=request.args.get("department",""); q=request.args.get("q","").strip()
    data=query("""SELECT r.*,d.department_name,c.category_name FROM risks r JOIN departments d USING(department_id)
      JOIN risk_categories c USING(category_id) WHERE (?='' OR r.status=?) AND (?='' OR d.department_id=?)
      AND (?='' OR r.title LIKE ?) ORDER BY r.risk_score DESC""",(status,status,dept,dept,q,"%"+q+"%"))
    departments=query("SELECT * FROM departments ORDER BY department_name")
    return page("""<section><h2>Risk Register</h2><form method="get" class="cols">
    <div><label>Search</label><input name="q" value="{{q}}" placeholder="Risk title"></div>
    <div><label>Status</label><select name="status"><option value="">All</option>{% for s in ['Open','Mitigated','Closed'] %}<option {% if status==s %}selected{% endif %}>{{s}}</option>{% endfor %}</select></div>
    <div><label>Department</label><select name="department"><option value="">All</option>{% for d in departments %}<option value="{{d.department_id}}" {% if dept|string==d.department_id|string %}selected{% endif %}>{{d.department_name}}</option>{% endfor %}</select></div><div><label>&nbsp;</label><button>Filter</button></div></form>
    <table><tr><th>Title</th><th>Department</th><th>Category</th><th>L×I</th><th>Score</th><th>Status</th></tr>
    {% for r in data %}<tr><td><a href="/risks/{{r.risk_id}}">{{r.title}}</a></td><td>{{r.department_name}}</td><td>{{r.category_name}}</td><td>{{r.likelihood_score}}×{{r.impact_score}}</td><td><span class="badge {{band(r.risk_score)}}">{{r.risk_score}} {{band(r.risk_score)}}</span></td><td>{{r.status}}</td></tr>{% else %}<tr><td colspan="6">No matching risks.</td></tr>{% endfor %}</table></section>""",data=data,departments=departments,status=status,dept=dept,q=q,band=band)

@app.route("/risks/new",methods=["GET","POST"])
def new_risk():
    if request.method=="POST":
        try:
            l=int(request.form["likelihood"]); i=int(request.form["impact"])
            if l not in range(1,6) or i not in range(1,6): raise ValueError()
            with db() as con:
                cur=con.execute("INSERT INTO risks(title,description,department_id,category_id,likelihood_score,impact_score) VALUES(?,?,?,?,?,?)",
                    (request.form["title"].strip(),request.form.get("description","").strip(),int(request.form["department_id"]),int(request.form["category_id"]),l,i))
                rid=cur.lastrowid
                con.execute("INSERT INTO risk_audit_logs(risk_id,action,details) VALUES(?,'CREATE',?)",(rid,"Risk created: "+request.form["title"]))
            flash("Risk created.")
            return redirect(url_for("risk_detail",rid=rid))
        except (ValueError,KeyError,sqlite3.IntegrityError): flash("Could not save. Check the required fields.")
    return page("""<section><h2>Add risk</h2><form method="post"><label>Title</label><input name="title" required maxlength="180">
    <label>Description</label><textarea name="description"></textarea><div class="cols">
    <div><label>Department</label><select name="department_id" required>{% for d in ds %}<option value="{{d.department_id}}">{{d.department_name}}</option>{% endfor %}</select></div>
    <div><label>Category</label><select name="category_id" required>{% for c in cs %}<option value="{{c.category_id}}">{{c.category_name}}</option>{% endfor %}</select></div>
    <div><label>Likelihood (1–5)</label><select name="likelihood">{% for n in range(1,6) %}<option>{{n}}</option>{% endfor %}</select></div>
    <div><label>Impact (1–5)</label><select name="impact">{% for n in range(1,6) %}<option>{{n}}</option>{% endfor %}</select></div></div><button>Create risk</button></form></section>""",ds=query("SELECT * FROM departments"),cs=query("SELECT * FROM risk_categories"))

@app.route("/risks/<int:rid>",methods=["GET","POST"])
def risk_detail(rid):
    if request.method=="POST":
        try:
            with db() as con:
                old=con.execute("SELECT * FROM risks WHERE risk_id=?",(rid,)).fetchone()
                if not old:return "Risk not found",404
                action=request.form["action"]
                if action=="reassess":
                    l=int(request.form["likelihood"]);i=int(request.form["impact"])
                    if l not in range(1,6) or i not in range(1,6):raise ValueError()
                    con.execute("UPDATE risks SET likelihood_score=?,impact_score=?,updated_at=datetime('now') WHERE risk_id=?",(l,i,rid))
                    detail=f"Risk score {old['risk_score']} -> {l*i}; likelihood {old['likelihood_score']} -> {l}; impact {old['impact_score']} -> {i}"
                else:
                    s=request.form["status"]
                    if s not in ("Open","Mitigated","Closed"):raise ValueError()
                    con.execute("UPDATE risks SET status=?,updated_at=datetime('now') WHERE risk_id=?",(s,rid))
                    detail=f"Status {old['status']} -> {s}"
                con.execute("INSERT INTO risk_audit_logs(risk_id,action,details) VALUES(?,?,?)",(rid,action.upper(),detail))
            flash("Risk updated; audit event saved.")
        except (ValueError,KeyError,sqlite3.IntegrityError):flash("Update failed; check values.")
        return redirect(url_for("risk_detail",rid=rid))
    result=query("""SELECT r.*,d.department_name,c.category_name FROM risks r JOIN departments d USING(department_id)
      JOIN risk_categories c USING(category_id) WHERE risk_id=?""",(rid,))
    if not result:return "Risk not found",404
    r=result[0]; cs=query("SELECT * FROM mitigation_controls WHERE risk_id=?",(rid,))
    return page("""<section><h2>{{r.title}}</h2><p>{{r.description}}</p><p><b>Department:</b> {{r.department_name}} | <b>Category:</b> {{r.category_name}}</p>
    <p><b>Score:</b> <span class="badge {{band(r.risk_score)}}">{{r.risk_score}} / 25 — {{band(r.risk_score)}}</span> | <b>Status:</b> {{r.status}}</p>
    <h3>Reassess</h3><form method="post"><input type="hidden" name="action" value="reassess"><div class="cols"><div><label>Likelihood</label><select name="likelihood">{% for n in range(1,6) %}<option {% if n==r.likelihood_score %}selected{% endif %}>{{n}}</option>{% endfor %}</select></div><div><label>Impact</label><select name="impact">{% for n in range(1,6) %}<option {% if n==r.impact_score %}selected{% endif %}>{{n}}</option>{% endfor %}</select></div></div><button>Save reassessment</button></form>
    <h3>Status</h3><form method="post"><input type="hidden" name="action" value="status"><select name="status">{% for s in ['Open','Mitigated','Closed'] %}<option {% if s==r.status %}selected{% endif %}>{{s}}</option>{% endfor %}</select><button>Update status</button></form>
    <p><a class="btn" href="/controls/new?risk_id={{r.risk_id}}">Add mitigation control</a></p></section>
    <section><h3>Controls</h3><table><tr><th>Control</th><th>Owner</th><th>Status</th><th>Due</th></tr>{% for c in cs %}<tr><td>{{c.control_title}}</td><td>{{c.owner_name}}</td><td>{{c.status}}</td><td>{{c.due_date or '—'}}</td></tr>{% else %}<tr><td colspan="4">No controls yet.</td></tr>{% endfor %}</table></section>""",r=r,cs=cs,band=band)

@app.route("/controls")
def controls():
    data=query("""SELECT m.*,r.title FROM mitigation_controls m JOIN risks r USING(risk_id)
      ORDER BY CASE m.status WHEN 'In Progress' THEN 1 WHEN 'Planned' THEN 2 ELSE 3 END,m.due_date""")
    return page("""<section><h2>Mitigation controls</h2><p><a class="btn" href="/controls/new">Add control</a></p><table><tr><th>Risk</th><th>Control</th><th>Owner</th><th>Status</th><th>Due</th><th>Action</th></tr>
    {% for c in data %}<tr><td><a href="/risks/{{c.risk_id}}">{{c.title}}</a></td><td>{{c.control_title}}</td><td>{{c.owner_name}}</td><td>{{c.status}}</td><td>{{c.due_date or '—'}}</td><td>{% if c.status!='Completed' %}<form method="post" action="/controls/{{c.control_id}}/complete"><button>Complete</button></form>{% else %}Done{% endif %}</td></tr>{% else %}<tr><td colspan="6">No controls added.</td></tr>{% endfor %}</table></section>""",data=data)

@app.route("/controls/new",methods=["GET","POST"])
def new_control():
    if request.method=="POST":
        try:
            rid=int(request.form["risk_id"])
            with db() as con:
                cur=con.execute("INSERT INTO mitigation_controls(risk_id,control_title,owner_name,due_date) VALUES(?,?,?,?)",
                    (rid,request.form["control_title"].strip(),request.form["owner_name"].strip(),request.form.get("due_date") or None))
                con.execute("INSERT INTO risk_audit_logs(risk_id,action,details) VALUES(?,'CONTROL_CREATED',?)",(rid,"Created control #"+str(cur.lastrowid)))
            flash("Control added.")
            return redirect(url_for("controls"))
        except (ValueError,KeyError,sqlite3.IntegrityError):flash("Could not add control.")
    return page("""<section><h2>Add mitigation control</h2><form method="post"><label>Risk</label><select name="risk_id" required>{% for r in rs %}<option value="{{r.risk_id}}" {% if selected|string==r.risk_id|string %}selected{% endif %}>#{{r.risk_id}} — {{r.title}}</option>{% endfor %}</select>
    <label>Action</label><input name="control_title" required><label>Owner</label><input name="owner_name" required><label>Due date</label><input type="date" name="due_date"><button>Add control</button></form></section>""",rs=query("SELECT risk_id,title FROM risks WHERE status!='Closed'"),selected=request.args.get("risk_id",""))

@app.post("/controls/<int:cid>/complete")
def complete(cid):
    with db() as con:
        c=con.execute("SELECT * FROM mitigation_controls WHERE control_id=?",(cid,)).fetchone()
        if not c:return "Control not found",404
        con.execute("UPDATE mitigation_controls SET status='Completed',completion_date=date('now') WHERE control_id=?",(cid,))
        con.execute("INSERT INTO risk_audit_logs(risk_id,action,details) VALUES(?,'CONTROL_COMPLETED',?)",(c["risk_id"],"Completed control #"+str(cid)))
    flash("Control marked completed.")
    return redirect(url_for("controls"))

@app.get("/audit")
def audit():
    data=query("""SELECT a.*,r.title FROM risk_audit_logs a LEFT JOIN risks r USING(risk_id)
      ORDER BY a.changed_at DESC,a.audit_id DESC LIMIT 200""")
    return page("""<section><h2>Audit history</h2><table><tr><th>When</th><th>Risk</th><th>Action</th><th>Details</th></tr>
    {% for a in data %}<tr><td>{{a.changed_at}}</td><td>{{a.title or 'Deleted risk'}}</td><td>{{a.action}}</td><td>{{a.details}}</td></tr>{% else %}<tr><td colspan="4">No changes recorded.</td></tr>{% endfor %}</table></section>""",data=data)


# ---------------- Company financial analysis ----------------
import math
import re
from financial_extractor import extract_financial_items as extract_financial_candidates
from werkzeug.utils import secure_filename

UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_FINANCIAL_ITEMS = {
    "CURRENT_ASSETS": "Current assets",
    "CURRENT_LIABILITIES": "Current liabilities",
    "INVENTORY": "Inventory",
    "REVENUE": "Revenue",
    "NET_PROFIT": "Net profit",
    "TOTAL_DEBT": "Total debt",
    "EQUITY": "Total equity",
    "OPERATING_CASH_FLOW": "Operating cash flow",
}

@app.route("/company-analysis", methods=["GET", "POST"])
def company_analysis():
    if request.method == "POST":
        uploaded = request.files.get("report")
        company_name = request.form.get("company_name", "").strip()
        fiscal_year = request.form.get("fiscal_year", "").strip()
        statement_scope = request.form.get("statement_scope", "CONSOLIDATED").upper()
        if statement_scope not in {"STANDALONE", "CONSOLIDATED"}:
            statement_scope = "CONSOLIDATED"
        if not company_name or not fiscal_year:
            flash("Enter a company name and financial year.")
            return redirect(url_for("company_analysis"))
        if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
            flash("Please upload an annual report PDF.")
            return redirect(url_for("company_analysis"))
        file_path = None
        try:
            safe_name = secure_filename(uploaded.filename)
            if not safe_name:
                raise ValueError("Invalid filename")
            stored_name = f"{__import__('uuid').uuid4().hex}_{safe_name}"
            file_path = UPLOAD_DIR / stored_name
            uploaded.save(file_path)
            values, evidence, meta = extract_financial_candidates(
                file_path, fiscal_year=fiscal_year, statement_scope=statement_scope
            )
            if not evidence:
                flash("No supported financial statement rows were identified. Try another text-based PDF or check the statement and year.")
                return redirect(url_for("company_analysis"))
            return page("""<section><h2>Review extracted figures</h2>
            <p>Company: <b>{{company}}</b> · Year: <b>{{year}}</b> · Scope: <b>{{scope}}</b></p>
            <div class="flash" style="background:#27251b;color:#fef3c7;border-color:#854d0e">{{meta.unit_note}}</div>
            <p class="muted">Candidates are ranked from the source PDF. Higher-confidence values are pre-filled; lower-confidence values are shown as evidence only. Verify the label, year column, scope and unit on the report page before saving.</p>
            <form method="post" action="/company-analysis/save">
            <input type="hidden" name="company_name" value="{{company}}">
            <input type="hidden" name="fiscal_year" value="{{year}}">
            <input type="hidden" name="statement_scope" value="{{scope}}">
            <input type="hidden" name="source_filename" value="{{filename}}">
            <div class="cols">{% for code,label in items %}
              {% set ev = evidence.get(code) %}
              <div class="card" style="padding:14px">
                <label for="{{code}}">{{label}}</label>
                <input id="{{code}}" type="number" step="any" name="{{code}}" value="{{values.get(code, '')}}" placeholder="Verify and enter value">
                {% if ev %}
                  <p class="muted">Candidate: <b>{{"%.2f"|format(ev.value)}}</b> · page {{ev.page}} · confidence {{(ev.confidence * 100)|round|int}}%</p>
                  {% if code not in values %}<p class="muted">Not auto-filled because evidence confidence is low. Verify before entering.</p>{% endif %}
                  <details><summary>View extraction evidence</summary>
                    <p class="muted">Matched label: {{ev.label}} · method: {{ev.method}} · detected page scope: {{ev.scope_seen}}</p>
                    <pre class="evidence">{{ev.snippet}}</pre>
                    <p class="muted">{{ev.reason}}</p>
                    {% if ev.ambiguous %}<p class="muted" style="color:#fcd34d">Ambiguous match: another similarly ranked row has a different value. Verify carefully.</p>{% endif %}
                    {% if ev.alternatives %}<h4>Other matching rows</h4><ul>{% for alt in ev.alternatives %}<li>Page {{alt.page}} · {{alt.label}} · {{'%.2f'|format(alt.value)}} · confidence {{(alt.confidence*100)|round|int}}%{% if alt.year_confirmed %} · year column matched{% endif %}</li>{% endfor %}</ul>{% endif %}
                  </details>
                  <input type="hidden" name="source_page_{{code}}" value="{{ev.page}}">
                  <input type="hidden" name="source_label_{{code}}" value="{{ev.label}}">
                  <input type="hidden" name="source_snippet_{{code}}" value="{{ev.snippet}}">
                  <input type="hidden" name="source_confidence_{{code}}" value="{{ev.confidence}}">
                {% else %}
                  <p class="muted">No candidate found. Enter from the report if required.</p>
                {% endif %}
              </div>
            {% endfor %}</div>
            <label>Unit for all entered values</label>
            <select name="unit">
              <option value="INR crore" {% if meta.unit_hint == 'INR crore' %}selected{% endif %}>INR crore</option>
              <option value="INR lakh" {% if meta.unit_hint == 'INR lakh' %}selected{% endif %}>INR lakh</option>
              <option value="INR" {% if meta.unit_hint == 'INR' %}selected{% endif %}>INR</option>
            </select>
            <button>Validate and save figures</button>
            </form></section>
            <section><h3>Extraction diagnostics</h3>
              <div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
                <div class="card"><div class="metric-label">PDF pages</div><div class="num">{{meta.page_count}}</div></div>
                <div class="card"><div class="metric-label">Financial item candidates</div><div class="num">{{evidence|length}}</div></div>
                <div class="card"><div class="metric-label">Target year detected</div><div class="num" style="font-size:20px">{{meta.target_year}}</div></div>
              </div>
            </section>""",
                company=company_name, year=fiscal_year, scope=statement_scope,
                filename=safe_name, items=list(ALLOWED_FINANCIAL_ITEMS.items()),
                values=values, evidence=evidence, meta=meta)
        except Exception:
            flash("Could not extract this PDF. If it is scanned or password-protected, the current extractor may not be able to read it.")
            return redirect(url_for("company_analysis"))
        finally:
            if file_path:
                file_path.unlink(missing_ok=True)

    companies = query("""SELECT c.company_name, p.fiscal_year, p.period_id, p.unit, p.statement_scope,
        COUNT(v.item_code) AS item_count FROM financial_periods p
        JOIN companies c USING(company_id) LEFT JOIN financial_values v USING(period_id)
        GROUP BY p.period_id ORDER BY c.company_name, p.fiscal_year DESC""")
    return page("""<section class="form-section"><h2>Company Financial Analysis</h2>
    <p>Upload an annual report PDF. SmartFin will search likely financial-statement rows and show the matched label, page, extraction method and confidence. Review every number before saving.</p>
    <form method="post" enctype="multipart/form-data">
    <label>Company name</label><input name="company_name" required maxlength="160" placeholder="e.g. Tata Consultancy Services">
    <label>Financial year</label><input name="fiscal_year" required maxlength="30" placeholder="e.g. FY2025-26">
    <label>Statement scope</label><select name="statement_scope"><option value="CONSOLIDATED">Consolidated</option><option value="STANDALONE">Standalone</option></select>
    <label>Annual report PDF</label><input type="file" name="report" accept=".pdf,application/pdf" required>
    <button>Upload and extract figures</button></form></section>
    <section><h2>Saved company periods</h2><table><tr><th>Company</th><th>Year</th><th>Unit</th><th>Figures saved</th><th>Scope</th><th>Report</th></tr>
    {% for p in periods %}<tr><td>{{p.company_name}}</td><td>{{p.fiscal_year}}</td><td>{{p.unit}}</td><td>{{p.item_count}}</td><td>{{p.statement_scope or 'CONSOLIDATED'}}</td><td><a href="/company-analysis/{{p.period_id}}">Analyze</a></td></tr>
    {% else %}<tr><td colspan="6">No company financial data saved yet.</td></tr>{% endfor %}</table></section>
    """, periods=companies)

@app.post("/company-analysis/save")
def save_company_financials():
    company = request.form.get("company_name", "").strip()
    year = request.form.get("fiscal_year", "").strip()
    scope = request.form.get("statement_scope", "CONSOLIDATED").upper()
    unit = request.form.get("unit", "INR crore")
    filename = request.form.get("source_filename", "").strip()
    if not company or not year or scope not in {"STANDALONE", "CONSOLIDATED"}:
        flash("Company, year and valid statement scope are required.")
        return redirect(url_for("company_analysis"))
    if unit not in {"INR crore", "INR lakh", "INR"}:
        flash("Select a supported reporting unit.")
        return redirect(url_for("company_analysis"))

    values = {}
    try:
        for code in ALLOWED_FINANCIAL_ITEMS:
            raw = request.form.get(code, "").strip()
            if not raw:
                continue
            number = float(raw)
            if not math.isfinite(number):
                raise ValueError("Value must be a finite number.")
            if number < 0 and code not in {"NET_PROFIT", "OPERATING_CASH_FLOW"}:
                raise ValueError("Negative values are only allowed for profit/loss and cash flow items.")
            values[code] = number
        if not values:
            raise ValueError("At least one financial figure is required.")
        if values.get("CURRENT_LIABILITIES") == 0:
            raise ValueError("Current liabilities must be greater than zero when supplied.")

        with db() as con:
            con.execute(
                "INSERT INTO companies(company_name) VALUES(?) ON CONFLICT(company_name) DO NOTHING",
                (company,),
            )
            company_id = con.execute(
                "SELECT company_id FROM companies WHERE company_name=?", (company,)
            ).fetchone()["company_id"]
            con.execute("""INSERT INTO financial_periods
                (company_id,fiscal_year,unit,source_filename,statement_scope)
                VALUES(?,?,?,?,?)
                ON CONFLICT(company_id,fiscal_year,statement_scope) DO UPDATE SET
                    unit=excluded.unit, source_filename=excluded.source_filename""",
                (company_id, year, unit, filename, scope))
            period_id = con.execute(
                "SELECT period_id FROM financial_periods WHERE company_id=? AND fiscal_year=? AND statement_scope=?",
                (company_id, year, scope),
            ).fetchone()["period_id"]

            for code, value in values.items():
                page_text = request.form.get(f"source_page_{code}", "").strip()
                source_page = int(page_text) if page_text.isdigit() else None
                source_label = request.form.get(f"source_label_{code}", "").strip()[:250] or None
                source_snippet = request.form.get(f"source_snippet_{code}", "").strip()[:500] or None
                confidence_text = request.form.get(f"source_confidence_{code}", "").strip()
                confidence = float(confidence_text) if confidence_text else None
                if confidence is not None and not 0 <= confidence <= 1:
                    confidence = None
                validation_status = "VALIDATED" if source_page is not None else "MANUAL_REVIEWED"
                con.execute("""INSERT INTO financial_values
                    (period_id,item_code,item_value,source_page,source_label,source_snippet,
                     extraction_confidence,validation_status)
                    VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(period_id,item_code) DO UPDATE SET
                     item_value=excluded.item_value,source_page=excluded.source_page,
                     source_label=excluded.source_label,source_snippet=excluded.source_snippet,
                     extraction_confidence=excluded.extraction_confidence,
                     validation_status=excluded.validation_status""",
                    (period_id, code, value, source_page, source_label, source_snippet,
                     confidence, validation_status))
        flash("Verified financial figures saved with source evidence.")
        return redirect(url_for("company_analysis_detail", period_id=period_id))
    except (ValueError, sqlite3.IntegrityError):
        flash("Could not save these figures. Check the values and ensure the database schema is up to date.")
        return redirect(url_for("company_analysis"))

@app.get("/company-analysis/<int:period_id>")
def company_analysis_detail(period_id):
    periods = query("""SELECT p.*,c.company_name FROM financial_periods p JOIN companies c USING(company_id)
        WHERE p.period_id=?""", (period_id,))
    if not periods:
        return "Financial period not found", 404
    p = periods[0]
    value_rows = query("""SELECT item_code,item_value,source_page,source_label,
        extraction_confidence,validation_status FROM financial_values WHERE period_id=?""", (period_id,))
    data = {r["item_code"]: r["item_value"] for r in value_rows}
    current_ratio = data.get("CURRENT_ASSETS") / data.get("CURRENT_LIABILITIES") if data.get("CURRENT_ASSETS") is not None and data.get("CURRENT_LIABILITIES") else None
    quick_ratio = (data["CURRENT_ASSETS"] - data.get("INVENTORY", 0)) / data["CURRENT_LIABILITIES"] if data.get("CURRENT_ASSETS") is not None and data.get("CURRENT_LIABILITIES") else None
    working_capital = data["CURRENT_ASSETS"] - data["CURRENT_LIABILITIES"] if data.get("CURRENT_ASSETS") is not None and data.get("CURRENT_LIABILITIES") is not None else None
    net_margin = data["NET_PROFIT"] / data["REVENUE"] * 100 if data.get("NET_PROFIT") is not None and data.get("REVENUE") else None
    debt_equity = data["TOTAL_DEBT"] / data["EQUITY"] if data.get("TOTAL_DEBT") is not None and data.get("EQUITY") else None
    warnings = []
    if current_ratio is not None:
        if current_ratio < 1:
            warnings.append("Current ratio below 1: current liabilities exceed current assets.")
        elif current_ratio < 1.5:
            warnings.append("Current ratio is relatively low; compare with industry norms.")
        else:
            warnings.append("Current assets cover current liabilities based on the supplied figures.")
    if working_capital is not None and working_capital < 0:
        warnings.append("Negative working capital: review short-term liquidity.")
    return page("""<section><h2>{{p.company_name}} — {{p.fiscal_year}}</h2>
    <p class="muted">Unit: {{p.unit}} · Scope: {{p.statement_scope or 'CONSOLIDATED'}} · Source: {{p.source_filename or 'Not recorded'}}</p>
    <div class="grid">
    <div class="card"><div class="muted">Current ratio</div><div class="num">{{'%.2f'|format(cr) if cr is not none else 'N/A'}}</div></div>
    <div class="card"><div class="muted">Quick ratio</div><div class="num">{{'%.2f'|format(qr) if qr is not none else 'N/A'}}</div></div>
    <div class="card"><div class="muted">Working capital</div><div class="num">{{'%.2f'|format(wc) if wc is not none else 'N/A'}}</div></div>
    <div class="card"><div class="muted">Net profit margin</div><div class="num">{{('%.2f%%'|format(margin)) if margin is not none else 'N/A'}}</div></div>
    <div class="card"><div class="muted">Debt-to-equity</div><div class="num">{{'%.2f'|format(de) if de is not none else 'N/A'}}</div></div></div>
    <h3>Saved financial figures and provenance</h3>
    <table><tr><th>Item</th><th>Value</th><th>Source label</th><th>Page</th><th>Confidence</th><th>Status</th></tr>
    {% for r in rows %}<tr><td>{{labels.get(r.item_code,r.item_code)}}</td><td>{{'%.2f'|format(r.item_value)}}</td><td>{{r.source_label or 'Manual entry'}}</td><td>{{r.source_page or '—'}}</td><td>{{('%d%%'|format(r.extraction_confidence*100)) if r.extraction_confidence is not none else '—'}}</td><td>{{r.validation_status}}</td></tr>{% endfor %}</table></section>
    <section><h2>Rule-based observations</h2>{% for w in warnings %}<p>• {{w}}</p>{% else %}<p>Enter current assets and current liabilities to generate liquidity observations.</p>{% endfor %}
    <p class="muted">These are simple indicators, not investment advice. Compare multiple years and industry peers before drawing conclusions.</p>
    <a class="btn" href="/company-analysis">Back to company analysis</a></section>
    """, p=p, cr=current_ratio, qr=quick_ratio, wc=working_capital, margin=net_margin, de=debt_equity,
        rows=value_rows, labels=ALLOWED_FINANCIAL_ITEMS, warnings=warnings)



if __name__=="__main__":
    initialize()
    print("Open http://127.0.0.1:5000")
    app.run(debug=True)
