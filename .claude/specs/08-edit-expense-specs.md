# Spec: Edit Expense

## Overview
Allow authenticated users to modify their own existing expenses. The route pre-populates a form with the current expense data and validates changes before saving. Ownership is enforced at the database level — users cannot edit expenses that belong to other users.

## Depends on
- Step 01 — Database setup (`expenses` table, `get_db()`)
- Step 03 — Login (`session["user_id"]`)
- Step 05 — Backend connection (`database/queries.py`, `get_recent_transactions`)
- Step 07 — Add expense (establishes the form pattern and category list)

## Routes
- `GET /expenses/<int:id>/edit` — render pre-populated edit form — login required
- `POST /expenses/<int:id>/edit` — validate and save changes, redirect to `/profile` — login required

## Database changes
Add to `database/queries.py`:
- **`get_expense_by_id(expense_id, user_id)`** — fetches a single expense row only if it belongs to the given user; returns `None` otherwise
- **`update_expense(expense_id, user_id, amount, category, date, description)`** — issues a parameterized `UPDATE` scoped to both `id` AND `user_id`

Also modify:
- **`get_recent_transactions(user_id, ...)`** — include the `id` column in the returned rows so edit links can be constructed in the template

## Templates
- **Create**: `templates/edit_expense.html` extending `base.html`
  - Same fields as the add form: amount, category dropdown, date, description
  - All fields pre-populated with current expense values
  - Submit button labelled "Save Changes"
  - Displays flash error messages on validation failure

- **Modify**: `templates/profile.html` — add an "Actions" column to the transaction table with an "Edit" link per row pointing to `/expenses/<id>/edit`

## Files to change
- `app.py` — add GET+POST handler for `/expenses/<int:id>/edit`
- `database/queries.py` — add `get_expense_by_id()`, `update_expense()`; update `get_recent_transactions()` to include `id`
- `templates/profile.html` — add Actions column with edit links

## Files to create
- `templates/edit_expense.html`

## New dependencies
None.

## Rules for implementation
- Raw `sqlite3` only — no ORMs
- Parameterized queries only — never f-strings in SQL
- Unauthenticated requests redirect to `/login`
- If expense is not found or belongs to another user → `abort(404)`
- Valid categories (exactly seven): Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Validation rules identical to Step 07 (amount > 0 float, valid category, valid YYYY-MM-DD date, optional description)
- On validation failure: re-render form with error and pre-populated fields — do not redirect
- On success: flash confirmation and redirect to `url_for("profile")`
- Ownership check must happen at the database level (WHERE clause includes `user_id`) — not only in Python
- Currency as Rs — never £ or $
- CSS variables only — never hardcoded hex values

## Definition of done
- [ ] `GET /expenses/<id>/edit` renders the form pre-populated with the expense's current values
- [ ] Unauthenticated access redirects to `/login`
- [ ] Attempting to edit another user's expense returns 404
- [ ] Attempting to edit a non-existent expense returns 404
- [ ] Submitting valid changes updates the row in `expenses` and redirects to `/profile`
- [ ] Updated values appear immediately on the profile page
- [ ] Submitting invalid data re-renders the form with an error and pre-populated fields
- [ ] The `id` column is now returned by `get_recent_transactions()` and edit links appear in the transaction table
