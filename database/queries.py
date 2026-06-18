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
def get_recent_transactions(user_id, limit=10):
    """STUB — implemented by Subagent 1.

    Return a list of the user's most recent expenses, newest first, capped
    at `limit`. Each item is a dict with keys: "date", "category",
    "description", "amount". The "date" must be formatted for display as
    "DD Mon YYYY" (e.g. "18 May 2026") parsed from the stored "YYYY-MM-DD".
    A user with no expenses returns []. Parameterised queries only; close
    the connection before returning.
    """
    con = get_db()
    rows = con.execute(
        """
        SELECT date, category, description, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    con.close()

    return [
        {
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "category": row["category"],
            "description": row["description"],
            "amount": row["amount"],
        }
        for row in rows
    ]


# --- Subagent 2: get_summary_stats ---
def get_summary_stats(user_id):
    """STUB — implemented by Subagent 2.

    Return {"total_spent": float, "transaction_count": int,
    "top_category": str} for the user. total_spent is the sum of all their
    expense amounts; transaction_count is the number of expenses;
    top_category is the single category with the highest summed amount.
    A user with no expenses returns
    {"total_spent": 0, "transaction_count": 0, "top_category": "—"}.
    Parameterised queries only; close the connection before returning.
    """
    con = get_db()
    totals = con.execute(
        "SELECT COUNT(*) AS count, SUM(amount) AS total FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    top = con.execute(
        """
        SELECT category
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY SUM(amount) DESC, category ASC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
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
def get_category_breakdown(user_id):
    """STUB — implemented by Subagent 3.

    Return a list of dicts with keys "category", "total", "percent",
    ordered by "total" descending. "percent" values are integers that sum
    to exactly 100 — round each category's share, then add the leftover
    remainder to the largest category so the total is exactly 100. A user
    with no expenses returns []. Parameterised queries only; close the
    connection before returning.
    """
    con = get_db()
    rows = con.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
        """,
        (user_id,),
    ).fetchall()
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
