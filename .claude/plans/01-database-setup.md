# Plan: Step 1 — Database Setup

## Context

`database/db.py` is currently a comment-only stub. Every later step (auth, profile, expenses) needs a working SQLite data layer, so this step implements it per `.claude/specs/01-database-setup.md`: two tables (`users`, `expenses`), three functions (`get_db`, `init_db`, `seed_db`), and startup wiring in `app.py` so the DB exists and is seeded before any route runs. Work happens on branch `feature/database-setup`.

**First action after approval:** copy this plan to `.claude/plans/01-database-setup.md`, as requested. Note that `.claude/plans/` is gitignored, so the copy stays local.

## Decisions (confirmed with user)

- **DB filename: `spendly.db`**. Remove every trace of `expense_tracker.db` (details under Changes §0).
- **Path is absolute, resolved from `db.py`'s location** (`<project root>/spendly.db`). This means running Flask or pytest from another working directory can't create a stray DB somewhere else.
- **Category values are enforced in the database** with a `CHECK (category IN (...))` constraint on `expenses.category`. The same 7 values live in a Python constant `CATEGORIES` in `db.py` for later steps (the Step 7 form) to import. The CHECK list is written as a literal in the DDL rather than built from `CATEGORIES`, to honour the spec's "no string formatting in SQL" rule. Verification checks that the two stay in sync.
- **Seed dates use fixed days in the current month** (`date.today().replace(day=N).isoformat()`, days ≤ 28).
- **Connections are closed by the functions that open them.** `init_db()` and `seed_db()` use `try/finally: conn.close()`. `get_db()` just returns an open connection, and callers close it.

## Changes

### 0. Retire `expense_tracker.db`

- **Delete the existing `expense_tracker.db`** in the project root. I inspected it read-only: it's a leftover from an earlier run, holding 1 user and 8 expenses, with no CHECK constraint. It's gitignored, so nothing is tracked.
- **`.gitignore`:** replace the `expense_tracker.db` line with `spendly.db`. The file also has your earlier uncommitted edits (`context.txt`, `.venv/`), which stay as they are.
- **`CLAUDE.md`:** in the "Database layer" paragraph, change `expense_tracker.db` to `spendly.db` and mention the category CHECK constraint.

### 1. `database/db.py`: replace the stub

```python
import os
import sqlite3
from datetime import date
from werkzeug.security import generate_password_hash

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "spendly.db")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
```

- **`get_db()`**: `sqlite3.connect(DB_PATH)`, set `conn.row_factory = sqlite3.Row`, run `conn.execute("PRAGMA foreign_keys = ON")`, return `conn`.
- **`init_db()`**: one `conn.executescript(...)` with both `CREATE TABLE IF NOT EXISTS` statements, then commit and close.
  - `users`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `name TEXT NOT NULL`, `email TEXT NOT NULL UNIQUE`, `password_hash TEXT NOT NULL`, `created_at TEXT DEFAULT (datetime('now'))`
  - `expenses`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER NOT NULL REFERENCES users(id)`, `amount REAL NOT NULL`, `category TEXT NOT NULL CHECK (category IN ('Food', 'Transport', 'Bills', 'Health', 'Entertainment', 'Shopping', 'Other'))`, `date TEXT NOT NULL`, `description TEXT`, `created_at TEXT DEFAULT (datetime('now'))`
  - Note that `DEFAULT (datetime('now'))` needs the parentheses to be a valid expression default.
- **`seed_db()`**:
  1. `SELECT COUNT(*) FROM users`. If > 0, close and return early.
  2. `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)` with `"Demo User"`, `"demo@spendly.com"`, `generate_password_hash("demo123")`. Take `cursor.lastrowid` as `user_id`.
  3. `executemany("INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)", rows)` with 8 rows: one per category plus a second Food row. Amounts are floats in ₹.

     | Day | Category | Amount | Description |
     |---|---|---|---|
     | 2 | Food | 450.00 | Groceries at local market |
     | 4 | Transport | 120.00 | Auto rickshaw to office |
     | 5 | Bills | 1850.00 | Electricity bill |
     | 8 | Health | 600.00 | Pharmacy — vitamins |
     | 12 | Entertainment | 499.00 | Movie tickets |
     | 15 | Shopping | 2299.00 | Running shoes |
     | 18 | Other | 300.00 | Birthday gift for a friend |
     | 22 | Food | 780.50 | Dinner with family |
  4. Commit once, so the user and expenses are inserted atomically. Close in `finally`.
- All SQL is parameterized (`?` placeholders). No f-strings, `%` or `.format` anywhere in SQL. Exceptions are not caught, so integrity and syntax errors surface clearly.

### 2. `app.py`: wire up startup

- Add `from database.db import get_db, init_db, seed_db` below the Flask import.
- Right after `app = Flask(__name__)`:
  ```python
  with app.app_context():
      init_db()
      seed_db()
  ```
- Routes stay untouched. Both functions are idempotent, so the debug reloader running startup twice is harmless.

No new files and no new dependencies (`sqlite3` is stdlib, `werkzeug` is already pinned in `requirements.txt`).

## Verification

1. **Install deps.** The existing `.venv` currently has no Flask installed: `source .venv/bin/activate && pip install -r requirements.txt`
2. **Start the app:** `python app.py`. It should start without errors, `spendly.db` should appear in the project root, `expense_tracker.db` should be gone, and `http://localhost:5001/`, `/login` and `/register` should still render. Stop the server.
   - Also start it from another directory (`cd /tmp && python /home/bacancy/drive/spendship/app.py`) and confirm no `spendly.db` gets created outside the project root.
3. **Check data and constraints** with a throwaway script in the scratchpad (not in the repo), run from the project root:
   - `sqlite_master` lists the `users` and `expenses` tables with the expected columns (`PRAGMA table_info`).
   - There's 1 user and 8 expenses, the 7 distinct categories equal `CATEGORIES`, and every `user_id` matches the demo user.
   - `check_password_hash(row["password_hash"], "demo123")` is `True`, and the stored hash isn't the plaintext.
   - All dates match `^\d{4}-\d{2}-\d{2}$` and fall in the current month. `amount` has the SQLite type `real` (`typeof(amount)`).
   - Calling `init_db(); seed_db()` again leaves the counts at 1 and 8.
   - `PRAGMA foreign_keys` returns 1 on a `get_db()` connection.
   - Inserting a second `demo@spendly.com` user raises `sqlite3.IntegrityError` (UNIQUE).
   - Inserting an expense with `user_id=9999` raises `sqlite3.IntegrityError` (FOREIGN KEY).
   - Inserting an expense with `category='Groceries'` raises `sqlite3.IntegrityError` (CHECK).
   - Each value in `CATEGORIES` inserts successfully, which proves the constant and the CHECK list agree. Roll back afterwards.
4. **Restart `python app.py` once more**, then confirm there are still 1 user and 8 expenses (no duplicate seed).
5. **Check for unsafe SQL:** `grep -nE "execute.*(f\"|f'|%|\.format)" database/db.py` returns nothing.
