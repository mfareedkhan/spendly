"""Tests for Step 8 — Edit Expense.

Covers:
  - Unit tests for database.queries.get_expense_by_id
  - Unit tests for database.queries.update_expense
  - Route tests for GET /expenses/<id>/edit  (auth guard, 200, pre-fill, ownership, 404)
  - Route tests for POST /expenses/<id>/edit (auth guard, valid submit, DB update,
    ownership 404, all validation failure cases, optional description behaviour)

All cases run against an isolated SQLite temp database (one per test function)
provided by the root conftest.py `app` fixture, which seeds the demo user
demo@spendly.com / demo123 with 8 expenses.

Fixtures used:
  app    — from conftest.py; sets SPENDLY_DB to a tmp file, inits & seeds the DB
  client — test client derived from `app`

No fixtures or helpers are imported from other test files.
"""

import pytest
from database.db import get_db, get_user_by_email, create_user
from database.queries import get_expense_by_id, update_expense


# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

VALID_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

VALID_PAYLOAD = {
    "amount": "75.50",
    "category": "Transport",
    "date": "2026-04-10",
    "description": "Careem to airport",
}


# ------------------------------------------------------------------ #
# Shared helpers                                                       #
# ------------------------------------------------------------------ #

def _login_demo(client):
    """Log the test client in as the seeded demo user."""
    return client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=False,
    )


def _demo_user_id():
    """Return the primary key of the demo user from the active temp DB."""
    row = get_user_by_email("demo@spendly.com")
    assert row is not None, "Demo user not found — seed_db() may have failed"
    return row["id"]


def _demo_expense_id():
    """Return the id of the first expense owned by the demo user."""
    user_id = _demo_user_id()
    con = get_db()
    row = con.execute(
        "SELECT id FROM expenses WHERE user_id = ? ORDER BY id ASC LIMIT 1",
        (user_id,),
    ).fetchone()
    con.close()
    assert row is not None, "No expenses found for demo user — seed_db() may have failed"
    return row["id"]


def _get_expense_row(expense_id):
    """Return the full expense row for the given id, or None."""
    con = get_db()
    row = con.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    con.close()
    return row


# ------------------------------------------------------------------ #
# Fixture: client derived from the shared app fixture                 #
# ------------------------------------------------------------------ #

@pytest.fixture
def client(app):
    """Flask test client backed by the isolated temp DB."""
    return app.test_client()


# ================================================================== #
# Unit tests — get_expense_by_id                                      #
# ================================================================== #

class TestGetExpenseByIdUnit:
    """Direct unit tests for database.queries.get_expense_by_id.

    The `app` fixture activates the correct SPENDLY_DB env var so that
    get_db() inside get_expense_by_id opens the temp database.
    """

    def test_returns_row_for_valid_id_and_owner(self, app):
        """get_expense_by_id with matching expense_id and user_id must return a Row."""
        user_id = _demo_user_id()
        expense_id = _demo_expense_id()

        row = get_expense_by_id(expense_id, user_id)

        assert row is not None, (
            "get_expense_by_id must return a Row when expense_id and user_id both match"
        )
        assert row["id"] == expense_id, (
            f"Returned row id must equal {expense_id}, got {row['id']}"
        )

    def test_returns_none_for_wrong_user_id(self, app):
        """get_expense_by_id must return None when user_id does not own the expense."""
        expense_id = _demo_expense_id()
        wrong_user_id = 999999

        row = get_expense_by_id(expense_id, wrong_user_id)

        assert row is None, (
            "get_expense_by_id must return None when the user_id does not match the owner"
        )

    def test_returns_none_for_nonexistent_expense_id(self, app):
        """get_expense_by_id must return None when expense_id does not exist."""
        user_id = _demo_user_id()
        nonexistent_id = 999999

        row = get_expense_by_id(nonexistent_id, user_id)

        assert row is None, (
            "get_expense_by_id must return None for a nonexistent expense_id"
        )


# ================================================================== #
# Unit tests — update_expense                                         #
# ================================================================== #

