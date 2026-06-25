"""Tests for Step 6 — Date Filter for the Profile Page.

All cases run against an isolated SQLite temp DB (one per test function)
via the shared `app` fixture in the root conftest.py.

The seeded demo user (demo@spendly.com / demo123) comes with 8 expenses
all dated within May 2026 (2026-05-01 through 2026-05-22).  Tests that
need deterministic filter results rely on those fixed dates or insert
additional rows via get_db() directly.

Seed data summary (from db.py seed_db):
  2026-05-01  Food         450.00
  2026-05-03  Bills       3200.00
  2026-05-05  Transport    600.00
  2026-05-08  Shopping    4500.00
  2026-05-10  Entertainment 1200.00
  2026-05-14  Health       850.00
  2026-05-18  Food        2800.00
  2026-05-22  Entertainment 1100.00
  Total: 14700.00  (8 transactions)
"""

import pytest
from datetime import date
from database.db import get_db, get_user_by_email


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _login_demo(client):
    """Log the test client in as the demo user; follows redirect silently."""
    client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=False,
    )


def _demo_user_id():
    """Return the demo user's primary key from the temp DB."""
    row = get_user_by_email("demo@spendly.com")
    assert row is not None, "Demo user not found — seed_db() may have failed"
    return row["id"]


def _insert_expense(user_id, amount, category, date_str, description=None):
    """Insert a single expense row directly into the temp DB."""
    con = get_db()
    con.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_str, description),
    )
    con.commit()
    con.close()


def _profile(client, **params):
    """GET /profile with optional query params; returns Response."""
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = "/profile" + (f"?{query}" if query else "")
    return client.get(url)


# ------------------------------------------------------------------ #
# Case 21 — Auth guard (no login required context)                   #
# ------------------------------------------------------------------ #

class TestAuthGuard:

    def test_unauthenticated_get_profile_redirects_to_login(self, client, app):
        """Unauthenticated GET /profile must redirect to /login (auth guard unchanged)."""
        resp = client.get("/profile", follow_redirects=False)
        assert resp.status_code == 302, (
            "Unauthenticated /profile must return 302, not 200"
        )
        assert "/login" in resp.headers["Location"], (
            "Redirect must point to /login"
        )

    def test_unauthenticated_with_date_params_still_redirects(self, client, app):
        """Auth guard must fire even when date filter params are present."""
        resp = client.get(
            "/profile?date_from=2026-05-01&date_to=2026-05-31",
            follow_redirects=False,
        )
        assert resp.status_code == 302, (
            "Unauthenticated request with date params must still redirect"
        )
        assert "/login" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# Case 1 — Unfiltered baseline                                        #
# ------------------------------------------------------------------ #

class TestUnfilteredBaseline:

    def test_no_params_returns_200(self, client, app):
        """GET /profile with no params returns 200."""
        _login_demo(client)
        resp = _profile(client)
        assert resp.status_code == 200, "Unfiltered /profile must return 200"

    def test_no_params_total_includes_all_expenses(self, client, app):
        """With no filter, total_spent must equal the sum of all seeded expenses (14700)."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        # Seed total is 14,700.00; template formats as "Rs 14,700.00"
        assert "14,700.00" in body, (
            "Unfiltered total must include all seeded expenses (14,700.00)"
        )

    def test_no_params_transaction_count_is_eight(self, client, app):
        """With no filter, all 8 seeded transactions must appear."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        # Each transaction row contains a date; count occurrences of "May 2026"
        # (all 8 seeded expenses fall in May 2026)
        assert body.count("May 2026") >= 8, (
            "All 8 seeded transactions (all in May 2026) must appear unfiltered"
        )

    def test_no_params_user_name_present(self, client, app):
        """Unfiltered profile page must still show the user's name."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "Ahmed Khan" in body, "User name must appear on unfiltered profile page"


# ------------------------------------------------------------------ #
# Case 2 — Filter bar rendered                                        #
# ------------------------------------------------------------------ #

class TestFilterBarRendering:

    def test_filter_bar_section_present(self, client, app):
        """The filter bar section must be rendered on GET /profile."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "filter-bar" in body, (
            "filter-bar section must be present in the rendered HTML"
        )

    def test_filter_bar_has_this_month_button(self, client, app):
        """The filter bar must contain a 'This Month' preset link."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "This Month" in body, "'This Month' preset text must appear in filter bar"

    def test_filter_bar_has_last_3_months_button(self, client, app):
        """The filter bar must contain a 'Last 3 Months' preset link."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "Last 3 Months" in body, "'Last 3 Months' preset text must appear in filter bar"

    def test_filter_bar_has_last_6_months_button(self, client, app):
        """The filter bar must contain a 'Last 6 Months' preset link."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "Last 6 Months" in body, "'Last 6 Months' preset text must appear in filter bar"

    def test_filter_bar_has_all_time_button(self, client, app):
        """The filter bar must contain an 'All Time' preset link."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "All Time" in body, "'All Time' preset text must appear in filter bar"


