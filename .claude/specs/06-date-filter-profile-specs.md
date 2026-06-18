# Spec: Date Filter for Profile Page

## Overview
Add a date-range filter to the profile page so users can narrow the transaction history, summary stats, and category breakdown to a specific time window. The filter operates via query parameters — no new routes required.

## Depends on
- Step 05 — Backend connection (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown` must exist)

## Routes
No new routes. The existing `GET /profile` route gains optional query parameters:
- `?date_from=YYYY-MM-DD`
- `?date_to=YYYY-MM-DD`

## Database changes
Update the three query functions in `database/queries.py` to accept optional `date_from` and `date_to` parameters:

- `get_summary_stats(user_id, date_from=None, date_to=None)`
- `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`
- `get_category_breakdown(user_id, date_from=None, date_to=None)`

When both dates are provided, append `AND date BETWEEN ? AND ?` to the existing WHERE clause.

## Templates
- **Modify**: `templates/profile.html` — add a filter bar above the summary stats with:
  - Four preset buttons: "This Month", "Last 3 Months", "Last 6 Months", "All Time"
  - A custom date range form with `date_from` and `date_to` inputs
  - Visual highlighting on the currently active preset or custom range

## Files to change
- `app.py` — read `date_from` and `date_to` from `request.args`; validate with `datetime.strptime()`; pass to query functions
- `database/queries.py` — update the three query functions to accept and apply optional date parameters
- `templates/profile.html` — add the filter bar UI

## Files to create
None.

## New dependencies
None. `datetime` is stdlib.

## Rules for implementation
- Validate dates with `datetime.strptime(value, "%Y-%m-%d")` — silently fall back to unfiltered view on `ValueError`
- If `date_from > date_to`, flash "Start date must be before end date." and revert to unfiltered display
- Malformed dates silently default to showing all expenses — no error page
- All three data sections (stats, transactions, breakdown) must respect the active filter
- Active preset button must be visually highlighted using a CSS class — no inline styles
- CSS variables only — never hardcoded hex values
- Currency as Rs throughout

## Definition of done
- [ ] Visiting `/profile` with no query params shows all expenses (unchanged behaviour)
- [ ] `?date_from=2024-01-01&date_to=2024-01-31` filters all three sections to January 2024
- [ ] "This Month" preset filters to the current calendar month
- [ ] "Last 3 Months" preset filters to the past 3 months
- [ ] "Last 6 Months" preset filters to the past 6 months
- [ ] "All Time" preset removes any active filter
- [ ] Active preset button is visually distinguished
- [ ] `date_from` after `date_to` shows a flash error and falls back to unfiltered view
- [ ] Malformed date strings (e.g. `?date_from=abc`) silently show all expenses
- [ ] Zero results within a date range shows zero totals — no errors