class TestUpdateExpenseUnit:
    """Direct unit tests for database.queries.update_expense.

    The `app` fixture activates the correct SPENDLY_DB env var.
    """

    def test_updates_amount_for_correct_owner(self, app):
        """update_expense must write the new amount to the DB when user_id matches."""
        user_id = _demo_user_id()
        expense_id = _demo_expense_id()
        original_row = _get_expense_row(expense_id)

        update_expense(
            expense_id,
            user_id,
            99.0,
            original_row["category"],
            original_row["date"],
            original_row["description"],
        )

        updated_row = _get_expense_row(expense_id)
        assert updated_row is not None, "Row must still exist after update_expense"
        assert updated_row["amount"] == pytest.approx(99.0), (
            f"DB amount must be 99.0 after update, got {updated_row['amount']}"
        )

    def test_does_not_update_for_wrong_user_id(self, app):
        """update_expense must not modify the row when user_id does not match the owner."""
        user_id = _demo_user_id()
        expense_id = _demo_expense_id()
        original_row = _get_expense_row(expense_id)
        original_amount = original_row["amount"]

        update_expense(
            expense_id,
            999999,  # wrong user_id
            original_amount + 500.0,
            original_row["category"],
            original_row["date"],
            original_row["description"],
        )

        row_after = _get_expense_row(expense_id)
        assert row_after is not None, "Row must still exist after failed update_expense"
        assert row_after["amount"] == pytest.approx(original_amount), (
            "update_expense with a wrong user_id must not change the stored amount"
        )


# ================================================================== #
# Route tests — GET /expenses/<id>/edit (unauthenticated)             #
# ================================================================== #

class TestGetEditExpenseUnauthenticated:
    """Auth guard tests for GET /expenses/<id>/edit."""

    def test_redirects_to_login(self, client, app):
        """Unauthenticated GET /expenses/<id>/edit must return 302 to /login."""
        expense_id = _demo_expense_id()

        resp = client.get(f"/expenses/{expense_id}/edit", follow_redirects=False)

        assert resp.status_code == 302, (
            "Unauthenticated GET /expenses/<id>/edit must redirect (302)"
        )
        location = resp.headers.get("Location", "")
        assert "/login" in location, (
            f"Redirect target must contain '/login', got '{location}'"
        )


# ================================================================== #
# Route tests — GET /expenses/<id>/edit (authenticated)               #
# ================================================================== #

class TestGetEditExpenseAuthenticated:
    """Happy-path and ownership tests for GET /expenses/<id>/edit."""

    def test_own_expense_returns_200(self, client, app):
        """GET /expenses/<id>/edit for an owned expense must return 200."""
        _login_demo(client)
        expense_id = _demo_expense_id()

        resp = client.get(f"/expenses/{expense_id}/edit")

        assert resp.status_code == 200, (
            "Authenticated GET for an owned expense must return 200"
        )

    def test_form_contains_prefilled_amount(self, client, app):
        """The edit form must be pre-filled with the expense's current amount."""
        _login_demo(client)
        expense_id = _demo_expense_id()
        row = _get_expense_row(expense_id)
        amount = row["amount"]

        resp = client.get(f"/expenses/{expense_id}/edit")
        body = resp.get_data(as_text=True)

        # Amount may render as "450.0" or "450" — check for the integer portion at minimum
        int_part = str(int(amount))
        assert int_part in body or str(amount) in body, (
            f"Edit form must contain the pre-filled amount '{amount}' (int part '{int_part}')"
        )

    def test_form_has_category_preselected(self, client, app):
        """The edit form must mark the expense's current category as selected."""
        _login_demo(client)
        expense_id = _demo_expense_id()
        row = _get_expense_row(expense_id)
        category = row["category"]

        resp = client.get(f"/expenses/{expense_id}/edit")
        body = resp.get_data(as_text=True)

        assert "selected" in body, (
            "Edit form must contain a 'selected' attribute on the current category option"
        )
        assert category in body, (
            f"Edit form must contain the expense's category '{category}'"
        )

    def test_other_users_expense_returns_404(self, client, app):
        """GET /expenses/<id>/edit for another user's expense must return 404."""
        _login_demo(client)

        # Create a second user and insert an expense owned by them
        other_user_id = create_user("Other User", "other@example.com", "otherpass")
        con = get_db()
        con.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (other_user_id, 100.0, "Food", "2026-01-01", "Other user expense"),
        )
        con.commit()
        other_expense_id = con.execute(
            "SELECT id FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (other_user_id,),
        ).fetchone()["id"]
        con.close()

        resp = client.get(f"/expenses/{other_expense_id}/edit", follow_redirects=False)

        assert resp.status_code == 404, (
            "GET /expenses/<id>/edit for another user's expense must return 404"
        )

    def test_nonexistent_expense_returns_404(self, client, app):
        """GET /expenses/999999/edit for a nonexistent expense must return 404."""
        _login_demo(client)

        resp = client.get("/expenses/999999/edit", follow_redirects=False)

        assert resp.status_code == 404, (
            "GET /expenses/999999/edit must return 404 for a nonexistent expense"
        )


