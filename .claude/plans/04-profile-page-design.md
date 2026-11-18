# Plan: Step 4 — Profile Page Design (implementation)

## Context
`/profile` (`app.py:122`) still returns the string "Profile page — coming in Step 4", even though login already redirects there. Spec `.claude/specs/04-profile-page-design.md` asks for a styled, **design-only** profile page that uses hardcoded sample data. A later step swaps that data for real DB queries. The design follows the project skill `.claude/skills/frontend-design/SKILL.md` (Spendly UI Designer), adapted to the tokens that already exist in `style.css`.

Work happens on branch `feature/profile-page-design-02`. Once approved, this plan is also saved as `.claude/plans/04-profile-page-design.md`, the per-project convention.

## UI plan (frontend-design skill, step 1)
- **Page header row:** a "Your profile" title in the `--font-display` serif with a muted subtitle on the left. An "Add expense" `.btn-primary` with a `plus` icon on the right links to `/expenses/add`, which is still the Step 7 placeholder.
- **Profile card:** a 56px circle with initials (`--accent-light` background, `--accent` text), then the name, the email and "Member since Nov 2026", each with a small Lucide icon (`mail`, `calendar`).
- **Stats row:** three equal tiles:
  - Total spent, with the `wallet` icon
  - Transactions, with the `receipt` icon
  - Top category, with the `tag` icon
  - Each tile shows a small uppercase label and a large `tabular-nums` value.
- **Two-column body:**
  - Left (about 2fr): a "Recent transactions" table (Date, Description, Category pill, Amount). The Amount column is right-aligned, rows highlight on hover, and the table scrolls sideways on mobile.
  - Right (about 1fr): a "Spending by category" card with one row per category showing the name, a ₹ total, a percentage and a 6px bar whose width is that category's share.
- **Empty state:** if `transactions` is empty, show a centred muted message plus an "Add your first expense" link. Assumption: the later DB step will rely on this.

## Files

### 1. `app.py` — modify `profile()` and add two small template filters
- **Route guard:** `if not session.get("user_id"): return redirect(url_for("login"))`
- **Sample data:** a module-level `SAMPLE_PROFILE` dict, so the later DB step only replaces this one source. It mirrors `SEED_EXPENSES` in `database/db.py` so the numbers feel real:
  - `user`: `name` comes from `session["user_name"]`, falling back to "Demo User". `email` is "demo@spendly.com" and `member_since` is "2026-11-01".
  - `transactions`: the 8 seed rows, each `{date: "YYYY-MM-DD", description, category, amount}`, sorted newest first.
- **Derived values:** computed in the route from the transactions, never typed in by hand, so they can't drift:
  - `total` (₹6,898.50)
  - `count` (8)
  - `top_category` (Shopping)
  - `categories`: a list of `{name, amount, pct}` sorted by amount descending, with `pct = round(amount / total * 100, 1)`
  - These calculations are DB-agnostic, so the next step keeps them as they are.
- **Template filters:**
  - `@app.template_filter("inr")` returns `"₹{:,.2f}".format(value)`.
  - `@app.template_filter("pretty_date")` turns an ISO date string into "22 Nov 2026" with `datetime.strptime`.
  - Both can be reused on the expense pages in Steps 7–9.
- `render_template("profile.html", user=..., stats=..., transactions=..., categories=...)`.
- Initials are computed in the template with `{{ user.name.split() | map('first') | join | upper }}` (first two words), or in the route if the template version gets messy.

### 2. `templates/profile.html` — create
- `{% extends "base.html" %}`, with `{% block title %}Profile — Spendly{% endblock %}`
- `{% block content %}` contains:
  ```
  section.profile-page > div.profile-inner
    header.profile-head      (title/subtitle + Add expense button)
    div.profile-card         (avatar + identity)
    div.profile-stats        (3 × div.profile-stat)
    div.profile-grid
      section.profile-panel  (Recent transactions; div.tx-table-wrap > table.tx-table)
      section.profile-panel  (Spending by category; ul.cat-list > li.cat-row)
  ```
- Category pill: `<span class="cat-pill cat-{{ tx.category|lower }}">`. Bar: `<span class="cat-bar cat-{{ c.name|lower }}" style="width: {{ c.pct }}%">`. Only the width is set inline, with no colours.
- `{% block scripts %}`: load Lucide from `https://unpkg.com/lucide@latest`, then run `lucide.createIcons()`.
  - The script is scoped to this page, so `base.html` doesn't change, as the spec requires.
  - It's a CDN script tag, not a pip dependency, and the page still reads fine if it fails to load (the icons are decorative and have `aria-hidden`).

