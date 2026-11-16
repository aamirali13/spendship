# Plan: Step 3 — Login and Logout

Spec: `.claude/specs/03-login-logout.md` · Branch: `feature/login-logout`
Saved copy goes to `.claude/plans/03-login-logout.md`, next to the existing plans.

## Context
Users can register (Step 2) but can't sign in. `/login` only renders the form, and `/logout` is a placeholder string. This step checks credentials, stores the user in Flask's signed `session`, makes the navbar show who is signed in, and adds sign-out. Steps 4 and 7–9 will rely on `session["user_id"]`.

## Existing pieces to reuse
- `get_user_by_email(email)` in `database/db.py`: already returns `id`, `name`, `password_hash`. No DB changes and no new db functions.
- `app.secret_key` in `app.py` (Step 2): sessions already work.
- `templates/login.html`: already POSTs to `/login` and renders `{{ error }}` plus flashed messages by category (`success` → `.auth-success`). The logout flash appears with no template changes.
- The `form_error()` inner-helper pattern in `register()` (`app.py`): reuse the same shape for login errors.
- The `.nav-links` / `.nav-cta` styles in `static/css/style.css`.

## Changes

### 1. `app.py`
- Imports: add `session` to the `flask` import. Add `from werkzeug.security import check_password_hash`.
- **`register()`**: first line, `if session.get("user_id"): return redirect(url_for("profile"))`. This applies to both GET and POST.
- **`login()`**: change to `@app.route("/login", methods=["GET", "POST"])`.
  1. Redirect to `profile` if `session.get("user_id")` is set (before the GET/POST branch).
  2. On GET, render `login.html`.
  3. On POST, `email = request.form.get("email", "").strip().lower()` and `password = request.form.get("password", "")` (not stripped).
  4. Add a local `form_error(message)` that renders `login.html` with `error=message, email=email`.
  5. If either field is empty, return `form_error("Please enter your email and password.")`.
  6. Run `user = get_user_by_email(email)`. If `user is None or not check_password_hash(user["password_hash"], password)`, return `form_error("Invalid email or password.")`.
  7. On success: `session.clear()`, then `session["user_id"] = user["id"]`, `session["user_name"] = user["name"]`, then `return redirect(url_for("profile"))`.
  8. Login has no length check, so `demo123` works.
- **`logout()`**: move it out of the "Placeholder routes" section into the main routes, next to `login()`. Body: `session.clear()`, `flash("You have been signed out.", "success")`, `return redirect(url_for("login"))`. It stays GET-only. Calling it while logged out is harmless.

### 2. `templates/login.html`
- Email input: add `value="{{ email or '' }}"`. Leave the password input as it is (never refilled).

### 3. `templates/base.html`: navbar `.nav-links`
```
{% if session.user_id %}
  <span class="nav-user">{{ session.user_name }}</span>
  <a href="{{ url_for('logout') }}" class="nav-cta">Sign out</a>
{% else %}
  (existing Sign in / Get started links, unchanged)
{% endif %}
```
"Sign out" uses `.nav-cta` so it stays visible on mobile. The rule at `@media (max-width: 600px)` hides every `.nav-links a` except `.nav-cta`. Jinja autoescapes the user name.

### 4. `static/css/style.css`
- In the Navbar section, after `.nav-links a:hover`, add `.nav-user { color: var(--ink-muted); }`. Variables only, no hex values.
- In the existing `@media (max-width: 600px)` block, add `.nav-user { display: none; }` to match how the other links collapse on mobile.

### 5. `CLAUDE.md`
- Routes paragraph: replace the "adding login means…" sentence with a description of `/login` GET/POST. It sets `session["user_id"]` and `session["user_name"]`, redirects to `/profile`, and redirects logged-in users away from `/login` and `/register`. Also describe `/logout` (clears the session, flashes, redirects to `/login`).
- Step table: remove the `/logout` row (now implemented).

## Decisions (correct before implementing if you disagree)
- After login, the user goes to `/profile`, which still shows the Step 4 placeholder text.
- Logout stays **GET**, matching the existing placeholder and a plain nav link. POST plus CSRF protection would be safer but needs a form; we can revisit later.
- No `login_required` decorator yet, as the spec says.
- No automated tests are added; there's no `tests/` directory yet. Verification is manual, below.

## Verification
Run `flask --app app run --debug --port 5001`, then:
1. Sign in as `demo@spendly.com` / `demo123`: you land on `/profile` and the navbar shows "Demo User" plus "Sign out".
2. Sign in with ` Demo@Spendly.com ` (mixed case, spaces): succeeds.
3. Wrong password, then an unknown email: both show "Invalid email or password." The email stays filled in and the password is empty.
4. Empty field via curl: `curl -s -X POST -d "email=&password=" localhost:5001/login | grep "Please enter"`.
5. While signed in, `/login` and `/register` redirect to `/profile`.
6. Click "Sign out": you're on `/login` with "You have been signed out." and the navbar is back to the logged-out links. Refreshing clears the message.
7. Visit `/logout` while logged out: it redirects to `/login` with no error.
8. Register a new user, then sign in with it: succeeds.
9. Decode the session cookie (`flask.sessions` / itsdangerous base64 payload) and confirm it holds only `user_id` and `user_name`, plus `_flashes` when one is pending.
10. Run `grep -n "#[0-9a-fA-F]\{3,6\}" static/css/style.css` and confirm the diff adds no new hex values. The narrow window (<600px) shows only "Sign out".