# ================================================================== #
# Route tests — POST /expenses/<id>/edit (unauthenticated)            #
# ================================================================== #

class TestPostEditExpenseUnauthenticated:
    """Auth guard tests for POST /expenses/<id>/edit."""

    def test_redirects_to_login(self, client, app):
        """Unauthenticated POST /expenses/<id>/edit must return 302 to /login."""
        expense_id = _demo_expense_id()

        resp = client.post(
            f"/expenses/{expense_id}/edit",
            data=VALID_PAYLOAD,
            follow_redirects=False,
        )

        assert resp.status_code == 302, (
            "Unauthenticated POST /expenses/<id>/edit must redirect (302)"
        )
        location = resp.headers.get("Location", "")
        assert "/login" in location, (
            f"Redirect target must contain '/login', got '{location}'"
        )


# ================================================================== #
# Route tests — POST /expenses/<id>/edit (valid data)                 #
# ================================================================== #

class TestPostEditExpenseValidData:
    """Happy-path tests for POST /expenses/<id>/edit with valid data."""

    def test_redirects_to_profile(self, client, app):
        """Valid POST must return 302 and redirect to /profile."""
        _login_demo(client)
        expense_id = _demo_expense_id()

        resp = client.post(
            f"/expenses/{expense_id}/edit",
            data=VALID_PAYLOAD,
            follow_redirects=False,
        )

        assert resp.status_code == 302, (
            "A valid edit submission must redirect (302)"
        )
        location = resp.headers.get("Location", "")
        assert "/profile" in location, (
            f"Successful POST must redirect to /profile, got '{location}'"
        )

    def test_updates_db_correctly(self, client, app):
        """Valid POST must update all expense fields in the DB."""
        _login_demo(client)
        expense_id = _demo_expense_id()

        client.post(
            f"/expenses/{expense_id}/edit",
            data=VALID_PAYLOAD,
            follow_redirects=False,
        )

        row = _get_expense_row(expense_id)
        assert row is not None, "Expense row must still exist after a valid edit POST"
        assert row["amount"] == pytest.approx(75.50), (
            f"DB amount must be 75.50 after edit, got {row['amount']}"
        )
        assert row["category"] == "Transport", (
            f"DB category must be 'Transport' after edit, got '{row['category']}'"
        )
        assert row["date"] == "2026-04-10", (
            f"DB date must be '2026-04-10' after edit, got '{row['date']}'"
        )
        assert row["description"] == "Careem to airport", (
            f"DB description must be 'Careem to airport' after edit, got '{row['description']}'"
        )

    def test_no_description_saves_null(self, client, app):
        """POST without a description field must redirect to /profile and store NULL."""
        _login_demo(client)
        expense_id = _demo_expense_id()
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "description"}

        resp = client.post(
            f"/expenses/{expense_id}/edit",
            data=payload,
            follow_redirects=False,
        )

        assert resp.status_code == 302, (
            "POST without description must still succeed (302 redirect)"
        )
        location = resp.headers.get("Location", "")
        assert "/profile" in location, (
            f"POST without description must redirect to /profile, got '{location}'"
        )
        row = _get_expense_row(expense_id)
        assert row is not None, "Expense row must still exist after edit without description"
        assert row["description"] is None, (
            "Omitting description in the edit form must store NULL in the DB"
        )


# ================================================================== #
# Route tests — POST /expenses/<id>/edit (ownership)                  #
# ================================================================== #

