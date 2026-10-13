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
<nav><a class="btn" href="/">Dashboard</a><a class="btn" href="/risks">Risk Register</a><a class="btn" href="/risks/new">Add Risk</a><a class="btn" href="/controls">Controls</a><a class="btn" href="/audit">Audit Log</a></nav>
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

if __name__=="__main__":
    initialize()
    print("Open http://127.0.0.1:5000")
    app.run(debug=True)
