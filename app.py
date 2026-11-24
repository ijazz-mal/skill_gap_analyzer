import sqlite3
import json
from flask import Flask, render_template, request, redirect, session, abort
from gap import compute_gaps, load_roles
from db import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-key")
init_db()
READY_THRESHOLD = 85

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")
    roles = load_roles()
    error = None
    if request.method == "POST":
        role = request.form["role"]
        my_skills = request.form.getlist("skills")
        degree = request.form["degree"].strip()
        institution = request.form["institution"].strip()
        interests = request.form["interests"].strip()
        try:
            year = int(request.form["graduation_year"])
        except ValueError:
            year = None
        if not degree or not institution:
            error = "Please enter your degree and institution."
        elif year is None or not 1990 <= year <= 2035:
            error = "Enter a valid graduation year."
        else:
            conn = get_db()
            conn.execute(
                """INSERT INTO profiles
                       (user_id, degree, institution, graduation_year, interests, target_role, skills)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       degree = excluded.degree,
                       institution = excluded.institution,
                       graduation_year = excluded.graduation_year,
                       interests = excluded.interests,
                       target_role = excluded.target_role,
                       skills = excluded.skills""",
                (session["user_id"], degree, institution, year, interests, role, json.dumps(my_skills)),
            )
            conn.commit()
            conn.close()
            return redirect("/report")

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()
    saved = dict(row) if row else {}
    saved_skills = json.loads(row["skills"]) if row else []
    skill_roles = {}
    
    for role_name, items in roles.items():
        for s in items:
            skill_roles.setdefault(s["skill"], []).append(role_name)
    all_skills = sorted(skill_roles)

    return render_template(
        "profile.html",
        roles=roles,
        all_skills=all_skills,
        saved=saved,
        saved_skills=saved_skills,
        error=error,
    )

@app.route("/report")
def report():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()
    if row is None or row["target_role"] not in load_roles():
        return redirect("/profile")
    gaps = compute_gaps(row["target_role"], json.loads(row["skills"]))
    return render_template("report.html", role=row["target_role"], gaps=gaps)

