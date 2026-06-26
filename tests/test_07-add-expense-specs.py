"""Tests for Step 7 — Add Expense (spec: 07-add-expense-specs.md).

Covers:
  - Unit tests for database.queries.insert_expense
  - Route tests for GET /expenses/add (auth guard, form structure, categories)
  - Route tests for POST /expenses/add (auth guard, valid submit, all validation
    failure cases, optional description behaviour)

All cases run against an isolated SQLite temp database (one per test function)
provided by the root conftest.py `app` fixture, which seeds the demo user
demo@spendly.com / demo123 with 8 expenses.

Fixtures used:
  app    — from conftest.py; sets SPENDLY_DB to a tmp file, inits & seeds the DB
  client — test client derived from `app`

No fixtures or helpers are imported from other test files.
"""

import pytest
from database.db import get_db, get_user_by_email
from database.queries import insert_expense


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

# Spec happy-path payload (Section: POST — authenticated, valid data)
SPEC_PAYLOAD = {
    "amount": "50.0",
    "category": "Food",
    "date": "2026-03-20",
    "description": "Lunch",
}


# ------------------------------------------------------------------ #
# Shared helpers                                                        #
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


def _expense_rows(user_id):
    """Return all expense rows for *user_id* as a list of sqlite3.Row objects."""
    con = get_db()
    rows = con.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id ASC",
        (user_id,),
    ).fetchall()
    con.close()
    return rows


def _latest_expense(user_id):
    """Return the most recently inserted expense row for *user_id*, or None."""
    con = get_db()
    row = con.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    con.close()
    return row


