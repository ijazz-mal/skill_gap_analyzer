import sqlite3
import json
from flask import Flask, render_template, request, redirect, session
from gap import compute_gaps, load_roles
from db import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
init_db()
app.secret_key = "change-this-to-a-long-random-string"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")
    roles = load_roles()
    if request.method == "POST":
        role = request.form["role"]
        my_skills = request.form.getlist("skills")
        conn = get_db()
        conn.execute(
            """INSERT INTO profiles (user_id, target_role, skills)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    target_role = excluded.target_role,
                    skills = excluded.skills""",
            (session["user_id"], role, json.dumps(my_skills)),
        )
        conn.commit()
        conn.close()
        return redirect("/roadmap")
    all_skills = sorted({s["skill"] for r in roles.values() for s in r})
    return render_template("profile.html", roles=roles, all_skills=all_skills)

@app.route("/report")
def report():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    if row is None:
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

@app.route("/roadmap")
def roadmap():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    if row is None:
        conn.close()
        return redirect("/profile")
    gaps = compute_gaps(row["target_role"], json.loads(row["skills"]))
    done = {
        r["skill"]
        for r in conn.execute(
            "SELECT skill FROM progress WHERE user_id = ?", (session["user_id"],)
        )
    }
    conn.close()
    total = len(load_roles()[row["target_role"]])
    completed = sum(1 for g in gaps if g["skill"] in done)
    score = round(100 * (total - len(gaps) + completed) / total)
    return render_template(
        "roadmap.html", role=row["target_role"], gaps=gaps, done=done, score=score
    )

@app.route("/toggle", methods=["POST"])
def toggle():
    if "user_id" not in session:
        return redirect("/login")
    skill = request.form["skill"]
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
    else:
        conn.execute(
            "INSERT INTO progress (user_id, skill) VALUES (?, ?)",
            (session["user_id"], skill),
        )
    conn.commit()
    conn.close()
    return redirect("/roadmap")

if __name__ == "__main__":
    app.run(debug=True)