# Skill Gap Analyzer

A web app that helps unemployed African graduates find the skills they are missing for a target job role and follow a step-by-step roadmap to close them. Phase 1 MVP.

**Stack:** Python 3, Flask, SQLite, HTML/CSS (no paid APIs).

**About the name:** Yes, "Skill Gap Analyzer" is a lame name. It's a working title, because this is only Phase 1 of something bigger: career-mapping and upskilling pathways for African youth.

## How to run

```
python -m venv venv
venv\Scripts\activate
pip install flask
python app.py
```

Then open http://127.0.0.1:5000

## How it works

1. A user registers and logs in.
2. They pick a target role and tick the skills they already have.
3. The gap engine compares them against the role's required skills and ranks the missing ones by demand.
4. The roadmap shows each gap as a step with free or paid learning links.
5. Ticking steps off raises the readiness score.

## Project files

- `app.py`: routes (register, login, logout, profile, report, roadmap, toggle)
- `gap.py`: gap engine (loads roles, computes and ranks gaps)
- `db.py`: SQLite setup (users, profiles, progress tables)
- `data/roles.json`: seed data (roles, skills, demand scores, resources)
- `templates/`, `static/`: pages and CSS

## Progress

Done:

- Registration with password hashing
- Login, logout and sessions
- Profile form saved to the database (one profile per user)
- Gap engine ranked by demand
- Gap report page
- Roadmap with free/paid resource tags
- Progress tracking and readiness score

## Unfinished

- Styled pages (current pages are plain HTML; the designed screens still need to be turned into templates)
- Landing page connected to the app (buttons still need to point to /register and /login)
- Pre-filled profile form when editing
- More roles and better resources (only Data Analyst so far; Communication and Cloud Data Warehouses have no resources yet; paid courses need free alternatives)
- Navigation bar that changes when logged in
- Deployment (move the secret key to an environment variable, turn off debug mode)
- Testing

Not planned for the MVP: admin screen, study tracker, employer routing, forgot password.