### 3. `static/css/style.css` — append a `/* Profile page */` banner section at the end
- **Tokens:** reuse the existing ones only: `--paper`, `--paper-card`, `--border`, `--border-soft`, `--ink`, `--ink-soft`, `--ink-muted`, `--ink-faint`, `--accent`, `--accent-light`, `--accent-2`, `--accent-2-light`, `--teal`, `--teal-light`, `--danger`, `--danger-light`, `--radius-sm/md/lg`, `--font-display/body` and `--max-width`. The new rules contain **no hex values**.
- **Layout:**
  - `.profile-page` has `padding: 3rem 2rem`.
  - `.profile-inner` has `max-width: var(--max-width); margin: 0 auto; display: grid; gap: 1.5rem`.
- **Cards:** `.profile-card`, `.profile-stat` and `.profile-panel` reuse the `.auth-card` / `.feature-card` look (`--paper-card` background, 1px `--border`, `--radius-md`) with 1.5rem padding. There is no shadow beyond a border, per the skill's restraint rule.
- **Stats:** `.profile-stats` is `grid-template-columns: repeat(3, 1fr)`. Labels are 0.75rem uppercase in `--ink-muted` (matching `.mock-label`). Values are `--font-display` at 1.75rem with `font-variant-numeric: tabular-nums`.
- **Table:**
  - `.tx-table` has `width: 100%`, collapsed borders, 0.9rem text, and a `--border-soft` row separator.
  - `th` is uppercase in `--ink-muted` at 0.75rem.
  - `tr:hover` uses a `--paper` background.
  - `.tx-amount` is right-aligned with tabular-nums.
- **Category colours:** a shared `.cat-food` … `.cat-other` set drives both the pills (tinted background plus text colour) and the bars (solid background). It uses existing tokens, with `color-mix()` for the extra shades, a pattern `.auth-error` already uses:
  - Food → `--accent` / `--accent-light`
  - Transport → `--teal` / `--teal-light`
  - Bills → `--accent-2` / `--accent-2-light`
  - Health → `--danger` / `--danger-light`
  - Entertainment → `color-mix(in srgb, var(--accent) 50%, var(--teal))`, with the tint made by mixing that colour with `--paper-card`
  - Shopping → `color-mix(in srgb, var(--accent-2) 60%, var(--danger))`, tinted the same way
  - Other → `--ink-muted` / `--paper-warm`
- **Bars:** `.cat-bar-track` copies `.mock-bar-track` (6px, `--border-soft`, pill radius).
- **Icons:** `.profile-page svg.lucide` is 16px inline. Stat-tile icons are 20px, inside a 36px rounded square tinted with `--accent-light`.
- **Responsive:**
  - At `@media (max-width: 900px)`, `.profile-grid` becomes one column.
  - At `@media (max-width: 600px)`, `.profile-stats` becomes one column, `.profile-head` stacks, `.profile-page` padding drops to 2rem 1rem, and `.tx-table-wrap` gets `overflow-x: auto`.
  - These breakpoints match the 900px and 600px queries already in the file.

## Out of scope
- No DB queries and no `db.py` changes.
- No changes to `base.html`.
- No add/edit/delete expense logic.
- No new JS file.

## Verification
1. `flask --app app run --debug --port 5001`
2. Signed out, visiting `/profile` redirects to `/login`.
3. Sign in as `demo@spendly.com` / `demo123`. You land on the styled profile page, and the navbar shows "Demo User" and "Sign out".
4. Check the content:
   - The card shows "DU" initials, the email and "Member since".
   - The tiles show ₹6,898.50, 8 and Shopping.
   - The table has 8 rows, each with a coloured pill and a right-aligned ₹ amount.
   - The breakdown lists 7 categories, with percentages adding up to about 100% and bars of matching widths.
5. In DevTools at a 375px width, everything stacks into one column with no page-level horizontal scroll.
6. `git diff static/css/style.css | grep -E '^\+.*#[0-9a-fA-F]{3,6}'` returns nothing (no hex added).
7. `/`, `/login`, `/register`, `/terms` and `/privacy` still render.
8. After approval, copy this plan to `.claude/plans/04-profile-page-design.md`.
