import os
import sqlite3
from datetime import datetime, date as date_today

from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from database.db import init_db, seed_db, create_user, get_user_by_email
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    insert_expense,
    get_expense_by_id,
    update_expense,
)
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "spendly-dev-secret-key")
app.config["TEMPLATES_AUTO_RELOAD"] = os.environ.get("FLASK_ENV") == "development"

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def _first_of_month_n_back(n):
    today = date_today.today()
    month = today.month - n
    year  = today.year
    while month <= 0:
        month += 12
        year  -= 1
    return date_today(year, month, 1).isoformat()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            return render_template(
                "register.html", error="All fields are required.",
                name=name, email=email,
            )
        if password != confirm_password:
            return render_template(
                "register.html", error="Passwords do not match.",
                name=name, email=email,
            )

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            return render_template(
                "register.html", error="Email already registered.",
                name=name, email=email,
            )

        flash("Account created — please log in.", "success")
        return redirect(url_for("login"))
    else:
        abort(405)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Invalid email or password.")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("profile"))
    else:
        abort(405)


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # --- Date filter parsing ---
    raw_from = request.args.get("date_from", "").strip()
    raw_to   = request.args.get("date_to",   "").strip()

    date_from = None
    date_to   = None

    try:
        if raw_from:
            datetime.strptime(raw_from, "%Y-%m-%d")
            date_from = raw_from
    except ValueError:
        raw_from = ""

    try:
        if raw_to:
            datetime.strptime(raw_to, "%Y-%m-%d")
            date_to = raw_to
    except ValueError:
        raw_to = ""

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = None
        date_to   = None
        raw_from  = ""
        raw_to    = ""

    # --- Preset date ranges ---
    today               = date_today.today()
    today_iso           = today.isoformat()
    preset_this_month   = (today.replace(day=1).isoformat(), today_iso)
    preset_last_3months = (_first_of_month_n_back(2), today_iso)
    preset_last_6months = (_first_of_month_n_back(5), today_iso)

    stats        = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    transactions = get_recent_transactions(user_id, date_from=date_from, date_to=date_to)
    breakdown    = get_category_breakdown(user_id, date_from=date_from, date_to=date_to)
    initials     = "".join(w[0] for w in user["name"].split()[:2]).upper()

    return render_template(
        "profile.html",
        user=user, initials=initials,
        stats=stats, transactions=transactions, breakdown=breakdown,
        date_from=date_from, date_to=date_to,
        raw_from=raw_from, raw_to=raw_to,
        preset_this_month=preset_this_month,
        preset_last_3months=preset_last_3months,
        preset_last_6months=preset_last_6months,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            today=date_today.today().isoformat(),
        )

    amount_raw  = request.form.get("amount", "").strip()
    category    = request.form.get("category", "")
    date_raw    = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip() or None

    error  = None
    amount = None

    if not amount_raw:
        error = "Amount is required."
    else:
        try:
            amount = float(amount_raw)
            if amount <= 0:
                error = "Amount must be greater than zero."
        except ValueError:
            error = "Amount must be a valid number."

    if not error and category not in CATEGORIES:
        error = "Please select a valid category."

    if not error:
        try:
            datetime.strptime(date_raw, "%Y-%m-%d")
        except ValueError:
            error = "Please enter a valid date."

    if error:
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            error=error,
            amount=amount_raw,
            category=category,
            date=date_raw,
            description=description,
            today=date_today.today().isoformat(),
        )

    insert_expense(session["user_id"], amount, category, date_raw, description)
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template("analytics.html", user=user)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=CATEGORIES,
            amount=expense["amount"],
            category=expense["category"],
            date=expense["date"],
            description=expense["description"] or "",
        )

    amount_raw  = request.form.get("amount", "").strip()
    category    = request.form.get("category", "")
    date_raw    = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip() or None

    error  = None
    amount = None

    if not amount_raw:
        error = "Amount is required."
    else:
        try:
            amount = float(amount_raw)
            if amount <= 0:
                error = "Amount must be greater than zero."
        except ValueError:
            error = "Amount must be a valid number."

    if not error and category not in CATEGORIES:
        error = "Please select a valid category."

    if not error:
        try:
            datetime.strptime(date_raw, "%Y-%m-%d")
        except ValueError:
            error = "Please enter a valid date."

    if error:
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=CATEGORIES,
            error=error,
            amount=amount_raw,
            category=category,
            date=date_raw,
            description=description or "",
        )

    update_expense(id, user_id, amount, category, date_raw, description)
    flash("Expense updated.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
