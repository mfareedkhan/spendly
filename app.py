import sqlite3

from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from database.db import init_db, seed_db, create_user, get_user_by_email
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = "spendly-dev-secret-key"


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
        # Stale session pointing at a deleted user — clear it and re-auth.
        session.clear()
        return redirect(url_for("login"))

    stats = get_summary_stats(user_id)
    transactions = get_recent_transactions(user_id)
    breakdown = get_category_breakdown(user_id)
    initials = "".join(w[0] for w in user["name"].split()[:2]).upper()

    return render_template(
        "profile.html", user=user, initials=initials, stats=stats,
        transactions=transactions, breakdown=breakdown,
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


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
