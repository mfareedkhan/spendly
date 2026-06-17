# Spec: Backend Connection for Profile Page

## Overview
Replace the hardcoded demo data in the `/profile` route with live SQLite queries. After this step the profile page shows each logged-in user's actual expenses, real summary statistics, and a live category breakdown.

## Depends on
- Step 01 — Database setup (`get_db()`, `users` and `expenses` tables)
- Step 03 — Login (`session["user_id"]` populated on login)
- Step 04 — Profile page UI (template already built and styled)

## Routes
- `GET /profile` — no route signature change; only the data source changes

## Database changes
Create a new file `database/queries.py` with four query functions:

- **`get_user_by_id(user_id)`** — returns user row with `name`, `email`, and membership date formatted as `"Month YYYY"`
- **`get_summary_stats(user_id)`** — returns `total_spent` (float), `transaction_count` (int), `top_category` (str); returns zeros and empty string for users with no expenses
- **`get_recent_transactions(user_id, limit=10)`** — returns up to 10 most recent expenses ordered newest-first
- **`get_category_breakdown(user_id)`** — returns list of `{category, total, percentage}` dicts; percentages are integers summing to exactly 100 (apply rounding adjustment to the largest category)

## Templates
- **Modify**: `templates/profile.html` — replace hardcoded values with Jinja2 template variables

## Files to change
- `app.py` — update `profile()` to call the four query functions and pass real data to the template
- `templates/profile.html` — replace hardcoded demo data with template variables

## Files to create
- `database/queries.py` — implement the four query functions listed above

## New dependencies
None.

## Rules for implementation
- Raw `sqlite3` only — no ORMs, no SQLAlchemy
- Parameterized queries only — never f-strings or string concatenation in SQL
- Currency must always display as ₹ — never £ or $
- Empty state: functions must return zeros and empty collections for users with no expenses — never raise exceptions
- Category percentages must be integers and must sum to exactly 100; apply rounding correction to the largest category
- Membership date format: `"Month YYYY"` derived from `created_at`

## Definition of done
- [ ] Logging in as the seed user (`demo@spendly.com`) shows ₹346.24 total spending
- [ ] Transaction count shows 8
- [ ] Top category shows "Bills"
- [ ] All 7 categories appear in the breakdown
- [ ] Category percentages sum to exactly 100
- [ ] A user with no expenses sees zeros and empty tables — no errors
- [ ] No hardcoded data remains in `app.py`'s `profile()` function
