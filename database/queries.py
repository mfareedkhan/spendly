"""Read-only query helpers for the profile page.

Each function opens its own connection via get_db(), uses parameterised
queries only, closes the connection before returning, and returns data
already shaped for templates/profile.html. None of these functions raise
on an empty result set — they return zeros / empty collections instead.
"""

from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    """Return {"name", "email", "member_since"} for a user, or None.

    `member_since` is derived from users.created_at (stored either as
    "YYYY-MM-DD" for the seed user or "YYYY-MM-DD HH:MM:SS" for users
    created via create_user) and formatted as "Month YYYY".
    """
    con = get_db()
    row = con.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    con.close()

    if row is None:
        return None

    member_since = datetime.strptime(row["created_at"][:10], "%Y-%m-%d").strftime("%B %Y")
    return {"name": row["name"], "email": row["email"], "member_since": member_since}


# --- Subagent 1: get_recent_transactions ---
def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    if date_from and date_to:
        sql = """
        SELECT id, date, category, description, amount
        FROM expenses
        WHERE user_id = ? AND date BETWEEN ? AND ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """
        params = (user_id, date_from, date_to, limit)
    else:
        sql = """
        SELECT id, date, category, description, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """
        params = (user_id, limit)

    con = get_db()
    rows = con.execute(sql, params).fetchall()
    con.close()

    return [
        {
            "id": row["id"],
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "category": row["category"],
            "description": row["description"],
            "amount": row["amount"],
        }
        for row in rows
    ]


# --- Subagent 2: get_summary_stats ---
def get_summary_stats(user_id, date_from=None, date_to=None):
    if date_from and date_to:
        sql_totals = "SELECT COUNT(*) AS count, SUM(amount) AS total FROM expenses WHERE user_id = ? AND date BETWEEN ? AND ?"
        sql_top    = """
        SELECT category FROM expenses
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1
        """
        params = (user_id, date_from, date_to)
    else:
        sql_totals = "SELECT COUNT(*) AS count, SUM(amount) AS total FROM expenses WHERE user_id = ?"
        sql_top    = """
        SELECT category FROM expenses
        WHERE user_id = ?
        GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1
        """
        params = (user_id,)

    con = get_db()
    totals = con.execute(sql_totals, params).fetchone()
    top    = con.execute(sql_top,    params).fetchone()
    con.close()

    transaction_count = totals["count"]
    if transaction_count == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": float(totals["total"]),
        "transaction_count": transaction_count,
        "top_category": top["category"],
    }


# --- Subagent 3: get_category_breakdown ---
def get_category_breakdown(user_id, date_from=None, date_to=None):
    if date_from and date_to:
        sql    = """
        SELECT category, SUM(amount) AS total FROM expenses
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY category ORDER BY total DESC
        """
        params = (user_id, date_from, date_to)
    else:
        sql    = """
        SELECT category, SUM(amount) AS total FROM expenses
        WHERE user_id = ?
        GROUP BY category ORDER BY total DESC
        """
        params = (user_id,)

    con = get_db()
    rows = con.execute(sql, params).fetchall()
    con.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    if grand_total == 0:
        return []

    breakdown = [
        {
            "category": row["category"],
            "total": row["total"],
            "percent": round(row["total"] / grand_total * 100),
        }
        for row in rows
    ]

    remainder = 100 - sum(item["percent"] for item in breakdown)
    breakdown[0]["percent"] += remainder

    return breakdown


def insert_expense(user_id, amount, category, expense_date, description):
    con = get_db()
    con.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    con.commit()
    con.close()


def get_expense_by_id(expense_id, user_id):
    con = get_db()
    row = con.execute(
        "SELECT id, user_id, amount, category, date, description "
        "FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    con.close()
    return row


def update_expense(expense_id, user_id, amount, category, date, description):
    con = get_db()
    con.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, date, description, expense_id, user_id),
    )
    con.commit()
    con.close()
