from db import get_db

def load_roles():
    conn = get_db()
    resources = {}
    for r in conn.execute(
        "SELECT skill_id, title, url, cost FROM resources ORDER BY cost, title"
    ):
        resources.setdefault(r["skill_id"], []).append(
            {"title": r["title"], "url": r["url"], "cost": r["cost"]}
        )
    roles = {}
    rows = conn.execute(
        """SELECT r.name AS role, s.id AS skill_id, s.name AS skill, rs.demand
           FROM role_skills rs
           JOIN roles r ON r.id = rs.role_id
           JOIN skills s ON s.id = rs.skill_id
           ORDER BY r.name, rs.demand DESC"""
    ).fetchall()
    conn.close()
    for row in rows:
        roles.setdefault(row["role"], []).append(
            {
                "skill": row["skill"],
                "demand": row["demand"],
                "resources": resources.get(row["skill_id"], []),
            }
        )
    return roles


def compute_gaps(role, my_skills):
    required = load_roles()[role]
    gaps = [item for item in required if item["skill"] not in my_skills]
    gaps.sort(key=lambda g: g["demand"], reverse=True)
    return gaps