@app.route("/register", methods=["GET","POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            conn = get_db()
            try:
                cur = conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                conn.commit()
                session["user_id"] = cur.lastrowid
                return redirect("/profile")
            except sqlite3.IntegrityError:
                error = "That email is already registered."
            finally:
                conn.close()
    return render_template("register.html", error=error)

@app.route("/login", methods = ["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect("/roadmap")
        error = "Wrong email or password."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

def readiness(conn, user_id):
    row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    roles = load_roles()
    if row["target_role"] not in roles:
        return None
    gaps = compute_gaps(row["target_role"], json.loads(row["skills"]))
    done = {
        r["skill"]
        for r in conn.execute("SELECT skill FROM progress WHERE user_id = ?", (user_id,))
    }
    total = len(roles[row["target_role"]])
    completed = sum(1 for g in gaps if g["skill"] in done)
    score = round(100 * (total - len(gaps) + completed) / total) if total else 0
    return row, gaps, done, score


@app.route("/roadmap")
def roadmap():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    data = readiness(conn, session["user_id"])
    if data is None:
        conn.close()
        return redirect("/profile")
    row, gaps, done, score = data
    ready = score >= READY_THRESHOLD
    partners, shared = [], set()
    if ready:
        partners = conn.execute(
            """SELECT p.* FROM partners p
               JOIN partner_roles pr ON pr.partner_id = p.id
               JOIN roles r ON r.id = pr.role_id
               WHERE r.name = ? ORDER BY p.name""",
            (row["target_role"],),
        ).fetchall()
        shared = {
            r["partner_id"]
            for r in conn.execute(
                "SELECT partner_id FROM referrals WHERE user_id = ?", (session["user_id"],)
            )
        }
    conn.close()
    return render_template(
        "roadmap.html",
        role=row["target_role"], gaps=gaps, done=done, score=score,
        ready=ready, threshold=READY_THRESHOLD, partners=partners, shared=shared,
    )

@app.route("/toggle", methods=["POST"])
def toggle():
    if "user_id" not in session:
        return redirect("/login")
    skill = request.form["skill"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_db()
    exists = conn.execute(
        "SELECT 1 FROM progress WHERE user_id = ? AND skill = ?",
        (session["user_id"], skill),
    ).fetchone()
    if exists:
        conn.execute(
            "DELETE FROM progress WHERE user_id = ? AND skill = ?",
            (session["user_id"], skill),
        )
        action = "undone"
    else:
        conn.execute(
            "INSERT INTO progress (user_id, skill, completed_at) VALUES (?, ?, ?)",
            (session["user_id"], skill, now),
        )
        action = "done"
    conn.execute(
        "INSERT INTO progress_log (user_id, skill, action, created_at) VALUES (?, ?, ?, ?)",
        (session["user_id"], skill, action, now),
    )
    conn.commit()
    conn.close()
    return redirect("/roadmap")

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        conn = get_db()
        u = conn.execute(
            "SELECT is_admin FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        conn.close()
        if not u or not u["is_admin"]:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@app.route("/admin")
@admin_required
def admin():
    conn = get_db()
    rows = conn.execute(
        """SELECT r.id AS role_id, r.name AS role, s.id AS skill_id,
                  s.name AS skill, rs.demand
           FROM role_skills rs
           JOIN roles r ON r.id = rs.role_id
           JOIN skills s ON s.id = rs.skill_id
           ORDER BY r.name, rs.demand DESC"""
    ).fetchall()
    roles = conn.execute("SELECT * FROM roles ORDER BY name").fetchall()
    skills = conn.execute("SELECT * FROM skills ORDER BY name").fetchall()
    resources = conn.execute(
        """SELECT res.id, res.title, res.url, res.cost, s.name AS skill
           FROM resources res JOIN skills s ON s.id = res.skill_id
           ORDER BY s.name, res.cost"""
    ).fetchall()
    partners = conn.execute(
        """SELECT p.id, p.name, p.website, GROUP_CONCAT(r.name, ', ') AS roles
           FROM partners p
           LEFT JOIN partner_roles pr ON pr.partner_id = p.id
           LEFT JOIN roles r ON r.id = pr.role_id
           GROUP BY p.id ORDER BY p.name"""
    ).fetchall()
    referrals = conn.execute(
        """SELECT ref.created_at, p.name AS partner, u.name, u.email,
                  pf.degree, pf.institution
           FROM referrals ref
           JOIN partners p ON p.id = ref.partner_id
           JOIN users u ON u.id = ref.user_id
           LEFT JOIN profiles pf ON pf.user_id = u.id
           ORDER BY ref.created_at DESC"""
    ).fetchall()
    events = conn.execute(
        """SELECT l.created_at, u.name, u.email, l.skill, l.action
           FROM progress_log l JOIN users u ON u.id = l.user_id
           ORDER BY l.created_at DESC LIMIT 100"""
    ).fetchall()
    closers = conn.execute(
        """SELECT COUNT(*) FROM
           (SELECT user_id FROM progress GROUP BY user_id HAVING COUNT(*) >= 3)"""
    ).fetchone()[0] 
    conn.close()
    return render_template(
        "admin.html",
        rows=rows,
        roles=roles,
        skills=skills,
        resources=resources,
        partners=partners,
        referrals=referrals,
        events=events,
        closers=closers
    )


@app.route("/admin/role", methods=["POST"])
@admin_required
def admin_add_role():
    name = request.form["name"].strip()
    if name:
        conn = get_db()
        conn.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
    return redirect("/admin")


@app.route("/admin/skill", methods=["POST"])
@admin_required
def admin_save_skill():
    name = request.form["skill"].strip()
    try:
        demand = int(request.form["demand"])
    except ValueError:
        return redirect("/admin")
    if name and 0 <= demand <= 100:
        conn = get_db()
        conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (name,))
        skill_id = conn.execute(
            "SELECT id FROM skills WHERE name = ?", (name,)
        ).fetchone()["id"]
        conn.execute(
            """INSERT INTO role_skills (role_id, skill_id, demand) VALUES (?, ?, ?)
               ON CONFLICT(role_id, skill_id) DO UPDATE SET demand = excluded.demand""",
            (request.form["role_id"], skill_id, demand),
        )
        conn.commit()
        conn.close()
    return redirect("/admin")


@app.route("/admin/skill/delete", methods=["POST"])
@admin_required
def admin_delete_skill():
    conn = get_db()
    conn.execute(
        "DELETE FROM role_skills WHERE role_id = ? AND skill_id = ?",
        (request.form["role_id"], request.form["skill_id"]),
    )
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/admin/resource", methods=["POST"])
@admin_required
def admin_add_resource():
    title = request.form["title"].strip()
    url = request.form["url"].strip()
    cost = request.form["cost"]
    if title and url.startswith(("http://", "https://")) and cost in ("free", "paid"):
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO resources (skill_id, title, url, cost) VALUES (?, ?, ?, ?)",
            (request.form["skill_id"], title, url, cost),
        )
        conn.commit()
        conn.close()
    return redirect("/admin")


@app.route("/admin/resource/delete", methods=["POST"])
@admin_required
def admin_delete_resource():
    conn = get_db()
    conn.execute("DELETE FROM resources WHERE id = ?", (request.form["id"],))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/share", methods=["POST"])
def share():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    data = readiness(conn, session["user_id"])
    if data is None or data[3] < READY_THRESHOLD:
        conn.close()
        abort(403)
    partner_id = request.form["partner_id"]
    matches = conn.execute(
        """SELECT 1 FROM partner_roles pr JOIN roles r ON r.id = pr.role_id
           WHERE pr.partner_id = ? AND r.name = ?""",
        (partner_id, data[0]["target_role"]),
    ).fetchone()
    if matches:
        conn.execute(
            "INSERT OR IGNORE INTO referrals (user_id, partner_id, created_at) VALUES (?, ?, ?)",
            (session["user_id"], partner_id,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.commit()
    conn.close()
    return redirect("/roadmap")


@app.route("/unshare", methods=["POST"])
def unshare():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    conn.execute(
        "DELETE FROM referrals WHERE user_id = ? AND partner_id = ?",
        (session["user_id"], request.form["partner_id"]),
    )
    conn.commit()
    conn.close()
    return redirect("/roadmap")


@app.route("/admin/partner", methods=["POST"])
@admin_required
def admin_add_partner():
    name = request.form["name"].strip()
    website = request.form["website"].strip()
    if not website.startswith(("http://", "https://")):
        website = ""
    if name:
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO partners (name, website, description) VALUES (?, ?, ?)",
            (name, website, request.form["description"].strip()),
        )
        pid = conn.execute("SELECT id FROM partners WHERE name = ?", (name,)).fetchone()["id"]
        conn.execute(
            "INSERT OR IGNORE INTO partner_roles (partner_id, role_id) VALUES (?, ?)",
            (pid, request.form["role_id"]),
        )
        conn.commit()
        conn.close()
    return redirect("/admin")


@app.route("/admin/partner/delete", methods=["POST"])
@admin_required
def admin_delete_partner():
    pid = request.form["id"]
    conn = get_db()
    conn.execute("DELETE FROM referrals WHERE partner_id = ?", (pid,))
    conn.execute("DELETE FROM partner_roles WHERE partner_id = ?", (pid,))
    conn.execute("DELETE FROM partners WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return redirect("/admin")

if __name__ == "__main__":
    app.run(debug=True)