# ------------------------------------------------------------------ #
# Case 3 — "All Time" active when no params                          #
# ------------------------------------------------------------------ #

class TestAllTimeActiveState:

    def test_all_time_button_has_active_class_when_no_params(self, client, app):
        """When no date params are provided, 'All Time' must have filter-btn--active."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        # The "All Time" anchor and the active class must appear together
        all_time_block = body[body.rfind("All Time") - 200 : body.rfind("All Time") + 20]
        assert "filter-btn--active" in all_time_block, (
            "'All Time' button must carry filter-btn--active class when no filter is active"
        )

    def test_preset_buttons_do_not_have_active_class_when_no_params(self, client, app):
        """When no date params are given, only 'All Time' should be active.

        We count occurrences of filter-btn--active — exactly one expected.
        """
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        active_count = body.count("filter-btn--active")
        assert active_count == 1, (
            f"Exactly one filter-btn--active expected when unfiltered, found {active_count}"
        )


# ------------------------------------------------------------------ #
# Cases 4, 5, 6, 7 — Valid date range filter                         #
# ------------------------------------------------------------------ #

class TestValidDateRangeFilter:

    def test_valid_range_returns_200(self, client, app):
        """A valid date_from + date_to query string must return 200."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-10")
        assert resp.status_code == 200, "Valid date range must return 200"

    def test_valid_range_stats_reflect_only_ranged_expenses(self, client, app):
        """Stats (total_spent) must include only expenses within the date range.

        Expenses from 2026-05-01 to 2026-05-10 (inclusive):
          450 + 3200 + 600 + 4500 + 1200 = 9950.00
        """
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-10")
        body = resp.get_data(as_text=True)
        assert "9,950.00" in body, (
            "Total for 2026-05-01 to 2026-05-10 must be Rs 9,950.00"
        )

    def test_valid_range_excludes_expenses_outside_range(self, client, app):
        """Transactions outside the date range must not appear in the table."""
        _login_demo(client)
        # Filter to first 5 days only; 2026-05-14 expense (Health/850) is outside
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-10")
        body = resp.get_data(as_text=True)
        assert "14 May 2026" not in body, (
            "Expense on 2026-05-14 must not appear when filtered to 2026-05-01..2026-05-10"
        )
        assert "22 May 2026" not in body, (
            "Expense on 2026-05-22 must not appear when filtered to 2026-05-01..2026-05-10"
        )

    def test_valid_range_includes_boundary_dates(self, client, app):
        """The filter is inclusive on both bounds — boundary dates must appear."""
        _login_demo(client)
        # date_from = 2026-05-01; there IS an expense on 2026-05-01
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-05")
        body = resp.get_data(as_text=True)
        assert "01 May 2026" in body, (
            "Expense on lower bound date (2026-05-01) must be included"
        )
        assert "05 May 2026" in body, (
            "Expense on upper bound date (2026-05-05) must be included"
        )

    def test_valid_range_transaction_count_matches(self, client, app):
        """transaction_count in stats must match rows in the filtered range.

        2026-05-01 to 2026-05-05 yields 3 transactions (01-May, 03-May, 05-May).
        """
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-05")
        body = resp.get_data(as_text=True)
        # The stats section shows "Transactions" then the count; check for "3"
        # We look for the digit in the context of the stat value
        # A simple check: "3" appears AND the unfiltered count "8" is not the displayed value.
        # We verify the total value instead, which is more deterministic.
        # 450 + 3200 + 600 = 4250.00
        assert "4,250.00" in body, (
            "Stats total for 2026-05-01..2026-05-05 must be Rs 4,250.00 (3 transactions)"
        )

    def test_valid_range_category_breakdown_scoped(self, client, app):
        """Category breakdown must reflect only expenses within the filtered range."""
        _login_demo(client)
        # Filter to one day that has only Food (450.00 on 2026-05-01)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-01")
        body = resp.get_data(as_text=True)
        # Only Food should appear in breakdown; Bills must not
        # Check that total is 450 (only the Food expense)
        assert "450.00" in body, (
            "Category breakdown must be scoped to the filtered date range"
        )
        # Entertainment and Shopping expenses were after 2026-05-01
        assert "4,500.00" not in body, (
            "Shopping expense (4500.00) must not appear when filtered to 2026-05-01 only"
        )

    def test_valid_range_rs_symbol_present_in_stats(self, client, app):
        """The Rs symbol must appear in the filtered stats section (Case 22)."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-10")
        body = resp.get_data(as_text=True)
        assert "Rs" in body, "Rs currency symbol must appear even with an active date filter"

    def test_valid_range_rs_symbol_present_in_transactions(self, client, app):
        """The Rs symbol must appear in each filtered transaction row."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-05")
        body = resp.get_data(as_text=True)
        # At least 3 Rs occurrences: stat card + 3 transaction rows
        assert body.count("Rs") >= 4, (
            "Rs symbol must appear in the stats and in each transaction row"
        )


