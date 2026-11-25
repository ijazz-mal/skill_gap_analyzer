# Skill Gap Analyzer

A web app that helps unemployed African graduates find the skills they are missing for a target job role and follow a step-by-step roadmap to close them. This is Phase 1 of a larger mission: career mapping and upskilling pathways for African youth. "Skill Gap Analyzer" is a working title.

**SRS:** [LINK TO SRS DOC](https://docs.google.com/document/d/15eVAp3qyqcJ9VboWFsXDISRKXpEbyht1mq3_kQ0L5jk/edit?usp=sharing)

**Stack:** Python 3 (tested on 3.13), Flask, SQLite, Jinja templates, plain HTML and CSS. No paid APIs.

## What it does

1. A graduate registers and logs in.
2. They enter a profile: degree, institution, graduation year, interests, target role and the skills they already have.
3. The gap engine compares their skills with the target role and ranks the missing ones by demand.
4. The roadmap shows each gap as a step, with free and paid learning resources. Ticking steps updates a readiness score.
5. When the score reaches the threshold (85%), the graduate sees partner organizations that hire for their role and can choose to share their profile (and withdraw that choice).
6. An administrator manages roles, skills, demand scores, resources and partner organizations, and sees shared profiles and a log of roadmap completions.

Actors: Graduate, Administrator, and Employer / Institution (partners are records managed by the admin and have no login).

## Run it locally (every step)

You need Python 3.10 or newer and Git.

**1. Clone the repository**

```
git clone https://github.com/ijazz-mal/skill_gap_analyzer.git
cd skill_gap_analyzer
```

**2. Create and activate a virtual environment**

Windows (PowerShell):

```
python -m venv venv
venv\Scripts\activate
```

If PowerShell says running scripts is disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and activate again.

macOS / Linux:

```
python3 -m venv venv
source venv/bin/activate
```

**3. Install the dependencies**

```
python -m pip install -r requirements.txt
```

**4. (Optional) Set a secret key.** Without it the app uses an insecure development key, which is fine on your own machine.

Windows (PowerShell): `$env:SECRET_KEY="any-long-random-string"`
macOS / Linux: `export SECRET_KEY="any-long-random-string"`

**5. Start the app**

```
python app.py
```

Open http://127.0.0.1:5000

On the first start the app creates `app.db` and loads the roles, skills and resources from `data/roles.json` automatically. To reload that file, stop the app, delete `app.db` and start again (all accounts are deleted too).

**6. Create an admin account.** Register through the site first, then run this (replace the email with the one you registered; emails are stored in lowercase):

```
python -c "import db; c = db.get_db(); c.execute('UPDATE users SET is_admin = 1 WHERE email = ?', ('you@example.com',)); c.commit()"
```

Log in again and open `/admin`.

## Try the main flow

1. Go to `/register` and create an account.
2. Fill in the profile, pick a role and tick some skills, then submit to see the gap report.
3. Open the roadmap and press "Mark done" on steps until the readiness score passes 85%.
4. As admin, add a partner organization for that role at `/admin`. Back on the roadmap, the partner appears with a "Share my profile" button.
5. Check the "Shared profiles" and "Roadmap completions log" sections on `/admin`.

## Project files

| File                | Purpose                                                         |
| ------------------- | --------------------------------------------------------------- |
| `app.py`            | Flask routes: pages, login, profile, roadmap, sharing, admin    |
| `gap.py`            | Gap engine: loads roles from the database, ranks gaps by demand |
| `db.py`             | SQLite tables and first-run seeding from `data/roles.json`      |
| `data/roles.json`   | Seed data: roles, skills, demand scores, resources (free/paid)  |
| `templates/`        | Jinja HTML templates (`base.html` is the shared layout)         |
| `static/styles.css` | All styling                                                     |
| `requirements.txt`  | Python dependencies                                             |

## Security notes

- Passwords are stored as salted hashes, never as plain text.
- All forms use CSRF tokens (Flask-WTF), and the session cookie is `SameSite=Lax` and `Secure` when `SECRET_KEY` is set (as on the live host).
- Admin routes check an `is_admin` flag on the server.
- Sharing a profile is the graduate's choice and can be withdrawn.

## Deployment (PythonAnywhere)

1. Clone the repo in a Bash console, create a virtualenv and run `pip install -r requirements.txt`.
2. Add a manual-configuration web app, set the source folder and virtualenv.
3. In the WSGI file, `chdir` into the project folder, set `SECRET_KEY` in `os.environ`, and `from app import app as application`.
4. Reload, register an account on the live site, then run the admin command from step 6 in the console.

## Known limitations

- The demand scores in `data/roles.json` are estimates, not measured market data.
- The Study Tracker and a separate progress dashboard from the prototype are not built.
- The database is a plain SQLite file, so there is no encryption at rest, and the free host cannot meet the 500-concurrent-user target in the SRS.
- No password reset and no login rate limiting yet.
- Resource links are third-party pages and may change.
- The app has no automated tests; it was tested by hand.