def _expense_count(user_id):
    """Return the number of expense rows for *user_id*."""
    con = get_db()
    row = con.execute(
        "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    con.close()
    return row["cnt"]


# ------------------------------------------------------------------ #
# Fixture: client derived from the shared app fixture                 #
# ------------------------------------------------------------------ #

@pytest.fixture
def client(app):
    """Flask test client backed by the isolated temp DB."""
    return app.test_client()


# ================================================================== #
# Unit tests — insert_expense                                         #
# ================================================================== #

class TestInsertExpenseUnit:
    """Direct unit tests for database.queries.insert_expense.

    The `app` fixture is required to activate the correct SPENDLY_DB env var
    so that get_db() inside insert_expense opens the temp database.
    """

    def test_insert_with_all_fields_creates_row(self, app):
        """insert_expense with a full payload must create exactly one row."""
        user_id = _demo_user_id()
        count_before = _expense_count(user_id)

        insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")

        count_after = _expense_count(user_id)
        assert count_after == count_before + 1, (
            "insert_expense must insert exactly one new row into the expenses table"
        )

    def test_insert_with_all_fields_stores_correct_user_id(self, app):
        """The inserted row must be associated with the supplied user_id."""
        user_id = _demo_user_id()
        insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")
        row = _latest_expense(user_id)
        assert row is not None, "No expense row found after insert_expense call"
        assert row["user_id"] == user_id, (
            "Stored user_id must match the user_id argument passed to insert_expense"
        )

    def test_insert_with_all_fields_stores_correct_amount(self, app):
        """The inserted row must store the exact amount value supplied."""
        user_id = _demo_user_id()
        insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")
        row = _latest_expense(user_id)
        assert row is not None, "No expense row found after insert_expense call"
        assert row["amount"] == pytest.approx(50.0), (
            "Stored amount must equal 50.0"
        )

    def test_insert_with_all_fields_stores_correct_category(self, app):
        """The inserted row must store the exact category value supplied."""
        user_id = _demo_user_id()
        insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")
        row = _latest_expense(user_id)
        assert row is not None
        assert row["category"] == "Food", (
            "Stored category must equal 'Food'"
        )

    def test_insert_with_all_fields_stores_correct_date(self, app):
        """The inserted row must store the exact date string supplied."""
        user_id = _demo_user_id()
        insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")
        row = _latest_expense(user_id)
        assert row is not None
        assert row["date"] == "2026-03-20", (
            "Stored date must equal '2026-03-20'"
        )

    def test_insert_with_all_fields_stores_correct_description(self, app):
        """The inserted row must store the exact description string supplied."""
        user_id = _demo_user_id()
        insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")
        row = _latest_expense(user_id)
        assert row is not None
        assert row["description"] == "Lunch", (
            "Stored description must equal 'Lunch'"
        )

    def test_insert_with_description_none_stores_null(self, app):
        """When description=None is passed, the DB column must contain NULL."""
        user_id = _demo_user_id()
        insert_expense(user_id, 50.0, "Food", "2026-03-20", None)
        row = _latest_expense(user_id)
        assert row is not None, "No expense row found after insert_expense call"
        assert row["description"] is None, (
            "insert_expense(description=None) must store NULL in the DB, not an empty string"
        )

    def test_insert_with_description_none_row_is_queryable(self, app):
        """The row inserted with description=None must be retrievable and valid."""
        user_id = _demo_user_id()
        count_before = _expense_count(user_id)
        insert_expense(user_id, 50.0, "Food", "2026-03-20", None)
        count_after = _expense_count(user_id)
        assert count_after == count_before + 1, (
            "insert_expense with description=None must create a queryable row"
        )

    def test_insert_multiple_rows_all_stored(self, app):
        """Two successive calls to insert_expense must produce two distinct rows."""
        user_id = _demo_user_id()
        count_before = _expense_count(user_id)
        insert_expense(user_id, 10.0, "Food", "2026-03-20", "First")
        insert_expense(user_id, 20.0, "Bills", "2026-03-21", "Second")
        count_after = _expense_count(user_id)
        assert count_after == count_before + 2, (
            "Two insert_expense calls must produce exactly two new rows"
        )


# ================================================================== #
# Route tests — GET /expenses/add                                     #
# ================================================================== #

class TestGetAddExpense:
    """Tests for GET /expenses/add."""

    # Auth guard ------------------------------------------------------- #

    def test_unauthenticated_get_redirects(self, client, app):
        """Unauthenticated GET /expenses/add must return 302."""
        resp = client.get("/expenses/add", follow_redirects=False)
        assert resp.status_code == 302, (
            "Unauthenticated GET /expenses/add must redirect (302), not return a page"
        )

    def test_unauthenticated_get_redirects_to_login(self, client, app):
        """Unauthenticated GET /expenses/add must redirect to /login."""
        resp = client.get("/expenses/add", follow_redirects=False)
        location = resp.headers.get("Location", "")
        assert "/login" in location, (
            f"Redirect target must be /login, got '{location}'"
        )

    # Happy path: authenticated --------------------------------------- #

    def test_authenticated_get_returns_200(self, client, app):
        """Authenticated GET /expenses/add must return 200."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        assert resp.status_code == 200, (
            "Authenticated GET /expenses/add must return 200"
        )

    def test_authenticated_get_renders_form_tag(self, client, app):
        """The response must contain an HTML <form element."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert "<form" in body, (
            "Authenticated GET /expenses/add must render an HTML <form element"
        )

    def test_authenticated_get_form_uses_post_method(self, client, app):
        """The form must specify POST as its method."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        # Accept both method="POST" and method="post" (case-insensitive HTML)
        assert 'method="POST"' in body or 'method="post"' in body, (
            "The add-expense form must use method='POST'"
        )

    def test_authenticated_get_renders_select_element(self, client, app):
        """The response must contain a <select element for category."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert "<select" in body, (
            "The add-expense form must contain a <select element for category"
        )

    @pytest.mark.parametrize("category", VALID_CATEGORIES)
    def test_authenticated_get_renders_all_seven_categories(self, client, app, category):
        """Each of the 7 fixed categories must appear in the rendered form."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert category in body, (
            f"Category option '{category}' must appear in the add-expense form"
        )

    def test_authenticated_get_exactly_seven_valid_categories_present(self, client, app):
        """All seven valid category names must each appear at least once in the response."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        missing = [cat for cat in VALID_CATEGORIES if cat not in body]
        assert not missing, (
            f"The following categories are missing from the form: {missing}"
        )

    def test_authenticated_get_form_action_points_to_add_expense(self, client, app):
        """The form action must reference the /expenses/add route."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert "/expenses/add" in body, (
            "The form action must point to /expenses/add"
        )

    def test_authenticated_get_renders_amount_field(self, client, app):
        """The form must contain an amount input field."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert 'name="amount"' in body or "amount" in body.lower(), (
            "The add-expense form must render an amount field"
        )

    def test_authenticated_get_renders_date_field(self, client, app):
        """The form must contain a date input field."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert 'name="date"' in body or 'type="date"' in body, (
            "The add-expense form must render a date field"
        )

    def test_authenticated_get_renders_description_field(self, client, app):
        """The form must contain a description field (optional)."""
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert "description" in body.lower(), (
            "The add-expense form must render a description field"
        )


# ================================================================== #
# Route tests — POST /expenses/add                                    #
# ================================================================== #

class TestPostAddExpenseAuthGuard:
    """Auth guard tests for POST /expenses/add."""

    def test_unauthenticated_post_redirects(self, client, app):
        """Unauthenticated POST /expenses/add must return 302."""
        resp = client.post(
            "/expenses/add",
            data=SPEC_PAYLOAD,
            follow_redirects=False,
        )
        assert resp.status_code == 302, (
            "Unauthenticated POST /expenses/add must redirect (302)"
        )

    def test_unauthenticated_post_redirects_to_login(self, client, app):
        """Unauthenticated POST /expenses/add must redirect to /login."""
        resp = client.post(
            "/expenses/add",
            data=SPEC_PAYLOAD,
            follow_redirects=False,
        )
        location = resp.headers.get("Location", "")
        assert "/login" in location, (
            f"Unauthenticated POST must redirect to /login, got '{location}'"
        )

    def test_unauthenticated_post_inserts_no_row(self, client, app):
        """Unauthenticated POST must not insert any expense row."""
        user_id = _demo_user_id()
        count_before = _expense_count(user_id)
        client.post("/expenses/add", data=SPEC_PAYLOAD, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before, (
            "Unauthenticated POST must not insert any expense row into the DB"
        )


class TestPostAddExpenseValidData:
    """Happy-path tests for POST /expenses/add with valid data."""

    def test_valid_post_redirects(self, client, app):
        """Valid POST must return 302."""
        _login_demo(client)
        resp = client.post(
            "/expenses/add",
            data=SPEC_PAYLOAD,
            follow_redirects=False,
        )
        assert resp.status_code == 302, (
            "A valid expense submission must redirect (302)"
        )

    def test_valid_post_redirects_to_profile(self, client, app):
        """Valid POST must redirect to /profile."""
        _login_demo(client)
        resp = client.post(
            "/expenses/add",
            data=SPEC_PAYLOAD,
            follow_redirects=False,
        )
        location = resp.headers.get("Location", "")
        assert "/profile" in location, (
            f"Successful POST must redirect to /profile, got '{location}'"
        )

    def test_valid_post_inserts_exactly_one_row(self, client, app):
        """Valid POST must insert exactly one new expense row for the user."""
        user_id = _demo_user_id()
        count_before = _expense_count(user_id)
        _login_demo(client)
        client.post("/expenses/add", data=SPEC_PAYLOAD, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before + 1, (
            "Valid POST must result in exactly one new expense row in the DB"
        )

    def test_valid_post_stores_correct_amount(self, client, app):
        """The stored amount must equal the submitted value (50.0)."""
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=SPEC_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None, "Expected a new expense row after valid POST"
        assert row["amount"] == pytest.approx(50.0), (
            f"Stored amount must be 50.0, got {row['amount']}"
        )

    def test_valid_post_stores_correct_category(self, client, app):
        """The stored category must equal 'Food' as submitted."""
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=SPEC_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None
        assert row["category"] == "Food", (
            f"Stored category must be 'Food', got '{row['category']}'"
        )

    def test_valid_post_stores_correct_date(self, client, app):
        """The stored date must equal '2026-03-20' as submitted."""
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=SPEC_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None
        assert row["date"] == "2026-03-20", (
            f"Stored date must be '2026-03-20', got '{row['date']}'"
        )

    def test_valid_post_stores_correct_description(self, client, app):
        """The stored description must equal 'Lunch' as submitted."""
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=SPEC_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None
        assert row["description"] == "Lunch", (
            f"Stored description must be 'Lunch', got '{row['description']}'"
        )

    def test_valid_post_row_belongs_to_logged_in_user(self, client, app):
        """The inserted expense must be linked to the authenticated user."""
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=SPEC_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None
        assert row["user_id"] == user_id, (
            "The expense must be stored with the correct user_id"
        )


class TestPostAddExpenseMissingAmount:
    """Validation failure tests when amount is missing or invalid."""

    def test_missing_amount_returns_200(self, client, app):
        """POST with amount omitted must re-render the form (200), not redirect."""
        _login_demo(client)
        payload = {k: v for k, v in SPEC_PAYLOAD.items() if k != "amount"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            "Missing amount must cause form re-render (200), not a redirect"
        )

    def test_missing_amount_shows_error_message(self, client, app):
        """POST with amount omitted must display an error message in the response."""
        _login_demo(client)
        payload = {k: v for k, v in SPEC_PAYLOAD.items() if k != "amount"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        body = resp.get_data(as_text=True)
        # The error message must contain meaningful text about the failure
        assert len(body) > 0, "Response body must not be empty"
        has_error = (
            "required" in body.lower()
            or "amount" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Response must contain an error message when amount is missing"
        )

    def test_empty_amount_returns_200(self, client, app):
        """POST with amount='' (empty string) must re-render the form (200)."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "amount": ""}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            "Empty amount must cause form re-render (200), not a redirect"
        )

    def test_empty_amount_shows_error_message(self, client, app):
        """POST with amount='' must include an error message in the response."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "amount": ""}
        resp = client.post("/expenses/add", data=payload)
        body = resp.get_data(as_text=True)
        has_error = (
            "required" in body.lower()
            or "amount" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Response must contain an error message when amount is an empty string"
        )

    def test_missing_amount_inserts_no_row(self, client, app):
        """Validation failure on amount must not write any row to the DB."""
        user_id = _demo_user_id()
        _login_demo(client)
        count_before = _expense_count(user_id)
        payload = {k: v for k, v in SPEC_PAYLOAD.items() if k != "amount"}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before, (
            "A missing-amount POST must not insert any expense row"
        )


class TestPostAddExpenseAmountZero:
    """Validation failure tests when amount equals zero."""

    def test_amount_zero_returns_200(self, client, app):
        """POST with amount=0 must re-render the form (200), not redirect."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "amount": "0"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            "Amount = 0 must fail validation and re-render the form (200)"
        )

    def test_amount_zero_shows_error_message(self, client, app):
        """POST with amount=0 must display an error message."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "amount": "0"}
        resp = client.post("/expenses/add", data=payload)
        body = resp.get_data(as_text=True)
        has_error = (
            "zero" in body.lower()
            or "greater" in body.lower()
            or "positive" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Response must contain an error message indicating amount must be greater than zero"
        )

    def test_amount_zero_float_returns_200(self, client, app):
        """POST with amount='0.00' (zero as float string) must also fail (200)."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "amount": "0.00"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            "Amount 0.00 must fail validation and re-render (200)"
        )

    def test_amount_zero_inserts_no_row(self, client, app):
        """amount=0 validation failure must not write any row to the DB."""
        user_id = _demo_user_id()
        _login_demo(client)
        count_before = _expense_count(user_id)
        payload = {**SPEC_PAYLOAD, "amount": "0"}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before, (
            "amount=0 POST must not insert any expense row"
        )


