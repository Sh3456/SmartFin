from contextlib import contextmanager
from pathlib import Path
import sqlite3
from flask import Flask, flash, redirect, render_template_string, request, url_for

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "corporate_risk.db"
app = Flask(__name__)
app.secret_key = "development-key-change-before-deployment"

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

def seed():
    with db() as con:
        con.executescript((ROOT / "seed.sql").read_text(encoding="utf-8"))

def query(sql, args=()):
    with db() as con:
        return con.execute(sql, args).fetchall()

def band(score):
    return "Critical" if score >= 17 else "High" if score >= 10 else "Moderate" if score >= 5 else "Low"

BASE = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Corporate Risk Manager</title><style>
body{font:15px Arial;margin:0;background:#f3f6fb;color:#1c2940}header{background:#172944;color:white;padding:22px calc((100% - 1100px)/2);padding-left:max(20px,calc((100% - 1100px)/2));padding-right:20px}
main{max-width:1100px;margin:24px auto;padding:0 16px}nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}
a.btn,button{display:inline-block;background:#2459a9;color:white;padding:10px 13px;border:0;border-radius:6px;text-decoration:none;cursor:pointer}
section,.card{background:white;border:1px solid #e0e7f0;border-radius:9px;padding:16px;margin:14px 0;overflow:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.num{font-size:27px;font-weight:bold;margin-top:8px}
table{width:100%;border-collapse:collapse}td,th{text-align:left;border-bottom:1px solid #e8edf4;padding:10px 7px}th{font-size:12px;color:#65738a;text-transform:uppercase}
input,select,textarea{width:100%;padding:9px;border:1px solid #bdc8d8;border-radius:5px;margin:5px 0 12px;box-sizing:border-box}
label{font-weight:bold;font-size:13px}.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
.badge{border-radius:12px;padding:4px 8px;background:#e2e8f0}.Critical{background:#fee2e2;color:#991b1b}.High{background:#ffedd5;color:#9a3412}.Moderate{background:#fef3c7;color:#92400e}.Low{background:#dcfce7;color:#166534}
.flash{background:#dcfce7;padding:12px;border-radius:6px;margin:10px 0}.muted{color:#64748b;font-size:13px}
</style></head><body><header><h1>Corporate Risk Manager</h1><div>Risk register • Mitigation tracking • Audit history</div></header><main>
<nav><a class="btn" href="/">Dashboard</a><a class="btn" href="/risks">Risk Register</a><a class="btn" href="/risks/new">Add Risk</a><a class="btn" href="/controls">Controls</a><a class="btn" href="/audit">Audit Log</a><a class="btn" href="/company-analysis">Company Analysis</a></nav>
{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}</main></body></html>
"""
def page(body, **ctx):
    return render_template_string(BASE, body=render_template_string(body, **ctx))

@app.get("/")
def home():
    counts=query("""SELECT COUNT(*) total,
      SUM(CASE WHEN status!='Closed' THEN 1 ELSE 0 END) active,
      SUM(CASE WHEN status!='Closed' AND risk_score>=17 THEN 1 ELSE 0 END) critical FROM risks""")[0]
    controls=query("SELECT COUNT(*) total,SUM(status='Completed') done FROM mitigation_controls")[0]
    depts=query("SELECT * FROM v_department_risk_exposure ORDER BY total_risk_exposure DESC")
    top=query("""SELECT r.*,d.department_name FROM risks r JOIN departments d USING(department_id)
      WHERE status!='Closed' ORDER BY risk_score DESC LIMIT 5""")
    return page("""<div class="grid">
    <div class="card"><div class="muted">All risks</div><div class="num">{{c.total or 0}}</div></div>
    <div class="card"><div class="muted">Active risks</div><div class="num">{{c.active or 0}}</div></div>
    <div class="card"><div class="muted">Critical active</div><div class="num">{{c.critical or 0}}</div></div>
    <div class="card"><div class="muted">Controls completed</div><div class="num">{{k.done or 0}} / {{k.total or 0}}</div></div></div>
    <section><h2>Department exposure</h2><table><tr><th>Department</th><th>Risks</th><th>Total exposure</th><th>Critical</th></tr>
    {% for d in depts %}<tr><td>{{d.department_name}}</td><td>{{d.risk_count}}</td><td>{{d.total_risk_exposure}}</td><td>{{d.critical_risks or 0}}</td></tr>{% endfor %}</table></section>
    <section><h2>Top risks</h2><table><tr><th>Risk</th><th>Department</th><th>Score</th><th>Rating</th><th>Status</th></tr>
    {% for r in top %}<tr><td><a href="/risks/{{r.risk_id}}">{{r.title}}</a></td><td>{{r.department_name}}</td><td>{{r.risk_score}}</td><td><span class="badge {{band(r.risk_score)}}">{{band(r.risk_score)}}</span></td><td>{{r.status}}</td></tr>{% else %}<tr><td colspan="5">No risks. Load demo data or add a risk.</td></tr>{% endfor %}</table></section>""",c=counts,k=controls,depts=depts,top=top,band=band)

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
import re
from pypdf import PdfReader
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

def extract_pdf_text(path):
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)

def _number_from_line(line):
    # Supports Indian comma grouping and parentheses for negative values.
    match = re.search(r"\(?-?\d[\d,]*(?:\.\d+)?\)?", line)
    if not match:
        return None
    raw = match.group(0).replace(",", "")
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    try:
        return float(raw)
    except ValueError:
        return None

def extract_financial_items(text):
    # Candidate extraction is intentionally conservative and always requires review.
    patterns = {
        "CURRENT_ASSETS": [r"total current assets", r"current assets"],
        "CURRENT_LIABILITIES": [r"total current liabilities", r"current liabilities"],
        "INVENTORY": [r"inventories", r"inventory"],
        "REVENUE": [r"revenue from operations", r"total revenue", r"revenue"],
        "NET_PROFIT": [r"profit for the year", r"net profit", r"profit after tax"],
        "TOTAL_DEBT": [r"total borrowings", r"total debt", r"borrowings"],
        "EQUITY": [r"total equity", r"equity attributable", r"total shareholders.? equity"],
        "OPERATING_CASH_FLOW": [r"net cash from operating activities", r"net cash generated from operating activities", r"cash flow from operating activities"],
    }
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    found = {}
    for code, aliases in patterns.items():
        for line in lines:
            lower = line.lower()
            if any(re.search(r"\b" + alias + r"\b", lower) for alias in aliases):
                value = _number_from_line(line)
                if value is not None and value >= 0:
                    found[code] = value
                    break
    return found

@app.route("/company-analysis", methods=["GET", "POST"])
def company_analysis():
    if request.method == "POST":
        uploaded = request.files.get("report")
        company_name = request.form.get("company_name", "").strip()
        fiscal_year = request.form.get("fiscal_year", "").strip()
        if not company_name or not fiscal_year:
            flash("Enter a company name and financial year.")
            return redirect(url_for("company_analysis"))
        if not uploaded or not uploaded.filename.lower().endswith(".pdf"):
            flash("Please upload an annual report PDF.")
            return redirect(url_for("company_analysis"))
        try:
            safe_name = secure_filename(uploaded.filename)
            if not safe_name:
                raise ValueError("Invalid filename")
            stored_name = f"{__import__('uuid').uuid4().hex}_{safe_name}"
            file_path = UPLOAD_DIR / stored_name
            uploaded.save(file_path)
            text = extract_pdf_text(file_path)
            values = extract_financial_items(text)
            if not values:
                file_path.unlink(missing_ok=True)
                flash("No supported figures could be extracted. This PDF may be scanned or use a different layout.")
                return redirect(url_for("company_analysis"))
            return page("""
            <section><h2>Review extracted figures</h2>
            <p>Company: <b>{{company}}</b> | Financial year: <b>{{year}}</b></p>
            <p class="muted">PDF text extraction can select the wrong number or reporting column. Verify each figure against the report before saving. Values should use the same unit, preferably INR crore.</p>
            <form method="post" action="/company-analysis/save">
            <input type="hidden" name="company_name" value="{{company}}">
            <input type="hidden" name="fiscal_year" value="{{year}}">
            <input type="hidden" name="source_filename" value="{{filename}}">
            <div class="cols">{% for code,label in items %}<div><label>{{label}}{% if code in values %} (extracted){% endif %}</label>
            <input type="number" step="0.01" min="0" name="{{code}}" value="{{values.get(code, '')}}" placeholder="Verify and enter value"></div>{% endfor %}</div>
            <label>Unit</label><select name="unit"><option value="INR crore">INR crore</option><option value="INR lakh">INR lakh</option><option value="INR">INR</option></select>
            <button>Validate and save figures</button></form></section>
            """, company=company_name, year=fiscal_year, filename=stored_name, items=list(ALLOWED_FINANCIAL_ITEMS.items()), values=values)
        except Exception as exc:
            flash("Could not read this PDF. Try a text-based PDF and check that it is not password-protected.")
            return redirect(url_for("company_analysis"))
    companies = query("""SELECT c.company_name, p.fiscal_year, p.period_id, p.unit,
        COUNT(v.item_code) AS item_count FROM financial_periods p
        JOIN companies c USING(company_id) LEFT JOIN financial_values v USING(period_id)
        GROUP BY p.period_id ORDER BY c.company_name, p.fiscal_year DESC""")
    return page("""
    <section><h2>Company Financial Analysis</h2>
    <p>Upload an annual report PDF. SmartFin will suggest a few financial figures for you to verify before they are saved.</p>
    <form method="post" enctype="multipart/form-data">
    <label>Company name</label><input name="company_name" required placeholder="e.g. Tata Consultancy Services">
    <label>Financial year</label><input name="fiscal_year" required placeholder="e.g. FY2026">
    <label>Annual report PDF</label><input type="file" name="report" accept=".pdf,application/pdf" required>
    <button>Upload and extract figures</button></form></section>
    <section><h2>Saved company periods</h2><table><tr><th>Company</th><th>Year</th><th>Unit</th><th>Figures saved</th><th>Report</th></tr>
    {% for p in periods %}<tr><td>{{p.company_name}}</td><td>{{p.fiscal_year}}</td><td>{{p.unit}}</td><td>{{p.item_count}}</td><td><a href="/company-analysis/{{p.period_id}}">Analyze</a></td></tr>
    {% else %}<tr><td colspan="5">No company financial data saved yet.</td></tr>{% endfor %}</table></section>
    """, periods=companies)

@app.post("/company-analysis/save")
def save_company_financials():
    company = request.form.get("company_name", "").strip()
    year = request.form.get("fiscal_year", "").strip()
    unit = request.form.get("unit", "INR crore")
    filename = request.form.get("source_filename", "").strip()
    if not company or not year:
        flash("Company and financial year are required.")
        return redirect(url_for("company_analysis"))
    values = {}
    try:
        for code in ALLOWED_FINANCIAL_ITEMS:
            raw = request.form.get(code, "").strip()
            if raw:
                number = float(raw)
                if number < 0:
                    raise ValueError("Negative values need separate review.")
                values[code] = number
        if not values:
            raise ValueError("At least one financial figure is required.")
        if "CURRENT_ASSETS" in values and "CURRENT_LIABILITIES" in values and values["CURRENT_LIABILITIES"] == 0:
            raise ValueError("Current liabilities must be greater than zero.")
        with db() as con:
            con.execute("INSERT INTO companies(company_name) VALUES(?) ON CONFLICT(company_name) DO NOTHING", (company,))
            company_id = con.execute("SELECT company_id FROM companies WHERE company_name=?", (company,)).fetchone()[0]
            con.execute("""INSERT INTO financial_periods(company_id,fiscal_year,unit,source_filename)
                VALUES(?,?,?,?) ON CONFLICT(company_id,fiscal_year) DO UPDATE SET unit=excluded.unit,source_filename=excluded.source_filename""",
                (company_id, year, unit, filename))
            period_id = con.execute("SELECT period_id FROM financial_periods WHERE company_id=? AND fiscal_year=?", (company_id, year)).fetchone()[0]
            for code, value in values.items():
                con.execute("""INSERT INTO financial_values(period_id,item_code,item_value) VALUES(?,?,?)
                    ON CONFLICT(period_id,item_code) DO UPDATE SET item_value=excluded.item_value""", (period_id, code, value))
        flash("Verified financial figures saved.")
        return redirect(url_for("company_analysis_detail", period_id=period_id))
    except (ValueError, sqlite3.IntegrityError):
        flash("Please enter valid non-negative figures and ensure current liabilities are not zero.")
        return redirect(url_for("company_analysis"))

@app.get("/company-analysis/<int:period_id>")
def company_analysis_detail(period_id):
    periods = query("""SELECT p.*,c.company_name FROM financial_periods p JOIN companies c USING(company_id)
        WHERE p.period_id=?""", (period_id,))
    if not periods:
        return "Financial period not found", 404
    p = periods[0]
    data = {r["item_code"]: r["item_value"] for r in query("SELECT item_code,item_value FROM financial_values WHERE period_id=?", (period_id,))}
    current_ratio = data.get("CURRENT_ASSETS") / data.get("CURRENT_LIABILITIES") if data.get("CURRENT_ASSETS") is not None and data.get("CURRENT_LIABILITIES") else None
    quick_ratio = (data["CURRENT_ASSETS"] - data.get("INVENTORY", 0)) / data["CURRENT_LIABILITIES"] if data.get("CURRENT_ASSETS") is not None and data.get("CURRENT_LIABILITIES") else None
    working_capital = data["CURRENT_ASSETS"] - data["CURRENT_LIABILITIES"] if data.get("CURRENT_ASSETS") is not None and data.get("CURRENT_LIABILITIES") is not None else None
    net_margin = data["NET_PROFIT"] / data["REVENUE"] * 100 if data.get("NET_PROFIT") is not None and data.get("REVENUE") else None
    debt_equity = data["TOTAL_DEBT"] / data["EQUITY"] if data.get("TOTAL_DEBT") is not None and data.get("EQUITY") else None
    warnings = []
    if current_ratio is not None:
        if current_ratio < 1: warnings.append("Current ratio below 1: current liabilities exceed current assets.")
        elif current_ratio < 1.5: warnings.append("Current ratio is relatively low; compare with industry norms.")
        else: warnings.append("Current assets cover current liabilities based on the supplied figures.")
    if working_capital is not None and working_capital < 0:
        warnings.append("Negative working capital: review short-term liquidity.")
    return page("""
    <section><h2>{{p.company_name}} — {{p.fiscal_year}}</h2><p class="muted">Unit: {{p.unit}}. Ratios depend on the accuracy and comparability of the uploaded figures.</p>
    <div class="grid">
    <div class="card"><div class="muted">Current ratio</div><div class="num">{{'%.2f'|format(cr) if cr is not none else 'N/A'}}</div></div>
    <div class="card"><div class="muted">Quick ratio</div><div class="num">{{'%.2f'|format(qr) if qr is not none else 'N/A'}}</div></div>
    <div class="card"><div class="muted">Working capital</div><div class="num">{{'%.2f'|format(wc) if wc is not none else 'N/A'}}</div></div>
    <div class="card"><div class="muted">Net profit margin</div><div class="num">{{('%.2f%%'|format(margin)) if margin is not none else 'N/A'}}</div></div>
    <div class="card"><div class="muted">Debt-to-equity</div><div class="num">{{'%.2f'|format(de) if de is not none else 'N/A'}}</div></div></div>
    <h3>Saved financial figures</h3><table><tr><th>Item</th><th>Value</th><th>Unit</th></tr>
    {% for code,label in items %}{% if code in values %}<tr><td>{{label}}</td><td>{{'%.2f'|format(values[code])}}</td><td>{{p.unit}}</td></tr>{% endif %}{% endfor %}</table></section>
    <section><h2>Rule-based observations</h2>{% for w in warnings %}<p>• {{w}}</p>{% else %}<p>Enter current assets and current liabilities to generate liquidity observations.</p>{% endfor %}
    <p class="muted">These are simple indicators, not investment advice. Compare multiple years and industry peers before drawing conclusions.</p>
    <a class="btn" href="/company-analysis">Back to company analysis</a></section>
    """, p=p, cr=current_ratio, qr=quick_ratio, wc=working_capital, margin=net_margin, de=debt_equity, values=data, items=list(ALLOWED_FINANCIAL_ITEMS.items()), warnings=warnings)


if __name__=="__main__":
    initialize()
    print("Open http://127.0.0.1:5000")
    app.run(debug=True)
