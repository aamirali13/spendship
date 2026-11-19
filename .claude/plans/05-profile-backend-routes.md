# Plan: Step 05 — Backend Routes for Profile Page

## Context
`/profile` (Step 4) renders the hardcoded `SAMPLE_PROFILE` dict in `app.py`, so every signed-in
user sees the same 8 demo expenses. Spec `.claude/specs/05-profile-backend-routes.md` makes the page
show the logged-in user's real rows from `users` and `expenses`. The template layout stays the same
and only the data source changes. Branch: `feature/profile-backend-routes` (already created).

**Scope note:** the spec adds **no new URLs**. In this plan, the "transaction history route", the
"summary stats route" and the "category breakdown route" are the three data loaders behind
`GET /profile`. Each one is a DB query plus an `app.py` helper that feeds one section of the page.

**First action after approval:** copy this plan to `.claude/plans/05-profile-backend-routes.md`,
following the naming of the plans for Steps 01–04.

## Approach: scaffold first, then 3 parallel subagents, then integrate

All three subagents edit the same two files (`app.py`, `database/db.py`). To keep them from
clobbering each other, the main agent first creates **stub functions inside banner-marked
sections**. Each subagent then only replaces the bodies of its own stubs. Edits are narrow and
anchored to unique function names, so they don't overlap. If an Edit fails because the file
changed, the subagent re-reads the file and retries.

### Phase A — Scaffold (main agent, sequential)

**`database/db.py`**
- Add `get_user_by_id(user_id)` in full. It selects `id, name, email, created_at` (no
  `password_hash`) `WHERE id = ?`, follows the `get_db()`/`try`/`finally` pattern of
  `get_user_by_email`, and returns the `Row` or `None`.
- Add three banner sections, each with a stub that raises `NotImplementedError`:
  - `# --- Profile: transaction history ---` → `get_recent_expenses(user_id, limit=10)`
  - `# --- Profile: summary stats ---` → `get_expense_summary(user_id)`
  - `# --- Profile: category breakdown ---` → `get_category_totals(user_id)`

**`app.py`**
- Import `get_user_by_id`, `get_recent_expenses`, `get_expense_summary` and `get_category_totals`.
- Delete `SAMPLE_PROFILE`, its comment block and `_summarise()`.
- Add three banner sections, each with a stub helper:
  - `# Profile: transaction history` → `_load_transactions(user_id)`
  - `# Profile: summary stats` → `_load_stats(user_id)`
  - `# Profile: category breakdown` → `_load_categories(user_id)`
- Rewrite `profile()` and move it into the main routes section (out of "Placeholder routes"):
  1. If there is no `session["user_id"]`, redirect to `login`.
  2. Call `user = get_user_by_id(...)`. If it returns `None`, call `session.clear()` and redirect to `login`.
  3. `transactions = _load_transactions(uid)`, `categories = _load_categories(uid)` and `stats = _load_stats(uid)`.
  4. `stats["top_category"] = categories[0]["name"] if categories else "—"`. `profile()` owns
     this, so the stats and categories helpers stay independent.
  5. Compute `initials` from `user["name"]`, as now. Pass `user={"name", "email", "member_since": user["created_at"]}`
     along with `initials`, `stats`, `transactions` and `categories`, with the same names and shapes the template already uses.

**`templates/profile.html`**
- Change the subtitle to "An overview of your account and spending." (drop "this month").

### Phase B — Parallel subagents (3 `general-purpose` agents, launched in one message)

Every agent gets the same rules. It edits **only** its own stubs in `app.py` and `db.py` and nothing
else. It uses `?` placeholders and no ORM. It filters every query with `WHERE user_id = ?`. It
closes each connection in `try`/`finally`. It doesn't run the app (the main agent verifies).

| Agent | `database/db.py` | `app.py` | Extra |
|---|---|---|---|
| **1 — Transaction history** | `get_recent_expenses(user_id, limit=10)`: `SELECT id, date, description, category, amount ... ORDER BY date DESC, id DESC LIMIT ?` returns a list of `Row` | `_load_transactions(uid)` returns `get_recent_expenses(uid)` | In `profile.html`, change `{{ tx.description }}` to `{{ tx.description or "—" }}` (the only template edit it may make) |
| **2 — Summary stats** | `get_expense_summary(user_id)`: one query with `COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count`, returns `{"total": float, "count": int}` | `_load_stats(uid)` returns `{"total", "count"}` (`profile()` adds `top_category`) | — |
| **3 — Category breakdown** | `get_category_totals(user_id)`: `SELECT category, SUM(amount) AS total ... GROUP BY category ORDER BY total DESC` returns a list of `Row` | `_load_categories(uid)` builds `[{"name", "amount", "pct"}]`, where `pct = round(amount / grand_total * 100, 1)`, `grand_total` is the sum of the row totals, and `pct` is `0` when the total is 0 | — |

Agent 3 works out its own grand total from its rows, so it doesn't depend on Agent 2.

### Phase C — Integrate (main agent)
- Review the diff and confirm no `NotImplementedError` stubs remain and `SAMPLE_PROFILE` is gone.
- Update `CLAUDE.md`. `/profile` is now database-backed, so remove the mentions of `SAMPLE_PROFILE`, `_summarise()`
  and "design-only". Add the four new functions to the `db.py` list.
- Run the verification below.

## Critical files
- `app.py`: the profile section and the `profile()` route
- `database/db.py`: the four new query functions
- `templates/profile.html`: the subtitle and the description fallback
- `CLAUDE.md`: documentation update
- Reused: `get_db()` and the helper pattern of `get_user_by_email` (`database/db.py`), the
  `inr`/`pretty_date` filters (`app.py`, where `pretty_date` already slices `created_at[:10]`), and the
  existing empty states in `profile.html`

## Verification
1. `python -c "import app"` imports with no errors, and `grep -n "SAMPLE_PROFILE\|NotImplementedError" app.py database/db.py` returns nothing.
2. Start `flask --app app run --debug --port 5001`. Exercise the app with the Flask test client, using a script in the scratchpad (or a browser):
   - Signed out, `/profile` returns a 302 to `/login`.
   - Signed in as `demo@spendly.com` / `demo123`, the page shows ₹6,898.50, 8 transactions and top category "Shopping", with rows
     newest first and category percentages sorted from highest to lowest.
   - Change one amount with the `sqlite3` CLI and reload. The totals, breakdown and table update.
   - A newly registered user sees ₹0.00, 0, "—" and both empty states, and none of the demo user's rows.
   - Sign in as the new user, delete `spendly.db` and restart the app. `/profile` clears the session and redirects to `/login` with no 500 error.
3. `/`, `/login`, `/register`, `/logout`, `/terms` and `/privacy` behave as before.