class TestPostAddExpenseNonNumericAmount:
    """Validation failure tests when amount is not a valid number."""

    @pytest.mark.parametrize("bad_amount,label", [
        ("abc",      "alphabetic string"),
        ("twelve",   "English word"),
        ("12.3.4",   "malformed decimal"),
        ("1,000",    "comma-formatted number"),
        ("$50",      "currency symbol prefix"),
        ("50 dollars", "amount with trailing text"),
    ])
    def test_non_numeric_amount_returns_200(self, client, app, bad_amount, label):
        """Non-numeric amount values must trigger form re-render (200)."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "amount": bad_amount}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            f"Non-numeric amount '{label}' ({bad_amount!r}) must fail validation (200)"
        )

    @pytest.mark.parametrize("bad_amount,label", [
        ("abc",    "alphabetic string"),
        ("twelve", "English word"),
        ("12.3.4", "malformed decimal"),
    ])
    def test_non_numeric_amount_shows_error_message(self, client, app, bad_amount, label):
        """Non-numeric amount must include an error message in the response body."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "amount": bad_amount}
        resp = client.post("/expenses/add", data=payload)
        body = resp.get_data(as_text=True)
        has_error = (
            "valid" in body.lower()
            or "number" in body.lower()
            or "amount" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            f"Non-numeric amount '{label}' must produce an error message in the response"
        )

    def test_non_numeric_amount_inserts_no_row(self, client, app):
        """A non-numeric amount must not write any row to the DB."""
        user_id = _demo_user_id()
        _login_demo(client)
        count_before = _expense_count(user_id)
        payload = {**SPEC_PAYLOAD, "amount": "not-a-number"}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before, (
            "Non-numeric amount POST must not insert any expense row"
        )


