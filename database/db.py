import os
import sqlite3
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

# Resolve the DB path from this file's location, not the current working
# directory, so the app always uses <project root>/spendly.db.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "spendly.db")

# Must stay in sync with the CHECK constraint on expenses.category below.
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL NOT NULL,
    category    TEXT NOT NULL CHECK (category IN (
                    'Food', 'Transport', 'Bills', 'Health',
                    'Entertainment', 'Shopping', 'Other'
                )),
    date        TEXT NOT NULL,  -- YYYY-MM-DD
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""

# (days before today, category, amount, description). Relative dates keep every
# seeded expense in the past, whatever day of the month the database is created.
SEED_EXPENSES = [
    (21, "Food", 450.00, "Groceries at local market"),
    (19, "Transport", 120.00, "Auto rickshaw to office"),
    (18, "Bills", 1850.00, "Electricity bill"),
    (15, "Health", 600.00, "Pharmacy — vitamins"),
    (11, "Entertainment", 499.00, "Movie tickets"),
    (8, "Shopping", 2299.00, "Running shoes"),
    (4, "Other", 300.00, "Birthday gift for a friend"),
    (1, "Food", 780.50, "Dinner with family"),
]


def get_db():
    """Return a new SQLite connection. The caller is responsible for closing it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user_by_email(email):
    """Return the user row for an (already normalised) email, or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Return the user row (without password_hash) for an id, or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password):
    """Hash the password, insert a new user and return its id.

    Raises sqlite3.IntegrityError if the email is already registered.
    """
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def init_db():
    """Create all tables. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert a demo user and sample expenses, only if no users exist yet."""
    conn = get_db()
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        today = date.today()
        rows = [
            (user_id, amount, category, (today - timedelta(days=days_ago)).isoformat(), description)
            for days_ago, category, amount, description in SEED_EXPENSES
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


# ---- Profile: transaction history ----
def get_recent_expenses(user_id, limit=10):
    """Return the user's most recent expenses, newest first."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()
# ---- end Profile: transaction history ----


# ---- Profile: summary stats ----
def get_expense_summary(user_id):
    """Return the user's total spend and expense count.

    Returns {"total": 0.0, "count": 0} when the user has no expenses.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return {"total": float(row["total"]), "count": int(row["count"])}
    finally:
        conn.close()
# ---- end Profile: summary stats ----


# ---- Profile: category breakdown ----
def get_category_totals(user_id):
    """Return (category, total) rows for the user, highest total first.

    Returns an empty list when the user has no expenses.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
# ---- end Profile: category breakdown ----
