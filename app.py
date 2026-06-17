import sqlite3

from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from database.db import init_db, seed_db, create_user, get_user_by_email
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

    # Hardcoded data for Step 4 — replaced with real DB queries in Step 5.
    user = {"name": "Aarav Sharma", "email": "aarav.sharma@example.com",
            "member_since": "March 2025"}
    transactions = [
        {"date": "14 Jun 2026", "category": "Food",          "description": "Lunch at Saravana Bhavan", "amount": 420},
        {"date": "12 Jun 2026", "category": "Transport",     "description": "Auto to office",            "amount": 180},
        {"date": "10 Jun 2026", "category": "Shopping",      "description": "Cotton kurta",              "amount": 1299},
        {"date": "08 Jun 2026", "category": "Bills",         "description": "Electricity bill",          "amount": 2150},
        {"date": "05 Jun 2026", "category": "Entertainment", "description": "Movie tickets",             "amount": 600},
        {"date": "02 Jun 2026", "category": "Food",          "description": "Groceries — BigBasket",     "amount": 1850},
    ]

    total_spent = sum(t["amount"] for t in transactions)
    totals = {}
    for t in transactions:
        totals[t["category"]] = totals.get(t["category"], 0) + t["amount"]
    breakdown = [
        {"category": c, "total": a, "percent": round(a / total_spent * 100)}
        for c, a in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ]
    top_category = breakdown[0]["category"]
    initials = "".join(w[0] for w in user["name"].split()[:2]).upper()
    stats = {"total_spent": total_spent, "transaction_count": len(transactions),
             "top_category": top_category}

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
