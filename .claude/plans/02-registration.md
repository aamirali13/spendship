# Plan: Step 2 — Registration

## Context

`/register` currently only renders `templates/register.html` on GET. The form already POSTs `name`, `email` and `password` to `/register` and shows `{{ error }}`, but nothing handles the submission. This step implements `.claude/specs/02-registration.md`: server-side validation, a duplicate-email check, werkzeug password hashing, inserting into the existing `users` table, then a POST-redirect-GET to `/login` with a flashed success message. It also sets `app.secret_key`, which flashing needs now and Step 3's sessions will need later.

Branch: `feature/registration` (already created from `main` at `5657131`).

Out of scope: logging the user in, `/login` POST handling and `/logout` (all Step 3), automated tests, and any schema change.

## Decisions (confirmed with user: 1A 2A 3A 4A 5B 6B 7A)

1. **Helpers live in `database/db.py`, validation lives in `app.py`.** `get_user_by_email()` and `create_user()` only handle data access and hashing. The four validation rules stay in the `register()` view, written as a short series of checks so the order and messages match the spec exactly. Moving them into a separate validation helper isn't worth it for one form.
2. **`create_user()` expects an already-normalised email.** The view runs `.strip().lower()` on the email before both the lookup and the insert, so the helpers never change their inputs. The name is stripped. The password is passed through unchanged, so leading or trailing spaces in a password count.
3. **`create_user()` does not catch `sqlite3.IntegrityError`.** It lets the error propagate, and the view catches it and shows the duplicate-email message. That keeps the user-facing wording in one place.
4. **The secret key falls back to a fixed development value.** It's read with `os.environ.get("SECRET_KEY", ...)`, and the fallback string is named so it's obviously unsafe (e.g. `"dev-only-insecure-key-change-me"`). A comment beside it says to set `SECRET_KEY` in production. A random fallback (`os.urandom`) was ruled out because it would log everyone out on every debug reload once Step 3 adds sessions.
5. **No hex colours in either message box.** The new `.auth-success` copies the layout of `.auth-error` (padding, radius, font size, margin), with `var(--accent-light)` as the background and `var(--accent)` as the text colour. Its border uses `color-mix(in srgb, var(--accent) 25%, transparent)`, a soft border with no new hex value. **The existing `.auth-error` is fixed the same way:** its hard-coded `#f5c6c2` border becomes `color-mix(in srgb, var(--danger) 25%, transparent)`. That's a one-line change and should look nearly identical. After it, the auth section has no hex colours.
6. **Flash messages have categories.** Registration calls `flash(..., "success")`. `login.html` reads the messages with `get_flashed_messages(with_categories=true)` and picks the box style from the category: `"success"` gets `.auth-success`, and any other category (e.g. `"error"`) gets `.auth-error`. Only `"success"` is used in this step; Step 3 can flash `"error"` messages without touching the template again.
7. **`CLAUDE.md` gets a small update.** The Architecture section currently says every route accepts only GET and that no `secret_key` is set. Both stop being true, so I'll update those two sentences and mention the new `db.py` helpers.

## Change after implementation (requested by user)

Added a **Confirm password** field, like a typical sign-up form. `register.html` has a new `confirm_password` input below the password, which is never refilled after an error. The view now treats it as a required field, and after the length check it compares the two values exactly, showing "Passwords do not match." if they differ. That comparison comes before the duplicate-email lookup. Only the password itself is hashed and stored.

## Changes (in implementation order)

### 1. `database/db.py`: add two helpers below `get_db()`

- **`get_user_by_email(email)`**
  - Opens a connection with `get_db()` and runs `SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?` with `(email,)`.
  - Returns the result of `fetchone()`, which is a `sqlite3.Row` or `None`.
  - Closes the connection in `try/finally`.
  - Step 3's login will reuse it, which is why it returns `password_hash` too.
- **`create_user(name, email, password)`**
  - Hashes the password with the `generate_password_hash` that's already imported, using the default method (scrypt with werkzeug 3.1).
  - Runs `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)`. It leaves out `created_at` so the column default fills it in, the same way `seed_db()` does.
  - Commits, then returns `cursor.lastrowid`.
  - Closes the connection in `try/finally`. Any `IntegrityError` reaches the caller.
- Add a short docstring to each, matching the existing style. No other changes to the file. `seed_db()` keeps its own inline insert.

### 2. `app.py`: secret key and the `register()` view

