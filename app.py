import os
import sqlite3
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    create_user,
    get_category_totals,
    get_expense_summary,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

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
# Profile data loaders (each section feeds one part of /profile)      #
# ------------------------------------------------------------------ #

# ---- Profile: transaction history ----
def _load_transactions(user_id):
    """Return the user's recent expenses for the transaction history table."""
    return get_recent_expenses(user_id)
# ---- end Profile: transaction history ----


# ---- Profile: summary stats ----
def _load_stats(user_id):
    """Return a fresh dict with the user's spend `total` and expense `count`."""
    return get_expense_summary(user_id)
# ---- end Profile: summary stats ----


# ---- Profile: category breakdown ----
def _load_categories(user_id):
    """Return the user's spending per category with its share of the total.

    Each item is a dict with "name", "amount" and "pct" (percent, 1 decimal),
    ordered from the highest total to the lowest.
    """
    rows = get_category_totals(user_id)
    grand_total = sum(r["total"] for r in rows)
    return [
        {
            "name": r["category"],
            "amount": r["total"],
            "pct": round(r["total"] / grand_total * 100, 1) if grand_total else 0,
        }
        for r in rows
    ]
# ---- end Profile: category breakdown ----


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


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        # The session points at a user that no longer exists (e.g. the DB was reset).
        session.clear()
        return redirect(url_for("login"))

    transactions = _load_transactions(user_id)
    categories = _load_categories(user_id)
    stats = _load_stats(user_id)
    stats["top_category"] = categories[0]["name"] if categories else "—"
    initials = "".join(part[0] for part in user["name"].split()[:2]).upper()

    return render_template(
        "profile.html",
        user={"name": user["name"], "email": user["email"], "member_since": user["created_at"]},
        initials=initials,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

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