# ------------------------------------------------------------------ #
# Case 8, 9 — date_from > date_to (reversed range)                  #
# ------------------------------------------------------------------ #

class TestReversedDateRange:

    def test_reversed_range_returns_200(self, client, app):
        """date_from > date_to must return 200 (not 400 or 500)."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-31", date_to="2026-05-01")
        assert resp.status_code == 200, (
            "Reversed date range must return 200, not an error status"
        )

    def test_reversed_range_flashes_error_message(self, client, app):
        """date_from > date_to must produce a flash: 'Start date must be before end date.'"""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-31", date_to="2026-05-01")
        body = resp.get_data(as_text=True)
        assert "Start date must be before end date" in body, (
            "Flash message 'Start date must be before end date.' must appear "
            "when date_from > date_to"
        )

    def test_reversed_range_falls_back_to_all_expenses(self, client, app):
        """With a reversed range the page must show the unfiltered total (14700)."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-31", date_to="2026-05-01")
        body = resp.get_data(as_text=True)
        assert "14,700.00" in body, (
            "Reversed range must fall back to unfiltered view (total 14,700.00)"
        )

    def test_reversed_range_does_not_activate_any_preset(self, client, app):
        """After reversal fallback to unfiltered, 'All Time' must be the active preset."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-31", date_to="2026-05-01")
        body = resp.get_data(as_text=True)
        # Expect exactly one active button — All Time
        assert body.count("filter-btn--active") == 1, (
            "Only one preset (All Time) should be active after reversed-range fallback"
        )


# ------------------------------------------------------------------ #
# Cases 10, 11, 12 — Malformed date values                           #
# ------------------------------------------------------------------ #

class TestMalformedDates:

    @pytest.mark.parametrize("bad_from,label", [
        ("abc",         "arbitrary string"),
        ("not-a-date",  "english words"),
        ("25-05-2026",  "DD-MM-YYYY format"),
        ("05/25/2026",  "MM/DD/YYYY format"),
        ("2026-13-01",  "invalid month"),
        ("2026-00-01",  "month zero"),
        ("9999-99-99",  "all-nines"),
        ("",            "empty string (explicit)"),
    ])
    def test_malformed_date_from_does_not_crash(self, client, app, bad_from, label):
        """Any malformed date_from must return 200, not 500."""
        _login_demo(client)
        resp = client.get(f"/profile?date_from={bad_from}")
        assert resp.status_code == 200, (
            f"Malformed date_from '{label}' ({bad_from!r}) must not crash the app"
        )

    @pytest.mark.parametrize("bad_to,label", [
        ("abc",         "arbitrary string"),
        ("not-a-date",  "english words"),
        ("2026-13-01",  "invalid month"),
        ("2026-00-01",  "month zero"),
    ])
    def test_malformed_date_to_does_not_crash(self, client, app, bad_to, label):
        """Any malformed date_to must return 200, not 500."""
        _login_demo(client)
        resp = client.get(f"/profile?date_to={bad_to}")
        assert resp.status_code == 200, (
            f"Malformed date_to '{label}' ({bad_to!r}) must not crash the app"
        )

    def test_malformed_date_from_shows_all_expenses(self, client, app):
        """A malformed date_from must silently fall back to the unfiltered view."""
        _login_demo(client)
        resp = client.get("/profile?date_from=not-a-date")
        body = resp.get_data(as_text=True)
        assert "14,700.00" in body, (
            "Malformed date_from must fall back to unfiltered total (14,700.00)"
        )

    def test_malformed_date_to_shows_all_expenses(self, client, app):
        """A malformed date_to must silently fall back to the unfiltered view."""
        _login_demo(client)
        resp = client.get("/profile?date_to=not-a-date")
        body = resp.get_data(as_text=True)
        assert "14,700.00" in body, (
            "Malformed date_to must fall back to unfiltered total (14,700.00)"
        )

    def test_both_params_malformed_shows_all_expenses(self, client, app):
        """When both date params are malformed the app must not crash and must show all data."""
        _login_demo(client)
        resp = client.get("/profile?date_from=bad&date_to=also-bad")
        assert resp.status_code == 200, (
            "Both params malformed must still return 200"
        )
        body = resp.get_data(as_text=True)
        assert "14,700.00" in body, (
            "Both params malformed must fall back to unfiltered total (14,700.00)"
        )

    def test_malformed_dates_do_not_show_flash_error(self, client, app):
        """Malformed dates are silently ignored — no flash error message expected."""
        _login_demo(client)
        resp = client.get("/profile?date_from=abc&date_to=xyz")
        body = resp.get_data(as_text=True)
        assert "Start date must be before end date" not in body, (
            "Malformed dates must not trigger the reversed-range flash error"
        )


# ------------------------------------------------------------------ #
# Cases 13, 14 — Only one param provided                             #
# ------------------------------------------------------------------ #

class TestPartialParams:

    def test_only_date_from_falls_back_to_unfiltered(self, client, app):
        """When only date_from is provided (no date_to), show unfiltered view."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-10")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "14,700.00" in body, (
            "Only date_from (no date_to) must fall back to unfiltered total (14,700.00)"
        )

    def test_only_date_to_falls_back_to_unfiltered(self, client, app):
        """When only date_to is provided (no date_from), show unfiltered view."""
        _login_demo(client)
        resp = _profile(client, date_to="2026-05-10")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "14,700.00" in body, (
            "Only date_to (no date_from) must fall back to unfiltered total (14,700.00)"
        )

    def test_only_date_from_returns_200(self, client, app):
        """Only date_from provided must return 200, not an error."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01")
        assert resp.status_code == 200

    def test_only_date_to_returns_200(self, client, app):
        """Only date_to provided must return 200, not an error."""
        _login_demo(client)
        resp = _profile(client, date_to="2026-05-31")
        assert resp.status_code == 200


# ------------------------------------------------------------------ #
# Case 15 — Date range with zero matching expenses                    #
# ------------------------------------------------------------------ #

class TestEmptyDateRange:

    def test_range_with_no_expenses_returns_200(self, client, app):
        """A valid date range that matches no expenses must still return 200."""
        _login_demo(client)
        # Use a date range that is before all seeded expenses (all in May 2026)
        resp = _profile(client, date_from="2025-01-01", date_to="2025-01-31")
        assert resp.status_code == 200, (
            "A date range with zero matching expenses must return 200"
        )

    def test_range_with_no_expenses_shows_zero_total(self, client, app):
        """When no expenses fall in the range, total_spent must be Rs 0.00."""
        _login_demo(client)
        resp = _profile(client, date_from="2025-01-01", date_to="2025-01-31")
        body = resp.get_data(as_text=True)
        assert "0.00" in body, (
            "Date range with no matching expenses must show Rs 0.00 total"
        )

    def test_range_with_no_expenses_shows_rs_symbol(self, client, app):
        """The Rs symbol must still appear even when the filtered total is Rs 0.00."""
        _login_demo(client)
        resp = _profile(client, date_from="2025-01-01", date_to="2025-01-31")
        body = resp.get_data(as_text=True)
        assert "Rs" in body, (
            "Rs symbol must appear even when the filtered total is Rs 0.00"
        )

    def test_range_with_no_expenses_has_no_may_2026_transactions(self, client, app):
        """Transaction rows for May 2026 must not appear in an empty-range response."""
        _login_demo(client)
        resp = _profile(client, date_from="2025-01-01", date_to="2025-01-31")
        body = resp.get_data(as_text=True)
        assert "May 2026" not in body, (
            "No May 2026 transactions must appear in a 2025 date range filter"
        )

    def test_future_date_range_returns_200_without_crash(self, client, app):
        """A future date range with no data must not raise any exception."""
        _login_demo(client)
        resp = _profile(client, date_from="2099-01-01", date_to="2099-12-31")
        assert resp.status_code == 200, (
            "Future date range with no data must return 200 without crashing"
        )


# ------------------------------------------------------------------ #
# Cases 16, 17, 18 — Preset links in HTML                            #
# ------------------------------------------------------------------ #

class TestPresetLinks:

    def test_this_month_link_has_date_from_param(self, client, app):
        """'This Month' preset link must include a date_from query parameter."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        # The link for "This Month" is rendered by url_for and includes date_from
        # We check that the first day of the current month appears as a link param
        first_of_month = date.today().replace(day=1).isoformat()
        assert first_of_month in body, (
            f"'This Month' link must contain date_from={first_of_month}"
        )

    def test_this_month_link_has_today_as_date_to(self, client, app):
        """'This Month' preset link must include date_to=today."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        today_iso = date.today().isoformat()
        assert today_iso in body, (
            f"'This Month' link must contain date_to={today_iso}"
        )

    def test_this_month_preset_link_uses_profile_route(self, client, app):
        """'This Month' anchor href must point to /profile (not a hardcoded path)."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        # The anchor must lead to /profile with query params
        # We check the rendered href contains /profile?
        assert "/profile?" in body, (
            "Preset anchor href must use the /profile route with query params"
        )

    def test_last_3_months_link_present(self, client, app):
        """'Last 3 Months' link must be rendered in the filter bar."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "Last 3 Months" in body, (
            "'Last 3 Months' preset link text must appear in the filter bar"
        )

    def test_last_6_months_link_present(self, client, app):
        """'Last 6 Months' link must be rendered in the filter bar."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "Last 6 Months" in body, (
            "'Last 6 Months' preset link text must appear in the filter bar"
        )

    def test_all_time_link_goes_to_clean_profile_url(self, client, app):
        """'All Time' must render as a plain /profile link (no query params)."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        # The "All Time" anchor should point to /profile without query params.
        # url_for("profile") with no args produces exactly /profile.
        # We look for the pattern: href="/profile" followed shortly by "All Time"
        all_time_idx = body.find("All Time")
        assert all_time_idx != -1, "'All Time' text not found in page"
        # Extract the 300 chars before "All Time" to find the href
        surrounding = body[max(0, all_time_idx - 300): all_time_idx + 20]
        assert 'href="/profile"' in surrounding, (
            "'All Time' link must point to /profile with no query params"
        )


# ------------------------------------------------------------------ #
# Case 19 — Custom date range form                                   #
# ------------------------------------------------------------------ #

class TestCustomDateRangeForm:

    def test_custom_form_has_date_from_input(self, client, app):
        """The custom range form must have an input named 'date_from'."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert 'name="date_from"' in body, (
            "Custom range form must include an input with name='date_from'"
        )

    def test_custom_form_has_date_to_input(self, client, app):
        """The custom range form must have an input named 'date_to'."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert 'name="date_to"' in body, (
            "Custom range form must include an input with name='date_to'"
        )

    def test_custom_form_has_apply_button(self, client, app):
        """The custom range form must have an Apply submit button."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "Apply" in body, (
            "Custom range form must include an Apply submit button"
        )

    def test_custom_form_inputs_are_type_date(self, client, app):
        """Custom range inputs must use type='date' for native date pickers."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert 'type="date"' in body, (
            "Custom range form inputs must be of type='date'"
        )

    def test_custom_form_submits_via_get(self, client, app):
        """The custom range form must use method='GET' so params appear in the URL."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert 'method="GET"' in body or "method=GET" in body, (
            "Custom date range form must use GET method"
        )

    def test_custom_form_echoes_back_date_from_value(self, client, app):
        """After a valid filter request the date_from input must be pre-filled."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-10")
        body = resp.get_data(as_text=True)
        assert "2026-05-01" in body, (
            "The date_from input must echo back the submitted date_from value"
        )

    def test_custom_form_echoes_back_date_to_value(self, client, app):
        """After a valid filter request the date_to input must be pre-filled."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-10")
        body = resp.get_data(as_text=True)
        assert "2026-05-10" in body, (
            "The date_to input must echo back the submitted date_to value"
        )