- **Imports:** `import os` and `import sqlite3`. Expand the Flask import to `Flask, flash, redirect, render_template, request, url_for`. Expand the db import to include `create_user` and `get_user_by_email`.
- **Secret key:** right after `app = Flask(__name__)`, set `app.secret_key` from the `SECRET_KEY` environment variable with the fallback from Decision 4, plus a one-line comment.
- **Route:** change the decorator to `@app.route("/register", methods=["GET", "POST"])`.
- **GET:** render `register.html` exactly as now. The template's `name` and `email` variables are undefined, so they render empty.
- **POST, in this order:**
  1. Read `request.form.get(...)` for each field, defaulting to `""`. Strip the name. Strip and lowercase the email. Leave the password unchanged.
  2. **Required fields:** if the name, email or password is empty, re-render with `error="All fields are required."`.
  3. **Email format:** the email must contain `@`, the part before it must be non-empty, and there must be a `.` somewhere after the `@` that isn't the last character. Otherwise re-render with `"Please enter a valid email address."`. This is a deliberately simple check, not a full RFC parser.
  4. **Password length:** if `len(password) < 8`, re-render with `"Password must be at least 8 characters."`.
  5. **Duplicate:** if `get_user_by_email(email)` returns a row, re-render with `"An account with this email already exists."`.
  6. **Insert:** call `create_user(name, email, password)` inside `try`. On `sqlite3.IntegrityError`, re-render with the same duplicate message.
  7. **Success:** `flash("Account created — please sign in.", "success")`, then `return redirect(url_for("login"))`.
- **Re-rendering:** every error path calls `render_template("register.html", error=..., name=name, email=email)`, so the template can refill the fields. The password is never passed back. I'll write a tiny local helper inside the view (or a small module-level function) to avoid repeating that call 5 times. Errors return status 200, the Flask default, so the browser shows the form normally.

### 3. `templates/register.html`

- Add `value="{{ name or '' }}"` to the `name` input and `value="{{ email or '' }}"` to the `email` input. Jinja autoescaping keeps the values safe.
- The password input is unchanged and has no `value`.
- Nothing else changes: the HTML5 `required` attributes, the placeholders and `autofocus` all stay.

### 4. `templates/login.html`

- Inside `.auth-card`, before the existing `{% if error %}` block, add a loop over `get_flashed_messages(with_categories=true)`. Each `(category, message)` pair renders as a `<div>` with class `auth-success` when the category is `"success"`, and `auth-error` otherwise (Decision 6).
- The form and the rest of the page stay unchanged. Login still won't work until Step 3.

### 5. `static/css/style.css`

- In `.auth-error`, replace the `#f5c6c2` border colour with the `color-mix` on `var(--danger)` from Decision 5. Nothing else in that rule changes.
- Add a `.auth-success` rule directly after `.auth-error` in the auth section, styled as in Decision 5.
- Check the later, merged landing section to make sure no `.auth-*` rule overrides it.

### 6. `CLAUDE.md` (Decision 7)

- Change "Every route currently accepts only GET" to say `/register` now handles POST.
- Replace "No `app.secret_key` is set yet" with a note that it comes from the `SECRET_KEY` environment variable and has a dev fallback.
- In the Database layer list, add `get_user_by_email()` and `create_user()`.

## Verification (maps to the spec's Definition of done)

I'll run these myself after implementing, with Flask's test client in a scratchpad script plus `curl` against `flask --app app run --port 5001`. Test users go in with throwaway emails, which I'll delete afterwards so `spendly.db` (now tracked in git) only keeps the demo and seeded users.

1. `GET /register` returns 200, and the form looks the same as before.
2. A valid POST with a new email returns 302 to `/login`. Following the redirect shows "Account created — please sign in."
3. Querying the new row shows a `password_hash` starting with `scrypt:`, not the plain password, and `created_at` is filled in.
4. POST with `demo@spendly.com` shows the duplicate error, and the row count is unchanged.
5. POST with `Demo@Spendly.com ` (mixed case, trailing space) also shows the duplicate error.
6. POST with a 7-character password shows the length error.
7. POST with `abc` and with `abc@def` (via `curl`, skipping browser validation) shows the invalid-email error.
8. POST with a name of `"   "` shows "All fields are required."
9. After each error, the response HTML has the submitted name and email in the `value` attributes, and the password input has no value.
10. The success message renders inside a `div.auth-success` (checked in the HTML), and a second GET to `/login` after the flash no longer shows it.
11. The red error box on `/register` still renders correctly with the new `color-mix` border.
12. The app starts cleanly, `git diff static/css/style.css` adds no `#` colour literals, and the auth section (`.auth-*` rules) no longer contains any.

## Files touched

- Modified: `database/db.py`, `app.py`, `templates/register.html`, `templates/login.html`, `static/css/style.css`, `CLAUDE.md`
- Created: `.claude/plans/02-registration.md` (this file)
- No new dependencies and no schema change, so there's no need to delete `spendly.db`.
