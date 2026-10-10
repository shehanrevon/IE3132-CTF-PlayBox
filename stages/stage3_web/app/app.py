"""
Stage 3 - Web Security (IDOR): Meridian Freight "Ledger Portal"
Owner: Palugaswewa K I K I B

Deliberately vulnerable: /statement/<id>, /api/statements/<id> and /files/<id> check that the
visitor is LOGGED IN but never check that the record BELONGS to them (Broken Object Level
Authorization / IDOR).  Everything else is hardened on purpose so the IDOR is the ONLY way in
(Requirement 7): no database (no SQLi), debug off, no source/flag in any response except the
intended file, random passwords for every account except the one players earn in Stage 2.

State is in memory only -> restarting the container is a full reset.
"""
import os
import secrets
import sys
from functools import wraps

from flask import (Flask, abort, jsonify, redirect, render_template, request,
                   session, url_for, Response)
from werkzeug.security import check_password_hash, generate_password_hash

FLAG = os.environ.get("STAGE3_FLAG")
SECRET_KEY = os.environ.get("SECRET_KEY")
if not FLAG or not SECRET_KEY:
    sys.exit("STAGE3_FLAG and SECRET_KEY must be set (see docker-compose.stage3.yml)")

app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY, SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE="Lax", JSON_SORT_KEYS=False)

# ----------------------------------------------------------------------------- DATA
# Stage 2 leaks exactly one credential: dwijesekara / Ledger#2291
# Every other account gets a random password at startup (nobody is meant to log in as them).
USERS = {
    1: dict(username="dwijesekara", name="Dilani Wijesekara", dept="Finance & Audit", staff_id="MFC2291",
            pw=generate_password_hash("Ledger#2291")),
    2: dict(username="igunawardena", name="Ishara Gunawardena", dept="Customs & Compliance", staff_id="MFC2754"),
    3: dict(username="njayasinghe", name="Nuwan Jayasinghe", dept="Operations", staff_id="MFC1042"),
    4: dict(username="dwickramasinghe", name="Dilan Wickramasinghe", dept="Finance & Audit", staff_id="MFC3350"),
    5: dict(username="mkarunaratne", name="Mahesh Karunaratne", dept="IT Support", staff_id="MFC1986"),
}
for u in USERS.values():
    u.setdefault("pw", generate_password_hash(secrets.token_urlsafe(24)))
BY_NAME = {u["username"]: uid for uid, u in USERS.items()}

STATEMENTS = {
    5003: dict(owner=3, title="Dispatch cost summary", period="Q1 2026", files=[9102],
               note="Fuel surcharges came in 3% under forecast. No exceptions.",
               lines=[("Fuel surcharge", "1,204,300.00"), ("Driver overtime", "388,120.00"), ("Port fees", "902,450.00")]),
    5009: dict(owner=4, title="Q1 payables ledger", period="Q1 2026", files=[],
               note="All supplier invoices matched to POs except the three queried by D. Wijesekara.",
               lines=[("Supplier invoices", "6,481,900.00"), ("Credit notes", "-212,000.00")]),
    5017: dict(owner=1, title="Q1 freight reconciliation", period="Q1 2026", files=[9101],
               note=("Three Q1 invoices name a consignee with no customs record, all just under the review "
                     "threshold. I raised this with Compliance on 11 March. Their follow-up is recorded "
                     "in statement 5042."),
               lines=[("Freight invoices", "9,730,400.00"), ("Matched", "9,231,900.00"), ("Unmatched", "498,500.00")]),
    5024: dict(owner=5, title="Software licence costs", period="Q1 2026", files=[],
               note="Renewals complete. Forum hosting moved to the intranet mirror.",
               lines=[("Licences", "214,000.00"), ("Support contracts", "96,500.00")]),
    5042: dict(owner=2, title="Customs hold review", period="Q1 2026", files=[9103],
               note=("Held the three flagged invoices pending a beneficiary check. Evidence pack "
                     "(shadow_batch_Q1.csv) attached and forwarded to the Audit Director."),
               lines=[("Invoices held", "3"), ("Value held", "498,500.00")]),
    5050: dict(owner=2, title="Compliance training budget", period="FY 2026", files=[9104],
               note="Customs awareness workshop approved for all hubs.",
               lines=[("Workshops", "180,000.00"), ("Materials", "24,000.00")]),
}

FILES = {
    9101: ("q1_reconciliation.csv", "text/csv",
           "invoice,consignee,amount,status\nINV-Q1-0412,Halcyon Trade Ltd,166200.00,UNMATCHED\n"
           "INV-Q1-0419,Halcyon Trade Ltd,166150.00,UNMATCHED\nINV-Q1-0431,Halcyon Trade Ltd,166150.00,UNMATCHED\n"),
    9102: ("dispatch_costs_q1.csv", "text/csv", "item,amount\nfuel,1204300.00\novertime,388120.00\nport_fees,902450.00\n"),
    9103: ("shadow_batch_Q1.csv", "text/csv",
           "batch,consignee,amount,status\nSB-Q1-01,Halcyon Trade Ltd,166200.00,HELD\n"
           "SB-Q1-02,Halcyon Trade Ltd,166150.00,HELD\nSB-Q1-03,Halcyon Trade Ltd,166150.00,HELD\n"
           f"audit_ref,{FLAG},,\n"),
    9104: ("training_budget.csv", "text/csv", "item,amount\nworkshops,180000.00\nmaterials,24000.00\n"),
}

# ----------------------------------------------------------------------------- HELPERS
def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if "uid" not in session:
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapper


def current_user():
    return USERS[session["uid"]]


def view(sid):
    s = STATEMENTS.get(sid)
    if not s:
        abort(404)
    return s


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ----------------------------------------------------------------------------- ROUTES
@app.route("/")
def index():
    return redirect(url_for("dashboard" if "uid" in session else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        uid = BY_NAME.get(request.form.get("username", "").strip().lower())
        if uid and check_password_hash(USERS[uid]["pw"], request.form.get("password", "")):
            session.clear()
            session["uid"] = uid
            return redirect(url_for("dashboard"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["uid"]
    mine = [(sid, s) for sid, s in sorted(STATEMENTS.items()) if s["owner"] == uid]
    return render_template("dashboard.html", user=current_user(), statements=mine)


@app.route("/statement/<int:sid>")
@login_required
def statement(sid):
    s = view(sid)                      # VULNERABLE: never checks s["owner"] == session["uid"]
    return render_template("statement.html", user=current_user(), sid=sid, s=s, owner=USERS[s["owner"]],
                           files=[(f, FILES[f][0]) for f in s["files"]])


@app.route("/api/statements/<int:sid>")
@login_required
def api_statement(sid):
    s = view(sid)                      # VULNERABLE (same flaw, JSON flavour)
    return jsonify(id=sid, title=s["title"], period=s["period"], owner=USERS[s["owner"]]["name"],
                   department=USERS[s["owner"]]["dept"], note=s["note"], attachments=s["files"])


@app.route("/files/<int:fid>")
@login_required
def download(fid):
    f = FILES.get(fid)                 # VULNERABLE: no ownership check on attachments either
    if not f:
        abort(404)
    name, mime, body = f
    return Response(body, mimetype=mime, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.route("/healthz")
def healthz():
    return "ok"


@app.errorhandler(404)
def nf(_):
    return render_template("error.html", msg="Not found."), 404


@app.errorhandler(500)
def err(_):
    return render_template("error.html", msg="Something went wrong."), 500


if __name__ == "__main__":     # local dev only; the container uses gunicorn. debug stays OFF.
    app.run(host="127.0.0.1", port=5000, debug=False)
