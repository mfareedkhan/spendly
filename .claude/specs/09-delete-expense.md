# Spec: Delete Expense

## Overview
Allow authenticated users to permanently delete their own expenses from the profile page transaction table. The UI uses an inline form with a browser confirmation dialog. Ownership is verified before any deletion occurs.

## Depends on
- Step 01 — Database setup (`expenses` table, `get_db()`)
- Step 03 — Login (`session["user_id"]`)
- Step 05 — Backend connection (`database/queries.py`)
- Step 08 — Edit expense (`get_expense_by_id()` already exists for ownership verification)

## Routes
- `POST /expenses/<int:id>/delete` — verify ownership, delete row, redirect to `/profile` — login required
- `GET /expenses/<int:id>/delete` — returns 405 Method Not Allowed

## Database changes
Add to `database/queries.py`:
- **`delete_expense(expense_id, user_id)`** — executes `DELETE FROM expenses WHERE id = ? AND user_id = ?` using parameterized queries

## Templates
- **Modify**: `templates/profile.html` — add a delete button to the existing "Actions" column
  - Inline `<form method="post" action="{{ url_for('delete_expense', id=expense.id) }}" style="display:inline" onsubmit="return confirm('Delete this expense?')">`
  - The one permitted inline style is `display:inline` on the `<form>` tag
  - Delete button uses a `.btn-delete` CSS class with colour defined via CSS variables

## Files to change
- `app.py` — add `POST /expenses/<int:id>/delete` handler
- `database/queries.py` — add `delete_expense()` helper
- `templates/profile.html` — add delete form to the Actions column

## Files to create
None.

## New dependencies
None.

## Rules for implementation
- Raw `sqlite3` only — no ORMs
- Parameterized queries only — never f-strings in SQL
- Unauthenticated requests redirect to `/login` (302)
- If expense not found or belongs to another user → `abort(404)`
- GET requests to the delete URL → `abort(405)`
- Use `get_expense_by_id(expense_id, user_id)` from Step 08 for ownership verification before deleting
- On success: redirect to `url_for("profile")`
- The `confirm()` dialog is the only JS required — no other JS changes
- `.btn-delete` styling must use CSS variables — never hardcoded hex values
- Currency as ₹ — never £ or $

## Definition of done
- [ ] Delete button appears in the Actions column for each transaction on the profile page
- [ ] Clicking delete shows a browser confirm dialog before submitting
- [ ] Confirming deletes the expense row and redirects to `/profile`
- [ ] The deleted expense no longer appears in the transaction table
- [ ] Unauthenticated delete attempts redirect to `/login`
- [ ] Attempting to delete another user's expense returns 404
- [ ] Attempting to delete a non-existent expense returns 404
- [ ] `GET /expenses/<id>/delete` returns 405
