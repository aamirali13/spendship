# Spec: Login and Logout

## Overview
Make the existing `/login` page functional and replace the `/logout` placeholder
so registered users can sign in and out of Spendship. The login form in
`templates/login.html` already POSTs `email` and `password` to `/login` and
renders both `{{ error }}` and flashed messages; this step adds the server-side
handling: look up the user by normalised email, verify the password with
werkzeug's `check_password_hash`, store the user's id and name in Flask's
signed-cookie `session`, and redirect. `/logout` clears the session and sends
the user back to the login page. The navbar becomes session-aware. This is the
first step that tracks who is logged in, which Step 4 (profile) and the expense
steps (7–9) build on. Protecting those later routes is **not** part of this
step; it only provides the session they will check.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`, seeded demo user)
- Step 2 — Registration (`get_user_by_email()`, werkzeug-hashed passwords, `app.secret_key`, flashed messages on `login.html`)

## Routes
- `GET /login` — render the sign-in form; if already logged in, redirect to `/profile` — public
- `POST /login` — validate credentials; on success set the session and redirect to `/profile`; on failure re-render the form with `error=` and the typed `email` — public
- `GET /logout` — clear the session, flash "You have been signed out.", redirect to `/login` — public (works even when not logged in)

No new URLs: `login()` changes to `methods=["GET", "POST"]` and the `logout()` placeholder body is replaced. `/profile` stays a Step 4 placeholder; after login the user lands on its "coming in Step 4" text, which is expected.

## Database changes
No database changes. `get_user_by_email(email)` already returns `id`, `name`
and `password_hash`, which is everything login needs. No new `db.py` functions.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html`: repopulate the email input with the submitted value (`value="{{ email or '' }}"`) when re-rendered with an error. The password is never repopulated.
  - `templates/base.html`: make the navbar session-aware. When `session.user_id` is set, show the user's name (`session.user_name`) and a "Sign out" link to `url_for('logout')` instead of "Sign in" / "Get started". When logged out, keep the current links unchanged.

## Files to change
- `app.py`: import `session` from flask and `check_password_hash` from `werkzeug.security`; implement `login()` GET/POST; replace the `logout()` placeholder
- `templates/login.html`: keep the typed email after a failed submit
- `templates/base.html`: session-aware navbar links
- `static/css/style.css`: only if needed, a small style for the navbar user name in the navbar section, using existing CSS variables (e.g. `--ink-muted`)
- `CLAUDE.md`: update the Routes paragraph to describe `/login` POST and `/logout`

## Files to create
- `.claude/specs/03-login-logout.md` (this file)

## New dependencies
No new dependencies. `flask` (sessions) and `werkzeug` (`check_password_hash`) are already installed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders, never string formatting in SQL)
- Passwords hashed with werkzeug: verify with `check_password_hash(user["password_hash"], password)`; never compare plain text, never log passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Normalise the email with `.strip().lower()` before calling `get_user_by_email()`; do not strip the password
- Validation (first failure wins, message passed as `error=`):
  1. Email or password empty → "Please enter your email and password."
  2. No user with that email, **or** wrong password → the same generic message "Invalid email or password." (never reveal which one was wrong)
- Do **not** apply registration's 8-character minimum at login: the seeded demo password `demo123` is 7 characters and must still work
- On success: call `session.clear()` first (avoid carrying over old session data), then set `session["user_id"] = user["id"]` and `session["user_name"] = user["name"]`, then `redirect(url_for("profile"))`
- Store only `user_id` and `user_name` in the session — never the password hash or email-plus-hash
- A logged-in user hitting `GET /login` or `GET /register` is redirected to `/profile`
- `/logout`: `session.clear()`, `flash("You have been signed out.", "success")`, `redirect(url_for("login"))`
- Keep `app.secret_key` sourced from `SECRET_KEY` as in Step 2; do not change it
- Do not add a `login_required` decorator or protect other routes yet — that comes with the steps that need it

## Definition of done
- [ ] `GET /login` renders the form exactly as before when logged out
- [ ] Signing in with `demo@spendly.com` / `demo123` redirects to `/profile` (showing the Step 4 placeholder text)
- [ ] Signing in with ` Demo@Spendly.com ` (mixed case, surrounding spaces) also succeeds
- [ ] A user created through `/register` can sign in with their password
- [ ] A wrong password shows "Invalid email or password." and the email field keeps its value; the password field is empty
- [ ] An unregistered email shows the same "Invalid email or password." message
- [ ] Submitting with an empty field (bypass browser validation, e.g. with `curl`) shows "Please enter your email and password."
- [ ] After signing in, the navbar shows the user's name and "Sign out" instead of "Sign in" / "Get started"
- [ ] While signed in, visiting `/login` or `/register` redirects to `/profile`
- [ ] Clicking "Sign out" redirects to `/login`, shows "You have been signed out.", and the navbar returns to "Sign in" / "Get started"
- [ ] After signing out, visiting `/login` shows the form again (no redirect), and refreshing does not show the flash message again
- [ ] Visiting `/logout` while not signed in does not error and redirects to `/login`
- [ ] The session cookie contains no password or hash (it is signed, not encrypted: decode it to check)
- [ ] App starts without errors and no hex colours were added to `style.css`
