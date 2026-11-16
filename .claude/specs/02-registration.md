# Spec: Registration

## Overview
Make the existing `/register` page functional so visitors can create a Spendship
account. The form in `templates/register.html` already POSTs `name`, `email`
and `password` to `/register` and renders an `{{ error }}` variable; this step
adds the server-side handling: validate input, reject duplicate emails, hash
the password with werkzeug, insert the user into the `users` table and redirect
to the login page. It also sets `app.secret_key` so sessions and flashed
messages work, which Step 3 (login/logout) builds on. Logging in after
registration is **not** part of this step.

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `init_db()`, `users` table)

## Routes
- `GET /register` — render the registration form — public
- `POST /register` — validate the form, create the user, redirect to `/login` on success or re-render the form with `error` on failure — public

The existing `register` view is changed to `methods=["GET", "POST"]`; no new URL is added.

## Database changes
No database changes. The existing `users` table already has everything needed:
`id`, `name` (NOT NULL), `email` (NOT NULL UNIQUE), `password_hash` (NOT NULL),
`created_at` (default `datetime('now')`).

Two helper functions are added to `database/db.py` (no schema change):
- `get_user_by_email(email)`: returns the matching `sqlite3.Row` or `None`
- `create_user(name, email, password)`: hashes the password, inserts the row and returns the new user's `id`

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html`: add a "Confirm password" field (`name="confirm_password"`) below the password field; repopulate the `name` and `email` inputs with the submitted values (`value="{{ name or '' }}"`, `value="{{ email or '' }}"`) when the form is re-rendered with an error. The password is never repopulated.
  - `templates/login.html`: display flashed messages (e.g. "Account created — please sign in") above the form, using `get_flashed_messages()`

## Files to change
- `app.py`: import `request`, `redirect`, `url_for`, `flash`; set `app.secret_key`; change `register()` to handle GET and POST
- `database/db.py`: add `get_user_by_email()` and `create_user()`
- `templates/register.html`: keep entered values after a failed submit
- `templates/login.html`: show flashed success message
- `static/css/style.css`: add an `.auth-success` style next to the existing `.auth-error` in the auth section (reuse `--accent` / `--accent-light`)

## Files to create
- `.claude/specs/02-registration.md` (this file)

## New dependencies
No new dependencies. `flask` and `werkzeug` are already in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders, never string formatting in SQL)
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log plain text
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `app.secret_key` is read from the `SECRET_KEY` environment variable, with a clearly-labelled dev-only fallback string
- Every `get_db()` connection is closed in a `try/finally`
- Validation (in this order, first failure wins, message passed as `error=`):
  1. All four fields (name, email, password, confirm password) present after `.strip()` (passwords not stripped) → "All fields are required."
  2. Email contains `@` and a `.` after it → "Please enter a valid email address."
  3. Password at least 8 characters → "Password must be at least 8 characters."
  4. Password and confirm password match exactly → "Passwords do not match."
  5. Email not already registered → "An account with this email already exists."
- Emails are normalised with `.strip().lower()` before lookup and insert
- Also catch `sqlite3.IntegrityError` on insert (race on the UNIQUE constraint) and show the duplicate-email message
- On success: `flash("Account created — please sign in.")` then `redirect(url_for("login"))` (POST-redirect-GET)
- Do not log the user in or touch `/login` POST handling — that is Step 3

## Definition of done
- [ ] `GET /register` renders the form exactly as before
- [ ] Submitting a new name, email and 8+ character password redirects to `/login` and shows "Account created — please sign in."
- [ ] The new user appears in the `users` table with a werkzeug hash (starts with `scrypt:` or `pbkdf2:`), not the plain password
- [ ] Submitting `demo@spendly.com` shows "An account with this email already exists." and creates no row
- [ ] Submitting `Demo@Spendly.com ` (mixed case, trailing space) is also rejected as a duplicate
- [ ] A password shorter than 8 characters shows the length error
- [ ] A confirm password that differs from the password shows "Passwords do not match." and creates no row
- [ ] An email without `@` or domain shows the invalid-email error (test by bypassing browser validation, e.g. with `curl`)
- [ ] Blank or whitespace-only name shows "All fields are required."
- [ ] After any error, the name and email fields keep their values and the password field is empty
- [ ] Refreshing the `/login` page after the redirect does not resubmit the form or show the message again
- [ ] App starts without errors and no hex colours were added to `style.css`
