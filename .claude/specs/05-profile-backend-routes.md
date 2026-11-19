# Spec: Backend Routes for Profile Page

## Overview
Step 4 built the `/profile` page with hardcoded data: every signed-in user sees
the same `SAMPLE_PROFILE` dict from `app.py`, and only the name comes from the
session. This step connects the page to the database. The profile card, the
three stat tiles, the recent-transactions table and the category breakdown all
come from the logged-in user's rows in `users` and `expenses`. The template's
layout and styling stay the same. Only the data behind it changes, which was
the point of doing the design first. After this step, a newly registered user
sees an empty profile (zero totals and the empty-state messages), and the demo
user sees the 8 seeded expenses. That gives Steps 7–9 (add, edit and delete
expense) a real page where their changes show up.

## Depends on
- Step 1 — Database setup (`users` and `expenses` tables, `get_db()`, the seeded demo user and expenses)
- Step 2 — Registration (new users who start with no expenses)
- Step 3 — Login and logout (`session["user_id"]`, `session["user_name"]`)
- Step 4 — Profile page design (`templates/profile.html`, the `inr` and `pretty_date` filters, the empty states)

## Routes
No new routes. The existing route changes:
- `GET /profile` — renders `profile.html` with the logged-in user's real data instead of `SAMPLE_PROFILE` — logged-in

The route behaves like this:
1. If `session.user_id` is missing, redirect to `/login` (unchanged).
2. Load the user by id. If no row exists (for example, `spendly.db` was deleted while the session cookie was still valid), call `session.clear()` and redirect to `/login`.
3. Load the summary, the category totals and the recent transactions for that user, then render the template.

## Database changes
No schema changes. Checked against `database/db.py`: `users` already has `id`,
`name`, `email` and `created_at`, and `expenses` already has `user_id`,
`amount`, `category`, `date` and `description`. There is no need to delete
`spendly.db`.

New query functions in `database/db.py`. Each one opens its own connection with
`get_db()` and closes it in `finally`, the same way the existing helpers do:
- `get_user_by_id(user_id)`: returns the `Row` with `id, name, email, created_at`, or `None`. Leave out `password_hash` because the profile doesn't need it.
- `get_expense_summary(user_id)`: returns a dict `{"total": float, "count": int}` from one query using `COALESCE(SUM(amount), 0)` and `COUNT(*)`. A user with no expenses gets `{"total": 0, "count": 0}`.
- `get_category_totals(user_id)`: returns a list of `Row`s with `category` and `total`, built with `GROUP BY category` and ordered by `total DESC`. A user with no expenses gets an empty list.
- `get_recent_expenses(user_id, limit=10)`: returns a list of `Row`s with `id, date, description, category, amount`, ordered by `date DESC, id DESC` and capped with `LIMIT ?`.

Every query filters with `WHERE user_id = ?`, so a user can never see another user's expenses.

## Templates
- **Create:** none
- **Modify:**
  - `templates/profile.html`:
    - Change the subtitle from "An overview of your account and spending this month." to wording that doesn't claim "this month", because the totals cover all time (for example, "An overview of your account and spending.").
    - Change the "Recent transactions" table so that a `NULL` description shows "—" instead of "None" (`{{ tx.description or "—" }}`).
    - Keep everything else, including the variable names `user`, `initials`, `stats`, `transactions` and `categories`. The route must keep passing the same shapes the template already uses.

## Files to change
- `database/db.py`: add the four query functions above.
- `app.py`:
  - Import the new functions from `database.db`.
  - Remove the `SAMPLE_PROFILE` dict and the comment block above it.
  - Replace `_summarise()` with a small helper (for example `_build_categories(rows, total)`) that turns the category-total rows into the `[{"name", "amount", "pct"}]` list the template expects, with `pct = round(amount / total * 100, 1)` and `0` when the total is 0.
  - Rewrite the body of `profile()` as described under Routes, passing:
    - `user`: `{"name", "email", "member_since"}`, where `member_since` is the user's `created_at` (the `pretty_date` filter already reads only the first 10 characters)
    - `initials`: worked out from the database name, as now
    - `stats`: `{"total", "count", "top_category"}`, where `top_category` is the first category's name, or "—" when there are none
    - `transactions`: the recent-expense rows
    - `categories`: the list built by the helper
  - Move `profile()` out of the "Placeholder routes" section into the main routes section, because it's no longer a placeholder.
- `templates/profile.html`: the small text changes listed under Templates.
- `CLAUDE.md`: update the `/profile` description (it is now database-backed and `SAMPLE_PROFILE`/`_summarise()` are gone), and add the new `db.py` functions to the database layer list.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only. `user_id` and `limit` are passed as `?` parameters, never with f-strings or `%`.
- Passwords hashed with werkzeug. This step doesn't touch passwords, and `get_user_by_id` must not select `password_hash`.
- Use CSS variables — never hardcode hex values. No CSS changes are expected.
- All templates extend `base.html`
- Use the user id stored in the session as the only source of identity. Never take a user id from the query string or the form.
- Totals and per-category sums are calculated in SQL (`SUM`, `COUNT`, `GROUP BY`), not by loading every expense into Python.
- The stat tiles and category breakdown cover all of the user's expenses. Only the transactions table is limited to the most recent 10.
- Every database connection is closed (`try`/`finally`), the same way the existing helpers do it.
- Don't build Steps 7–9. The "Add expense" links still point to the existing placeholder.

## Definition of done
- [ ] Visiting `/profile` while signed out still redirects to `/login`.
- [ ] Signing in as `demo@spendly.com` / `demo123` shows the demo user's real name, email and a "Member since" month that matches `users.created_at`.
- [ ] The demo user's stat tiles show a total of ₹6,898.50, 8 transactions and "Shopping" as the top category, all read from `spendly.db`.
- [ ] The transactions table lists the demo expenses newest first, with category pills and right-aligned ₹ amounts.
- [ ] The category breakdown shows each category's ₹ total and percentage, sorted from highest to lowest, with bar widths that match the percentages.
- [ ] Changing an expense amount directly in `spendly.db` (for example with the `sqlite3` CLI) and refreshing `/profile` updates the total, the breakdown and the table.
- [ ] A newly registered user who signs in sees their own name and email, a total of ₹0.00, 0 transactions, "—" as the top category, and both empty-state messages. They see none of the demo user's expenses.
- [ ] A newly registered user signs in, `spendly.db` is deleted and the app is restarted, and the user then visits `/profile`. They are signed out and redirected to `/login` without a server error. Use a registered user rather than the demo user, because the reseed recreates the demo user with id 1.
- [ ] `SAMPLE_PROFILE` no longer appears in `app.py`.
- [ ] `/`, `/login`, `/register`, `/logout`, `/terms` and `/privacy` behave as before.