class TestPostAddExpenseInvalidCategory:
    """Validation failure tests when category is not in the fixed list."""

    def test_invalid_category_returns_200(self, client, app):
        """POST with a category not in the fixed list must re-render the form (200)."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "category": "Groceries"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            "An invalid category must fail validation and re-render the form (200)"
        )

    def test_invalid_category_shows_error_message(self, client, app):
        """POST with an invalid category must include an error message in the response."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "category": "Groceries"}
        resp = client.post("/expenses/add", data=payload)
        body = resp.get_data(as_text=True)
        has_error = (
            "category" in body.lower()
            or "valid" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Invalid category POST must produce an error message in the response body"
        )

    def test_empty_category_returns_200(self, client, app):
        """POST with category='' (empty string) must also fail validation (200)."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "category": ""}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            "Empty category must fail validation and re-render (200)"
        )

    @pytest.mark.parametrize("bad_category", [
        "Groceries",
        "Rent",
        "Utilities",
        "FOOD",           # wrong case
        "food",           # lowercase
        "Food ",          # trailing space
        " Food",          # leading space
        "InvalidCat",
        "",
        "NULL",
        "'; DROP TABLE expenses; --",  # SQL injection attempt
    ])
    def test_categories_outside_fixed_list_rejected(self, client, app, bad_category):
        """Every category value not in the fixed list must be rejected (200)."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "category": bad_category}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            f"Category {bad_category!r} is not in the fixed list and must fail (200)"
        )

    def test_invalid_category_inserts_no_row(self, client, app):
        """An invalid category POST must not write any row to the DB."""
        user_id = _demo_user_id()
        _login_demo(client)
        count_before = _expense_count(user_id)
        payload = {**SPEC_PAYLOAD, "category": "NotACategory"}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before, (
            "Invalid category POST must not insert any expense row"
        )


