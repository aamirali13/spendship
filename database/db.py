import os
import sqlite3
from datetime import date

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

# (day of current month, category, amount, description)
SEED_EXPENSES = [
    (2, "Food", 450.00, "Groceries at local market"),
    (4, "Transport", 120.00, "Auto rickshaw to office"),
    (5, "Bills", 1850.00, "Electricity bill"),
    (8, "Health", 600.00, "Pharmacy — vitamins"),
    (12, "Entertainment", 499.00, "Movie tickets"),
    (15, "Shopping", 2299.00, "Running shoes"),
    (18, "Other", 300.00, "Birthday gift for a friend"),
    (22, "Food", 780.50, "Dinner with family"),
]


def get_db():
    """Return a new SQLite connection. The caller is responsible for closing it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
            (user_id, amount, category, today.replace(day=day).isoformat(), description)
            for day, category, amount, description in SEED_EXPENSES
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
