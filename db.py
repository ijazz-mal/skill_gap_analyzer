import sqlite3
import json
import os

def get_db():
    conn = sqlite3.connect(os.environ.get("DB_PATH", "app.db"))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            degree TEXT NOT NULL,
            institution TEXT NOT NULL,
            graduation_year INTEGER NOT NULL,
            interests TEXT NOT NULL DEFAULT '',
            target_role TEXT NOT NULL,
            skills TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill TEXT NOT NULL,
            UNIQUE (user_id, skill),
            FOREIGN KEY (USER_id) REFERENCES users(id)
        )
    """)
    
    for table, column, ddl in [
        ("progress", "completed_at", "TEXT"),
        ("users", "is_admin", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS role_skills (
            role_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            demand INTEGER NOT NULL,
            PRIMARY KEY (role_id, skill_id),
            FOREIGN KEY (role_id) REFERENCES roles(id),
            FOREIGN KEY (skill_id) REFERENCES skills(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            cost TEXT NOT NULL,
            UNIQUE (skill_id, url),
            FOREIGN KEY (skill_id) REFERENCES skills(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            website TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS partner_roles (
            partner_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (partner_id, role_id),
            FOREIGN KEY (partner_id) REFERENCES partners(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            partner_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (user_id, partner_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (partner_id) REFERENCES partners(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill TEXT NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()
    seed_if_empty()


def seed_if_empty():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0] == 0:
        with open("data/roles.json") as f:
            data = json.load(f)
        for role, items in data.items():
            role_id = conn.execute("INSERT INTO roles (name) VALUES (?)", (role,)).lastrowid
            for item in items:
                conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (item["skill"],))
                skill_id = conn.execute(
                    "SELECT id FROM skills WHERE name = ?", (item["skill"],)
                ).fetchone()["id"]
                conn.execute(
                    "INSERT INTO role_skills (role_id, skill_id, demand) VALUES (?, ?, ?)",
                    (role_id, skill_id, item["demand"]),
                )
                for r in item.get("resources", []):
                    if r.get("url"):
                        conn.execute(
                            "INSERT OR IGNORE INTO resources (skill_id, title, url, cost) VALUES (?, ?, ?, ?)",
                            (skill_id, r["title"], r["url"], r["cost"]),
                        )
        conn.commit()
    conn.close()