class TestPostAddExpenseInvalidDate:
    """Validation failure tests when the date field is not a valid YYYY-MM-DD string."""

    @pytest.mark.parametrize("bad_date,label", [
        ("25-03-2026",  "DD-MM-YYYY format"),
        ("03/20/2026",  "MM/DD/YYYY format"),
        ("not-a-date",  "arbitrary string"),
        ("2026-13-01",  "month 13 (out of range)"),
        ("2026-00-10",  "month 00 (out of range)"),
        ("2026-03-00",  "day 00 (out of range)"),
        ("2026-03-32",  "day 32 (out of range)"),
        ("20260320",    "YYYYMMDD no separators"),
        ("",            "empty string"),
    ])
    def test_invalid_date_returns_200(self, client, app, bad_date, label):
        """Any invalid date string must cause form re-render (200)."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "date": bad_date}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            f"Invalid date '{label}' ({bad_date!r}) must fail validation and re-render (200)"
        )

    def test_invalid_date_shows_error_message(self, client, app):
        """An invalid date submission must include an error message in the response body."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "date": "not-a-date"}
        resp = client.post("/expenses/add", data=payload)
        body = resp.get_data(as_text=True)
        has_error = (
            "date" in body.lower()
            or "valid" in body.lower()
            or "error" in body.lower()
        )
        assert has_error, (
            "Invalid date POST must produce an error message referencing the date field"
        )

    def test_invalid_date_inserts_no_row(self, client, app):
        """An invalid date POST must not write any row to the DB."""
        user_id = _demo_user_id()
        _login_demo(client)
        count_before = _expense_count(user_id)
        payload = {**SPEC_PAYLOAD, "date": "not-a-date"}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before, (
            "Invalid date POST must not insert any expense row"
        )


