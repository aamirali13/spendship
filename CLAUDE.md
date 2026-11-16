# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly** — an expense tracker where users log, track and analyze their spending (amounts in ₹). It's a Claude Code learning project built feature by feature: placeholder routes in `app.py` mark the next step, and each step should be implemented to fit that sequence rather than jumping ahead.

## Commands

```bash
# Setup (virtualenv lives in .venv/)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the dev server on http://localhost:5001
flask --app app run --debug --port 5001
# or
python app.py

# Tests (pytest + pytest-flask; no tests/ directory exists yet)
pytest
pytest tests/test_foo.py::test_bar   # single test
```

There is no linter or build step configured.

## Architecture

Flask app, server-rendered with Jinja2, no frontend framework or build tooling.

**Request flow:** route in `app.py` → template in `templates/` → extends `base.html` → `static/css/style.css` + `static/js/main.js`.

**Routes (`app.py`):** All routes live in a single module. `/register` accepts GET and POST: it validates the form, creates the user via `create_user()`, flashes a `"success"` message and redirects to `/login`; on failure it re-renders with `error=` plus the typed `name`/`email`. `/login` accepts GET and POST: it normalises the email, checks the password with `check_password_hash`, then calls `session.clear()` and sets `session["user_id"]` and `session["user_name"]` before redirecting to `/profile`. On failure it re-renders with `error=` plus the typed `email`, and shows the same "Invalid email or password." message for an unknown email or a wrong password. Login has no password-length check, because the demo password is 7 characters. Signed-in users who visit `/login` or `/register` are redirected to `/profile`. `/logout` (GET) clears the session, flashes a `"success"` message and redirects to `/login`. `base.html` switches the navbar to the user's name plus "Sign out" when `session.user_id` is set. No route requires login yet. The other implemented pages (`/`, `/terms`, `/privacy`) only render templates and accept only GET. `login.html` renders flashed messages by category (`success` → `.auth-success`, anything else → `.auth-error`). `app.secret_key` comes from the `SECRET_KEY` environment variable, with a dev-only fallback in `app.py`.

**Planned step progression** (placeholder routes return a "coming in Step N" string):

| Step | Route | Purpose |
|------|-------|---------|
| 1 | — | Implement `database/db.py` |
| 4 | `/profile` | User profile page |
| 7 | `/expenses/add` | Create expense |
| 8 | `/expenses/<int:id>/edit` | Update expense |
| 9 | `/expenses/<int:id>/delete` | Remove expense |

**Database layer (`database/db.py`):** SQLite through the standard-library `sqlite3` module (no ORM). The database file is `spendly.db` in the project root (gitignored). Its path is built from `db.py`'s own location, so the working directory doesn't matter. The module exposes:
- `get_db()`: returns an open connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`. The caller must close it.
- `init_db()`: creates the `users` and `expenses` tables with `CREATE TABLE IF NOT EXISTS`
- `seed_db()`: inserts a demo user (`demo@spendly.com` / `demo123`) and 8 expenses, but only when `users` is empty
- `get_user_by_email(email)`: returns the user `Row` (including `password_hash`) or `None`. Pass an email already normalised with `.strip().lower()`
- `create_user(name, email, password)`: hashes the password with werkzeug, inserts the user and returns its id. Raises `sqlite3.IntegrityError` on a duplicate email
- `CATEGORIES`: the 7 allowed expense categories. `expenses.category` has a matching SQL `CHECK` constraint, so any change to the list must update both places.

`app.py` calls `init_db()` and `seed_db()` at import time inside `app.app_context()`. Because `CREATE TABLE IF NOT EXISTS` never alters an existing table, schema changes require deleting `spendly.db` so it gets recreated. SQL must always use `?` placeholders, never string formatting.

**Templates:** Every page extends `base.html`, which provides the navbar, footer, Google Fonts (DM Serif Display + DM Sans) and the single stylesheet/script includes. Override `{% block title %}` and `{% block content %}`, and optionally `{% block head %}` / `{% block scripts %}`. Page-specific JS goes inline in `{% block scripts %}` (see the demo-video modal in `landing.html`); `main.js` is an empty shared file.

**Styling:** One stylesheet, `static/css/style.css`, sectioned by banner comments. Design tokens (colors, fonts, radii, widths) are CSS custom properties on `:root`, so reuse them instead of hard-coding values. A former `landing.css` was merged into the end of this file, so some sections (e.g. "Hero") appear twice and the later rules win. Check both before editing landing styles.
