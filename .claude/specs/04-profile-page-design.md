# Spec: Profile Page Design

## Overview
Replace the `/profile` placeholder ("Profile page — coming in Step 4") with a
fully styled profile page, so users who sign in land on a real screen instead
of a plain string. This step is **design only**: every value on the page
(user details, summary stats, recent transactions, category breakdown) is
hardcoded sample data. The point is to settle the layout, components and
styling before any queries are written. A later step replaces the sample data
with the logged-in user's real rows from `users` and `expenses`. The page has
four parts:
- a user info card (avatar initials, name, email, "member since")
- three summary stat tiles (total spent, number of transactions, top category)
- a recent-transactions table (date, description, category, amount)
- a category breakdown, with one row per category showing its amount and a proportional bar

All amounts are in ₹, and all categories come from `CATEGORIES` in `database/db.py`.

## Depends on
- Step 1 — Database setup (`CATEGORIES` list; the seeded demo user for signing in)
- Step 2 — Registration (users who can sign in)
- Step 3 — Login and logout (`session["user_id"]` / `session["user_name"]`, the login redirect to `/profile`, the session-aware navbar)

## Routes
- `GET /profile` — render `profile.html` with hardcoded sample data. If `session.user_id` is not set, redirect to `/login` — logged-in

There are no new URLs. Only the body of the existing `profile()` placeholder in `app.py` changes. It still accepts only GET.

## Database changes
No database changes. Checked against `database/db.py`: the existing `users` and
`expenses` tables already have every column the final page will need (`name`,
`email`, `created_at`, `amount`, `category`, `date`, `description`). This step
adds no queries and no new `db.py` functions.

## Templates
- **Create:**
  - `templates/profile.html`: extends `base.html` and overrides `{% block title %}` ("Profile — Spendship") and `{% block content %}`. It has these sections:
    1. **Profile header card:** a circle with the user's initials, the name, the email and "Member since <Month YYYY>".
    2. **Stats row:** three tiles for Total spent (₹), Transactions (count) and Top category.
    3. **Recent transactions:** a table with Date, Description, Category (shown as a pill/badge) and Amount (right-aligned, ₹), with about 5–8 sample rows.
    4. **Category breakdown:** a list of categories, each with its ₹ total and a horizontal bar whose width is that category's share of the total.
    - An empty-state message is shown if the transactions list is empty, so the later DB step can rely on it.
- **Modify:** none. `base.html` already shows `session.user_name` and "Sign out" when signed in.

## Files to change
- `app.py`:
  - Replace the `profile()` placeholder body. If `session.get("user_id")` is not set, redirect to `url_for("login")`.
  - Otherwise, build a hardcoded sample-data dict (user, stats, transactions, categories) and pass it to `render_template("profile.html", ...)`.
- `static/css/style.css`: add a new `/* Profile page */` banner-comment section at the end of the file for the profile card, stat tiles, transactions table, category pills and breakdown bars.

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (this step adds no queries; the rule still applies to anything added)
- Passwords hashed with werkzeug (passwords are not touched in this step)
- Use CSS variables — never hardcode hex values. Use the `:root` tokens (`--ink*`, `--paper*`, `--accent*`, `--border*`, `--radius-*`, `--font-*`, `--max-width`).
- All templates extend `base.html`
- The sample data lives in a dict in the `profile()` route, not in the database and not scattered through the template. The template only loops over it and renders it, so the later DB step only has to swap out the dict.
- Sample categories must be values from `CATEGORIES`. Sample amounts are shown with ₹ and two decimals (for example `₹1,850.00`).
- Reuse the existing `.btn` styles and the card look from the Auth pages section where possible. Don't duplicate rules.
- No new JS file. Any page-specific JS goes inline in `{% block scripts %}`, though none should be needed.
- The layout is responsive. The stats row and the two-column area stack into one column on narrow screens (about 768px and below).
- Don't build Steps 7–9 (add/edit/delete expense). Links to `/expenses/add` may appear but must not be functional beyond the existing placeholder.

## Definition of done
- [ ] Visiting `/profile` while signed out redirects to `/login`.
- [ ] Signing in as `demo@spendly.com` / `demo123` lands on the styled profile page, not the "coming in Step 4" string.
- [ ] The profile card shows initials, a name, an email and a "Member since" date.
- [ ] Three stat tiles show total spent (₹), transaction count and top category.
- [ ] The recent-transactions table renders all sample rows, each with a category pill and a right-aligned ₹ amount.
- [ ] The category breakdown shows each sample category with a ₹ total and a bar proportional to its share.
- [ ] The page uses the site navbar and footer, and the navbar shows the user's name and "Sign out".
- [ ] `static/css/style.css` has a new "Profile page" section, and the added rules contain no hardcoded hex colours.
- [ ] At a viewport about 375px wide, the layout stacks into one column with no horizontal scrolling.
- [ ] `/`, `/login`, `/register`, `/terms` and `/privacy` still render as before.