class TestPostAddExpenseOptionalDescription:
    """Tests for the optional description field behaviour."""

    def test_omitted_description_redirects_to_profile(self, client, app):
        """POST without a description field must redirect to /profile (302)."""
        _login_demo(client)
        payload = {k: v for k, v in SPEC_PAYLOAD.items() if k != "description"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 302, (
            "Omitting description must be valid; expect 302 redirect"
        )
        location = resp.headers.get("Location", "")
        assert "/profile" in location, (
            f"Omitting description must redirect to /profile, got '{location}'"
        )

    def test_omitted_description_inserts_row_with_null_description(self, client, app):
        """When description is omitted, the inserted row must have description = NULL."""
        user_id = _demo_user_id()
        _login_demo(client)
        payload = {k: v for k, v in SPEC_PAYLOAD.items() if k != "description"}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None, "Expected a new expense row when description is omitted"
        assert row["description"] is None, (
            "An omitted description field must be stored as NULL in the DB"
        )

    def test_empty_description_redirects_to_profile(self, client, app):
        """POST with description='' (blank) must redirect to /profile (302)."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "description": ""}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 302, (
            "Blank description must be treated as valid; expect 302 redirect"
        )
        location = resp.headers.get("Location", "")
        assert "/profile" in location, (
            f"Blank description must redirect to /profile, got '{location}'"
        )

    def test_empty_description_stored_as_null(self, client, app):
        """POST with description='' must store NULL in the DB, not an empty string."""
        user_id = _demo_user_id()
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "description": ""}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None, "Expected a new expense row for blank description POST"
        assert row["description"] is None, (
            "A blank description must be stored as NULL, not as ''"
        )

    def test_whitespace_only_description_stored_as_null(self, client, app):
        """A description consisting only of whitespace must be stored as NULL."""
        user_id = _demo_user_id()
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "description": "   "}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None, "Expected a new expense row for whitespace description"
        assert row["description"] is None, (
            "Whitespace-only description must be stripped and stored as NULL"
        )

    def test_whitespace_only_description_redirects_to_profile(self, client, app):
        """A whitespace-only description is still optional; must redirect to /profile."""
        _login_demo(client)
        payload = {**SPEC_PAYLOAD, "description": "   "}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 302, (
            "Whitespace-only description must be treated as valid (302 redirect)"
        )
        location = resp.headers.get("Location", "")
        assert "/profile" in location, (
            f"Whitespace-only description must redirect to /profile, got '{location}'"
        )
