"""Tests for Step 5 — the profile page backend query helpers and route.

Runs against the seeded temp database provided by the `app` fixture in
conftest.py (demo user "Ahmed Khan" / demo@spendly.com with 8 expenses
totalling Rs 14,700.00).
"""

from database.db import get_user_by_email, create_user
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


def _demo_id():
    return get_user_by_email("demo@spendly.com")["id"]


# --------------------------------------------------------------------- #
# get_user_by_id                                                         #
# --------------------------------------------------------------------- #

def test_get_user_by_id_valid(app):
    user = get_user_by_id(_demo_id())
    assert user["name"] == "Ahmed Khan"
    assert user["email"] == "demo@spendly.com"
    assert user["member_since"] == "January 2026"


def test_get_user_by_id_missing(app):
    assert get_user_by_id(999999) is None


# --------------------------------------------------------------------- #
# get_summary_stats                                                      #
# --------------------------------------------------------------------- #

def test_get_summary_stats_with_expenses(app):
    stats = get_summary_stats(_demo_id())
    assert stats["total_spent"] == 14700.0
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Shopping"


def test_get_summary_stats_empty(app):
    uid = create_user("Empty User", "empty@spendly.com", "pw")
    assert get_summary_stats(uid) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


# --------------------------------------------------------------------- #
# get_recent_transactions                                               #
# --------------------------------------------------------------------- #

def test_get_recent_transactions_order_and_keys(app):
    txns = get_recent_transactions(_demo_id())
    assert len(txns) == 8
    assert set(txns[0].keys()) == {"date", "category", "description", "amount"}
    # Newest first (2026-05-22) … oldest last (2026-05-01), display-formatted.
    assert txns[0]["date"] == "22 May 2026"
    assert txns[-1]["date"] == "01 May 2026"


def test_get_recent_transactions_limit(app):
    assert len(get_recent_transactions(_demo_id(), limit=3)) == 3


def test_get_recent_transactions_empty(app):
    uid = create_user("Empty Two", "empty2@spendly.com", "pw")
    assert get_recent_transactions(uid) == []


# --------------------------------------------------------------------- #
# get_category_breakdown                                                #
# --------------------------------------------------------------------- #

def test_get_category_breakdown(app):
    breakdown = get_category_breakdown(_demo_id())
    assert len(breakdown) == 6
    assert set(breakdown[0].keys()) == {"category", "total", "percent"}
    # Ordered by total descending.
    totals = [row["total"] for row in breakdown]
    assert totals == sorted(totals, reverse=True)
    assert breakdown[0]["category"] == "Shopping"
    # Percentages are integers summing to exactly 100.
    assert all(isinstance(row["percent"], int) for row in breakdown)
    assert sum(row["percent"] for row in breakdown) == 100


def test_get_category_breakdown_empty(app):
    uid = create_user("Empty Three", "empty3@spendly.com", "pw")
    assert get_category_breakdown(uid) == []


# --------------------------------------------------------------------- #
# GET /profile route                                                     #
# --------------------------------------------------------------------- #

def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Ahmed Khan" in body
    assert "demo@spendly.com" in body
    assert "Rs" in body
    for category in ["Shopping", "Food", "Bills", "Entertainment", "Health", "Transport"]:
        assert category in body