class TestPostEditExpenseOwnership:
    """Ownership tests for POST /expenses/<id>/edit."""

    def test_other_users_expense_returns_404(self, client, app):
        """POST /expenses/<id>/edit targeting another user's expense must return 404."""
        _login_demo(client)

        # Create a second user and their expense
        other_user_id = create_user("Second User", "second@example.com", "secondpass")
        con = get_db()
        con.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (other_user_id, 200.0, "Bills", "2026-02-01", "Other user bill"),
        )
        con.commit()
        other_expense_id = con.execute(
            "SELECT id FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (other_user_id,),
        ).fetchone()["id"]
        con.close()

        resp = client.post(
            f"/expenses/{other_expense_id}/edit",
            data=VALID_PAYLOAD,
            follow_redirects=False,
        )

        assert resp.status_code == 404, (
            "POST to another user's expense must return 404"
        )


# ================================================================== #
# Route tests — POST /expenses/<id>/edit (validation failures)        #
# ================================================================== #

class TestPostEditExpenseValidation:
    """Validation failure tests for POST /expenses/<id>/edit.

    Every invalid submission must re-render the form (200) with an error
    message visible in the response body. No DB update must occur.
    """

    def test_missing_amount_returns_200_with_error(self, client, app):
        """POST with amount omitted must re-render the form (200) with an error."""
        _login_demo(client)
        expense_id = _demo_expense_id()
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "amount"}

        resp = client.post(
            f"/expenses/{expense_id}/edit",
            data=payload,
            follow_redirects=False,
        )

        assert resp.status_code == 200, (
            "Missing amount must cause form re-render (200), not a redirect"
        )
        body = resp.get_data(as_text=True)
        has_error = (
            "required" in body.lower()
            or "amount" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Response must contain an error message when amount is missing"
        )

    def test_amount_zero_returns_200_with_error(self, client, app):
        """POST with amount='0' must re-render the form (200) with an error."""
        _login_demo(client)
        expense_id = _demo_expense_id()
        payload = {**VALID_PAYLOAD, "amount": "0"}

        resp = client.post(
            f"/expenses/{expense_id}/edit",
            data=payload,
            follow_redirects=False,
        )

        assert resp.status_code == 200, (
            "Amount = 0 must fail validation and re-render the form (200)"
        )
        body = resp.get_data(as_text=True)
        has_error = (
            "zero" in body.lower()
            or "greater" in body.lower()
            or "positive" in body.lower()
            or "error" in body.lower()
            or "amount" in body.lower()
        )
        assert has_error, (
            "Response must contain an error message indicating amount must be greater than zero"
        )

    def test_non_numeric_amount_returns_200_with_error(self, client, app):
        """POST with amount='not-a-number' must re-render the form (200) with an error."""
        _login_demo(client)
        expense_id = _demo_expense_id()
        payload = {**VALID_PAYLOAD, "amount": "not-a-number"}

        resp = client.post(
            f"/expenses/{expense_id}/edit",
            data=payload,
            follow_redirects=False,
        )

        assert resp.status_code == 200, (
            "Non-numeric amount must fail validation and re-render the form (200)"
        )
        body = resp.get_data(as_text=True)
        has_error = (
            "valid" in body.lower()
            or "number" in body.lower()
            or "amount" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Response must contain an error message when amount is non-numeric"
        )

    def test_invalid_category_returns_200_with_error(self, client, app):
        """POST with category='Groceries' (not in fixed list) must return 200 with error."""
        _login_demo(client)
        expense_id = _demo_expense_id()
        payload = {**VALID_PAYLOAD, "category": "Groceries"}

        resp = client.post(
            f"/expenses/{expense_id}/edit",
            data=payload,
            follow_redirects=False,
        )

        assert resp.status_code == 200, (
            "An invalid category must fail validation and re-render the form (200)"
        )
        body = resp.get_data(as_text=True)
        has_error = (
            "category" in body.lower()
            or "valid" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Response must contain an error message when category is not in the fixed list"
        )

    def test_invalid_date_returns_200_with_error(self, client, app):
        """POST with date='not-a-date' must re-render the form (200) with an error."""
        _login_demo(client)
        expense_id = _demo_expense_id()
        payload = {**VALID_PAYLOAD, "date": "not-a-date"}

        resp = client.post(
            f"/expenses/{expense_id}/edit",
            data=payload,
            follow_redirects=False,
        )

        assert resp.status_code == 200, (
            "An invalid date must fail validation and re-render the form (200)"
        )
        body = resp.get_data(as_text=True)
        has_error = (
            "date" in body.lower()
            or "valid" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Response must contain an error message when date is not a valid YYYY-MM-DD string"
        )
