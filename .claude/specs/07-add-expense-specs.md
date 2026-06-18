# Spec: Add Expense

## Overview
Allow authenticated users to submit new expenses via a form at `/expenses/add`. This step implements both the GET and POST handlers, server-side validation, and the database insert. On success the user is redirected to the profile page.

## Depends on
- Step 01 — Database setup (`expenses` table, `get_db()`)
- Step 03 — Login (`session["user_id"]`)
- Step 05 — Backend connection (`database/queries.py` already exists)

## Routes
- `GET /expenses/add` — render the add expense form — login required
- `POST /expenses/add` — validate and insert the expense, redirect to `/profile` — login required

## Database changes
Add to `database/queries.py`:
- **`insert_expense(user_id, amount, category, date, description)`** — inserts a row into `expenses` using parameterized queries; `description` stores as `NULL` if blank

## Templates
- **Create**: `templates/add_expense.html` extending `base.html`
  - Fields: amount, category (dropdown), date, description (optional textarea)
  - Date field defaults to today's date
  - Re-populates all fields on validation failure
  - Displays flash error messages

- **Modify**: `templates/profile.html` — add an "Add Expense" button linking to `/expenses/add`
- **Modify**: `templates/base.html` — add a navbar link to `/expenses/add` visible only when logged in

## Files to change
- `app.py` — add GET+POST handler for `/expenses/add`
- `database/queries.py` — add `insert_expense()` helper
- `templates/profile.html` — add "Add Expense" button
- `templates/base.html` — add navbar link

## Files to create
- `templates/add_expense.html`

## New dependencies
None.

## Rules for implementation
- Raw `sqlite3` only — no ORMs
- Parameterized queries only — never f-strings in SQL
- Unauthenticated requests redirect to `/login`
- Valid categories (exactly seven): Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Server-side validation:
  - Amount: required, must parse as `float`, must be `> 0`
  - Category: required, must be one of the seven fixed options
  - Date: required, must be valid `YYYY-MM-DD` format via `datetime.strptime()`
  - Description: optional; strip whitespace; store as `NULL` if empty
- On validation failure: re-render form with error message and pre-populated fields — do not redirect
- On success: `flash` confirmation and `redirect` to `url_for("profile")`
- Currency displays as Rs — never £ or $
- CSS variables only — never hardcoded hex values
- All templates extend `base.html`
- Use `url_for()` for every internal link

## Definition of done
- [ ] `GET /expenses/add` renders the form with all fields for logged-in users
- [ ] Unauthenticated access redirects to `/login`
- [ ] Submitting valid data creates a new row in `expenses` and redirects to `/profile`
- [ ] The new expense appears immediately on the profile page
- [ ] Submitting a non-positive amount re-renders the form with an error
- [ ] Submitting an invalid category re-renders the form with an error
- [ ] Submitting an invalid date re-renders the form with an error
- [ ] Blank description stores as `NULL` in the database — not an empty string
- [ ] All form fields are pre-populated when the form re-renders after a validation error
