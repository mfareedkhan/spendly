"""Tests for Step 7 — GET/POST /expenses/add.

All cases run against the isolated temp database provided by the root-level
`app` fixture in conftest.py (seeded with demo@spendly.com / demo123).
The `client` fixture is auto-provided by pytest-flask.
"""

import pytest
from database.db import get_db, get_user_by_email


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

VALID_PAYLOAD = {
    "amount": "250.00",
    "category": "Food",
    "date": "2026-06-01",
    "description": "Test meal",
}


def _login_demo(client):
    """Log the test client in as the demo user."""
    return client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=False,
    )


def _demo_user_id():
    """Return the demo user's primary key from the temp DB."""
    row = get_user_by_email("demo@spendly.com")
    assert row is not None, "Demo user not found in temp DB — seed_db() may have failed"
    return row["id"]


def _expense_count(user_id):
    """Return the number of expense rows for user_id in the temp DB."""
    con = get_db()
    row = con.execute(
        "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    con.close()
    return row["cnt"]


def _latest_expense(user_id):
    """Return the most recently inserted expense row for user_id, or None."""
    con = get_db()
    row = con.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    con.close()
    return row


# ------------------------------------------------------------------ #
# GET /expenses/add                                                   #
# ------------------------------------------------------------------ #

class TestGetAddExpense:

    def test_get_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/expenses/add", follow_redirects=False)
        assert resp.status_code == 302, "Unauthenticated GET should redirect"
        assert "/login" in resp.headers["Location"], "Redirect target must be /login"

    def test_get_authenticated_returns_200(self, client, app):
        _login_demo(client)
        resp = client.get("/expenses/add")
        assert resp.status_code == 200, "Authenticated GET should return 200"

    def test_get_renders_all_seven_categories(self, client, app):
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        for category in VALID_CATEGORIES:
            assert category in body, f"Category '{category}' missing from form"

    def test_get_renders_form_with_correct_action(self, client, app):
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert "/expenses/add" in body, "Form action URL missing from rendered page"

    def test_get_renders_today_date_in_form(self, client, app):
        from datetime import date
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        today = date.today().isoformat()
        assert today in body, f"Today's date ({today}) should be pre-filled in the date field"

    def test_get_renders_amount_label(self, client, app):
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert "Amount" in body, "Amount label should appear on the form"

    def test_get_renders_description_field(self, client, app):
        _login_demo(client)
        resp = client.get("/expenses/add")
        body = resp.get_data(as_text=True)
        assert "description" in body.lower(), "Description field should appear on the form"


# ------------------------------------------------------------------ #
# POST /expenses/add — auth guard                                     #
# ------------------------------------------------------------------ #

class TestPostAddExpenseAuthGuard:

    def test_post_unauthenticated_redirects_to_login(self, client, app):
        resp = client.post(
            "/expenses/add",
            data=VALID_PAYLOAD,
            follow_redirects=False,
        )
        assert resp.status_code == 302, "Unauthenticated POST should redirect"
        assert "/login" in resp.headers["Location"], "Redirect target must be /login"

    def test_post_unauthenticated_inserts_no_row(self, client, app):
        user_id = _demo_user_id()
        count_before = _expense_count(user_id)
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before, (
            "Unauthenticated POST must not insert any expense row"
        )


# ------------------------------------------------------------------ #
# POST /expenses/add — validation failures                           #
# ------------------------------------------------------------------ #

class TestPostAddExpenseValidation:

    def setup_method(self):
        """Each test starts fresh; login happens inside the test via the client."""

    def test_post_empty_amount_returns_200_with_error(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "amount": ""}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, "Validation failure must re-render (200), not redirect"
        body = resp.get_data(as_text=True)
        assert "required" in body.lower() or "amount" in body.lower(), (
            "Error message should indicate that amount is required"
        )

    def test_post_empty_amount_shows_error_in_template(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "amount": ""}
        resp = client.post("/expenses/add", data=payload)
        body = resp.get_data(as_text=True)
        # Template renders error block only when error is set
        assert "auth-error" in body, "Error CSS class should appear when amount is missing"

    @pytest.mark.parametrize("bad_amount,label", [
        ("abc",    "non-numeric string"),
        ("12.3.4", "malformed decimal"),
        ("one",    "word instead of number"),
        ("",       "empty string"),
    ])
    def test_post_non_numeric_amount_returns_200(self, client, app, bad_amount, label):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "amount": bad_amount}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            f"Amount '{label}' should trigger re-render (200), not redirect"
        )

    def test_post_amount_zero_returns_200_with_error(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "amount": "0"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, "Amount = 0 must fail validation"
        body = resp.get_data(as_text=True)
        assert "zero" in body.lower() or "greater" in body.lower(), (
            "Error should mention that amount must be greater than zero"
        )

    def test_post_amount_zero_float_returns_200(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "amount": "0.00"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, "Amount 0.00 must fail validation"

    def test_post_negative_amount_returns_200_with_error(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "amount": "-50"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, "Negative amount must fail validation"
        body = resp.get_data(as_text=True)
        assert "zero" in body.lower() or "greater" in body.lower(), (
            "Error should mention that amount must be greater than zero"
        )

    def test_post_invalid_category_returns_200_with_error(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "category": "InvalidCat"}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, "Invalid category must fail validation"
        body = resp.get_data(as_text=True)
        assert "category" in body.lower(), (
            "Error message should mention category validation failure"
        )

    def test_post_empty_category_returns_200_with_error(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "category": ""}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, "Empty category must fail validation"

    def test_post_empty_date_returns_200_with_error(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "date": ""}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, "Empty date must fail validation"
        body = resp.get_data(as_text=True)
        assert "date" in body.lower(), "Error message should reference date field"

    @pytest.mark.parametrize("bad_date,label", [
        ("25-06-2026",  "DD-MM-YYYY format"),
        ("06/25/2026",  "MM/DD/YYYY format"),
        ("not-a-date",  "random string"),
        ("2026-13-01",  "month 13"),
        ("2026-00-10",  "month 00"),
    ])
    def test_post_malformed_date_returns_200(self, client, app, bad_date, label):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "date": bad_date}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 200, (
            f"Date '{label}' ({bad_date!r}) should fail validation and re-render"
        )

    def test_post_validation_failure_repopulates_form_fields(self, client, app):
        """On error the form must echo back the submitted values so the user
        does not have to retype everything."""
        _login_demo(client)
        payload = {
            "amount": "99.99",
            "category": "Health",
            "date": "2026-06-01",
            "description": "Doctor visit",
            "date_bad": "",  # intentionally omit correct date; use separate bad post below
        }
        # Trigger a validation error on amount = 0 while other fields are valid
        bad_payload = {**VALID_PAYLOAD, "amount": "0", "description": "Doctor visit"}
        resp = client.post("/expenses/add", data=bad_payload)
        body = resp.get_data(as_text=True)
        # The submitted description and category should appear in the re-rendered form
        assert "Doctor visit" in body, "Description should be echoed back on validation error"
        assert "Food" in body, "Category should be echoed back on validation error"

    def test_post_validation_failure_inserts_no_row(self, client, app):
        """A failed validation must not write anything to the DB."""
        user_id = _demo_user_id()
        _login_demo(client)
        count_before = _expense_count(user_id)
        client.post("/expenses/add", data={**VALID_PAYLOAD, "amount": "0"})
        count_after = _expense_count(user_id)
        assert count_after == count_before, (
            "Validation failure must not insert any expense row"
        )


# ------------------------------------------------------------------ #
# POST /expenses/add — success paths                                 #
# ------------------------------------------------------------------ #

class TestPostAddExpenseSuccess:

    def test_post_valid_redirects_to_profile(self, client, app):
        _login_demo(client)
        resp = client.post(
            "/expenses/add",
            data=VALID_PAYLOAD,
            follow_redirects=False,
        )
        assert resp.status_code == 302, "Successful POST must redirect (302)"
        assert "/profile" in resp.headers["Location"], (
            "Successful POST must redirect to /profile"
        )

    def test_post_valid_flash_message_present(self, client, app):
        _login_demo(client)
        resp = client.post(
            "/expenses/add",
            data=VALID_PAYLOAD,
            follow_redirects=True,
        )
        body = resp.get_data(as_text=True)
        assert "Expense added" in body, (
            "Flash message 'Expense added.' should appear after successful POST"
        )

    def test_post_valid_inserts_row_in_db(self, client, app):
        user_id = _demo_user_id()
        count_before = _expense_count(user_id)
        _login_demo(client)
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        count_after = _expense_count(user_id)
        assert count_after == count_before + 1, (
            "Successful POST must insert exactly one expense row for the user"
        )

    def test_post_valid_row_has_correct_amount(self, client, app):
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None, "Expected a new expense row in the DB"
        assert row["amount"] == pytest.approx(250.00), (
            "Stored amount should match the submitted value"
        )

    def test_post_valid_row_has_correct_category(self, client, app):
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row["category"] == "Food", "Stored category must match submitted value"

    def test_post_valid_row_has_correct_date(self, client, app):
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row["date"] == "2026-06-01", "Stored date must match submitted value"

    def test_post_valid_row_has_correct_description(self, client, app):
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row["description"] == "Test meal", (
            "Stored description must match the submitted value"
        )

    def test_post_valid_row_belongs_to_correct_user(self, client, app):
        user_id = _demo_user_id()
        _login_demo(client)
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row["user_id"] == user_id, (
            "Inserted expense must be associated with the logged-in user"
        )

    def test_post_blank_description_stored_as_null(self, client, app):
        user_id = _demo_user_id()
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "description": ""}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None, "Expected a new expense row in the DB"
        assert row["description"] is None, (
            "A blank description field must be stored as NULL, not an empty string"
        )

    def test_post_blank_description_still_redirects_to_profile(self, client, app):
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "description": ""}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 302, "Blank description is valid; must redirect"
        assert "/profile" in resp.headers["Location"]

    def test_post_whitespace_only_description_stored_as_null(self, client, app):
        """A description that is only whitespace should be stored as NULL."""
        user_id = _demo_user_id()
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "description": "   "}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None, "Expected a new expense row in the DB"
        assert row["description"] is None, (
            "Whitespace-only description should be stored as NULL"
        )

    @pytest.mark.parametrize("category", VALID_CATEGORIES)
    def test_post_each_valid_category_is_accepted(self, client, app, category):
        """Every category in the CATEGORIES constant must be accepted."""
        user_id = _demo_user_id()
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "category": category}
        resp = client.post("/expenses/add", data=payload, follow_redirects=False)
        assert resp.status_code == 302, (
            f"Category '{category}' should be accepted (302), got {resp.status_code}"
        )
        row = _latest_expense(user_id)
        assert row["category"] == category, (
            f"Stored category should be '{category}'"
        )

    def test_post_valid_fractional_amount_stored_correctly(self, client, app):
        """Amounts with decimal places must round-trip through the DB intact."""
        user_id = _demo_user_id()
        _login_demo(client)
        payload = {**VALID_PAYLOAD, "amount": "1234.56"}
        client.post("/expenses/add", data=payload, follow_redirects=False)
        row = _latest_expense(user_id)
        assert row is not None
        assert row["amount"] == pytest.approx(1234.56), (
            "Fractional amount must be stored accurately"
        )

    def test_post_multiple_expenses_all_inserted(self, client, app):
        """Posting twice should result in two new rows for the user."""
        user_id = _demo_user_id()
        count_before = _expense_count(user_id)
        _login_demo(client)
        client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=False)
        client.post(
            "/expenses/add",
            data={**VALID_PAYLOAD, "amount": "99", "category": "Transport"},
            follow_redirects=False,
        )
        count_after = _expense_count(user_id)
        assert count_after == count_before + 2, (
            "Two successful POSTs must result in exactly two new expense rows"
        )
