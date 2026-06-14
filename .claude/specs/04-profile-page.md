# Spec: Profile Page (UI with Hardcoded Data)

## Overview
Build the profile page UI with static, hardcoded data. The goal is to establish the complete layout — user info card, summary stats row, transaction history table, and category breakdown — before any real database queries are wired up. Validate the design in isolation so the next step can focus entirely on the backend connection.

## Depends on
- Step 03 — Login and Logout (`session["user_id"]` must exist for the auth guard)

## Routes
- `GET /profile` — logged-in only; redirect to `/login` if not authenticated

## Database changes
None. All data in this step is hardcoded Python dicts and lists in `app.py`.

## Templates
- **Create**: `templates/profile.html` extending `base.html`

### Four required sections

1. **User info card**
   - Avatar circle showing initials (derived from name)
   - Full name
   - Email address
   - Member since date

2. **Summary stats row**
   - Total spent
   - Transaction count
   - Top category

3. **Transaction history table**
   - Columns: Date, Category, Description, Amount
   - At least 5 hardcoded rows
   - Category badges using CSS classes only — no inline styles

4. **Category breakdown**
   - Per-category totals
   - Percentage of total spend per category

## Files to change
- `app.py` — replace the stub `profile()` route with an auth-checked handler that passes hardcoded context to the template

## Files to create
- `templates/profile.html`

## New dependencies
None.

## Rules for implementation
- All data must be hardcoded Python dicts/lists in `app.py` — no database queries in this step
- Authentication check: `if "user_id" not in session: return redirect(url_for("login"))`
- No inline styles — use CSS classes and CSS variables only
- No hardcoded hex colour values — use CSS variables
- Category badges must use CSS classes only
- Currency displays as ₹ — never £ or $
- All templates extend `base.html`
- Use `url_for()` for every internal link

## Definition of done
- [ ] `GET /profile` renders without errors when logged in
- [ ] Unauthenticated access to `/profile` redirects to `/login`
- [ ] All four sections are visible: user card, stats row, transaction table, category breakdown
- [ ] No inline `<style>` tags or hardcoded hex values in the template
- [ ] Category badges render correctly using CSS classes
- [ ] Currency shown as ₹ throughout