# ------------------------------------------------------------------ #
# Case 20 — Active preset button CSS class                           #
# ------------------------------------------------------------------ #

class TestActivePresetState:

    def test_all_time_active_when_no_filter(self, client, app):
        """When no filter is active, only 'All Time' must carry filter-btn--active."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "filter-btn--active" in body, (
            "filter-btn--active must appear on the active preset"
        )
        # "All Time" and active class should be close together
        all_time_idx = body.find("All Time")
        surrounding = body[max(0, all_time_idx - 200): all_time_idx + 20]
        assert "filter-btn--active" in surrounding, (
            "'All Time' button must be the one carrying filter-btn--active when unfiltered"
        )

    def test_this_month_active_when_this_month_selected(self, client, app):
        """When date_from/date_to match 'This Month', that button must be active."""
        _login_demo(client)
        first_of_month = date.today().replace(day=1).isoformat()
        today_iso = date.today().isoformat()
        resp = _profile(client, date_from=first_of_month, date_to=today_iso)
        body = resp.get_data(as_text=True)
        # Find "This Month" and check surrounding markup for the active class
        this_month_idx = body.find("This Month")
        assert this_month_idx != -1, "'This Month' text not found"
        surrounding = body[max(0, this_month_idx - 200): this_month_idx + 20]
        assert "filter-btn--active" in surrounding, (
            "'This Month' button must carry filter-btn--active when its range is active"
        )

    def test_inactive_presets_lack_active_class_when_this_month_selected(self, client, app):
        """Exactly one preset must be active at a time (This Month selected scenario)."""
        _login_demo(client)
        first_of_month = date.today().replace(day=1).isoformat()
        today_iso = date.today().isoformat()
        resp = _profile(client, date_from=first_of_month, date_to=today_iso)
        body = resp.get_data(as_text=True)
        active_count = body.count("filter-btn--active")
        assert active_count == 1, (
            f"Exactly one preset must have filter-btn--active when 'This Month' is selected, "
            f"found {active_count}"
        )

    def test_no_preset_active_for_custom_date_range(self, client, app):
        """A custom date range that matches no preset must have zero active preset buttons."""
        _login_demo(client)
        # Use a known arbitrary range that is not any preset
        resp = _profile(client, date_from="2026-05-03", date_to="2026-05-15")
        body = resp.get_data(as_text=True)
        # No preset should be active; filter-btn--active should not appear at all
        # (or appear 0 times)
        active_count = body.count("filter-btn--active")
        assert active_count == 0, (
            f"No preset button should be active for a custom date range, "
            f"found {active_count} occurrences of filter-btn--active"
        )

    def test_all_time_not_active_when_filter_is_applied(self, client, app):
        """'All Time' must NOT be active when a valid date range filter is applied."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-10")
        body = resp.get_data(as_text=True)
        all_time_idx = body.find("All Time")
        assert all_time_idx != -1, "'All Time' text not found in page"
        surrounding = body[max(0, all_time_idx - 200): all_time_idx + 20]
        assert "filter-btn--active" not in surrounding, (
            "'All Time' must not carry filter-btn--active when a date filter is active"
        )


