import os
import sqlite3
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_user_by_email, init_db, seed_db

app = Flask(__name__)

# Signs the session cookie (login state and flash messages). Set SECRET_KEY in production.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")

# Make sure the database schema and demo data exist before any route runs.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Template filters                                                    #
# ------------------------------------------------------------------ #

@app.template_filter("inr")
def format_inr(value):
    """Format a number as rupees, e.g. 1850 -> ₹1,850.00."""
    return "₹{:,.2f}".format(value)


@app.template_filter("pretty_date")
def format_pretty_date(value, fmt="%d %b %Y"):
    """Turn an ISO date string (YYYY-MM-DD) into e.g. '22 Nov 2026'."""
    return datetime.strptime(value[:10], "%Y-%m-%d").strftime(fmt)


# ------------------------------------------------------------------ #
# Sample data for the Step 4 profile design.                          #
# A later step replaces this with the logged-in user's real rows.     #
# ------------------------------------------------------------------ #

SAMPLE_PROFILE = {
    "user": {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "member_since": "2026-11-01",
    },
    "transactions": [
        {"date": "2026-11-22", "description": "Dinner with family", "category": "Food", "amount": 780.50},
        {"date": "2026-11-18", "description": "Birthday gift for a friend", "category": "Other", "amount": 300.00},
        {"date": "2026-11-15", "description": "Running shoes", "category": "Shopping", "amount": 2299.00},
        {"date": "2026-11-12", "description": "Movie tickets", "category": "Entertainment", "amount": 499.00},
        {"date": "2026-11-08", "description": "Pharmacy — vitamins", "category": "Health", "amount": 600.00},
        {"date": "2026-11-05", "description": "Electricity bill", "category": "Bills", "amount": 1850.00},
        {"date": "2026-11-04", "description": "Auto rickshaw to office", "category": "Transport", "amount": 120.00},
        {"date": "2026-11-02", "description": "Groceries at local market", "category": "Food", "amount": 450.00},
    ],
}


def _summarise(transactions):
    """Return (stats, categories) computed from a list of transaction dicts."""
    total = sum(tx["amount"] for tx in transactions)
    by_category = {}
    for tx in transactions:
        by_category[tx["category"]] = by_category.get(tx["category"], 0) + tx["amount"]

    categories = [
        {"name": name, "amount": amount, "pct": round(amount / total * 100, 1) if total else 0}
        for name, amount in sorted(by_category.items(), key=lambda item: item[1], reverse=True)
    ]
    stats = {
        "total": total,
        "count": len(transactions),
        "top_category": categories[0]["name"] if categories else "—",
    }
    return stats, categories


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


def _is_valid_email(email):
    """Simple shape check: something@something.tld (not a full RFC parser)."""
    local, at, domain = email.partition("@")
    return bool(local) and bool(at) and "." in domain[:-1]


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    def form_error(message):
        # Re-render with the typed name/email; never send the passwords back.
        return render_template("register.html", error=message, name=name, email=email)

    if not name or not email or not password or not confirm_password:
        return form_error("All fields are required.")
    if not _is_valid_email(email):
        return form_error("Please enter a valid email address.")
    if len(password) < 8:
        return form_error("Password must be at least 8 characters.")
    if password != confirm_password:
        return form_error("Passwords do not match.")
    if get_user_by_email(email) is not None:
        return form_error("An account with this email already exists.")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return form_error("An account with this email already exists.")

    flash("Account created — please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    def form_error(message):
        # Re-render with the typed email; never send the password back.
        return render_template("login.html", error=message, email=email)

    if not email or not password:
        return form_error("Please enter your email and password.")

    # Same message for unknown email and wrong password, so neither is revealed.
    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return form_error("Invalid email or password.")

    session.clear()  # drop any data left over from a previous session
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = dict(SAMPLE_PROFILE["user"], name=session.get("user_name") or SAMPLE_PROFILE["user"]["name"])
    transactions = SAMPLE_PROFILE["transactions"]
    stats, categories = _summarise(transactions)
    initials = "".join(part[0] for part in user["name"].split()[:2]).upper()

    return render_template(
        "profile.html",
        user=user,
        initials=initials,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