# ------------------------------------------------------------------ #
# Case 22 — Rs symbol always present                                 #
# ------------------------------------------------------------------ #

class TestRsSymbolPresence:

    def test_rs_symbol_present_unfiltered(self, client, app):
        """Rs symbol must appear on the unfiltered profile page."""
        _login_demo(client)
        resp = _profile(client)
        body = resp.get_data(as_text=True)
        assert "Rs" in body, "Rs symbol must appear on the unfiltered profile page"

    def test_rs_symbol_present_with_valid_filter(self, client, app):
        """Rs symbol must appear when a valid date filter is applied."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-01", date_to="2026-05-10")
        body = resp.get_data(as_text=True)
        assert "Rs" in body, "Rs symbol must appear in the filtered profile view"

    def test_rs_symbol_present_with_empty_range(self, client, app):
        """Rs symbol must appear even when no expenses exist in the filtered range."""
        _login_demo(client)
        resp = _profile(client, date_from="2020-01-01", date_to="2020-01-31")
        body = resp.get_data(as_text=True)
        assert "Rs" in body, "Rs symbol must appear even when the filtered total is Rs 0.00"

    def test_rs_symbol_present_after_reversed_range_fallback(self, client, app):
        """Rs symbol must appear after a reversed-range fallback (error + unfiltered)."""
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-31", date_to="2026-05-01")
        body = resp.get_data(as_text=True)
        assert "Rs" in body, (
            "Rs symbol must appear even after a reversed-range fallback"
        )


# ------------------------------------------------------------------ #
# Multi-user isolation                                                #
# ------------------------------------------------------------------ #

class TestMultiUserIsolation:

    def test_date_filter_shows_only_current_users_expenses(self, client, app):
        """The date filter must not expose another user's expenses."""
        from database.db import create_user

        # Create a second user with a single expense in the same date range
        other_id = create_user("Other User", "other@test.com", "pw")
        _insert_expense(
            other_id, 9999.99, "Shopping", "2026-05-05", "Other user expense"
        )

        # Log in as the demo user and filter to include 2026-05-05
        _login_demo(client)
        resp = _profile(client, date_from="2026-05-05", date_to="2026-05-05")
        body = resp.get_data(as_text=True)

        # Other user's unique amount must not appear
        assert "9,999.99" not in body, (
            "Expenses belonging to another user must not appear in the filtered view"
        )
        # Demo user's transport expense on 2026-05-05 (600.00) should appear
        assert "600.00" in body, (
            "Demo user's own expense on 2026-05-05 must appear in the filtered view"
        )
