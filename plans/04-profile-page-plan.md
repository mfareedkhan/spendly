# Plan — Step 4: `/profile` Page (UI with Hardcoded Data)

## Context
Spendly's `/profile` route is currently a stub (`app.py:100-102`) returning plain text. Step 4 of the
roadmap builds the **full profile UI** — user card, summary stats, transaction table, category
breakdown — but deliberately with **hardcoded data only**. Wiring these to live DB queries is a
separate, later step (Step 5, `05-backend-routes-for-profile-page.md`). The goal here is to validate
the page layout in isolation so the next step can focus purely on the backend.

Spec: `.claude/specs/04-profile-page.md`. This plan honors all CLAUDE.md constraints: page-specific
styles in a new `.css` file (not inline), no hardcoded hex (CSS variables only), templates extend
`base.html`, `url_for()` for internal links, no new pip packages, no DB helpers added this step.

Confirmed design decisions (from user):
- **Badge colors:** add a small set of `--cat-*` tokens to `:root`; `profile.css` references only vars.
- **Breakdown:** show percentage **and** a data-driven progress bar (width via `style="--pct: N%"`).
- **Dates:** prettified display (`14 Jun 2026`), hardcoded directly — no `datetime` import.

## Step 1 — `app.py`: implement the `profile()` route
Replace the stub at `app.py:100-102`. `redirect`, `url_for`, `session` are already imported (line 3) —
no new imports.

- **Auth guard** (mirror inverse of login/register's `session.get("user_id")` pattern):
  ```python
  @app.route("/profile")
  def profile():
      if "user_id" not in session:
          return redirect(url_for("login"))
  ```
- **Hardcoded context** as local literals inside the function (not module-level — keeps it obviously
  temporary for Step 5 removal). Currency stored as integer rupees; dates as pretty strings:
  ```python
  user = {"name": "Aarav Sharma", "email": "aarav.sharma@example.com",
          "member_since": "March 2025"}
  transactions = [
      {"date": "14 Jun 2026", "category": "Food",          "description": "Lunch at Saravana Bhavan", "amount": 420},
      {"date": "12 Jun 2026", "category": "Transport",     "description": "Auto to office",            "amount": 180},
      {"date": "10 Jun 2026", "category": "Shopping",      "description": "Cotton kurta",              "amount": 1299},
      {"date": "08 Jun 2026", "category": "Bills",         "description": "Electricity bill",          "amount": 2150},
      {"date": "05 Jun 2026", "category": "Entertainment", "description": "Movie tickets",             "amount": 600},
      {"date": "02 Jun 2026", "category": "Food",          "description": "Groceries — BigBasket",     "amount": 1850},
  ]
  ```
- **Derive** (don't hardcode) computed values so they can't drift from the table:
  ```python
  total_spent = sum(t["amount"] for t in transactions)
  totals = {}
  for t in transactions:
      totals[t["category"]] = totals.get(t["category"], 0) + t["amount"]
  breakdown = [
      {"category": c, "total": a, "percent": round(a / total_spent * 100)}
      for c, a in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
  ]
  top_category = breakdown[0]["category"]
  initials = "".join(w[0] for w in user["name"].split()[:2]).upper()  # "AS"
  stats = {"total_spent": total_spent, "transaction_count": len(transactions),
           "top_category": top_category}
  ```
- **Render:** `render_template("profile.html", user=user, initials=initials, stats=stats,
  transactions=transactions, breakdown=breakdown)`

## Step 2 — `templates/profile.html` (new)
Extends `base.html`; link page CSS via `{% block head %}` exactly as `landing.html:5-7` does.

```jinja
{% extends "base.html" %}
{% block title %}Profile — Spendly{% endblock %}
{% block head %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/profile.css') }}">
{% endblock %}
{% block content %} ... {% endblock %}
```

Wrap all four sections in a `.profile-page` container at `var(--max-width)` (the `.auth-*` classes are
440px — too narrow for the table). Sections:
1. **User card** — `.avatar-circle` (initials), name (`--font-display`), email, "Member since {{ user.member_since }}".
2. **Stats row** — three `.stat-card`s: Total spent `₹{{ "{:,}".format(stats.total_spent) }}`,
   transaction count, top category.
3. **Transaction table** — columns Date / Category / Description / Amount; loop `transactions`;
   category cell = `<span class="badge badge-{{ t.category|lower }}">{{ t.category }}</span>`;
   amount `₹{{ "{:,}".format(t.amount) }}`. (Category names are single words → `|lower` is a safe class slug.)
4. **Category breakdown** — loop `breakdown`; per row show category badge, `₹total`, `{{ b.percent }}%`,
   and a bar: `<div class="bar" style="--pct: {{ b.percent }}%"></div>` (the only `style=` attr — width
   only, data-driven; all colors via CSS vars).

No inline `<style>`, no hex, no hardcoded URLs.

## Step 3 — `static/css/style.css`: add category color tokens to `:root`
Append to the existing `:root` block (`style.css:5-31`) — reuse existing palette for 3 categories, add
2 new tints for the others:
```css
--cat-food: var(--accent);            --cat-food-bg: var(--accent-light);
--cat-transport: var(--accent-2);     --cat-transport-bg: var(--accent-2-light);
--cat-bills: var(--danger);           --cat-bills-bg: var(--danger-light);
--cat-shopping: #5b4b8a;              --cat-shopping-bg: #efeaf7;     /* new purple */
--cat-entertainment: #1f6f8b;         --cat-entertainment-bg: #e6f1f4; /* new teal */
```
These two new hex values live in `:root` alongside the existing palette — the established place for raw
colors. `profile.css` references only the variables.

## Step 4 — `static/css/profile.css` (new)
Define, using CSS variables only (no literal hex):
- `.profile-page` (`max-width: var(--max-width); margin: 0 auto; padding: 3rem 2rem;`)
- `.profile-header-card`, `.avatar-circle` (bg `--accent`, white text, circular), `.user-name`
  (`--font-display`), `.user-email`/`.user-since` (`--ink-muted`)
- `.stats-row` (grid/flex), `.stat-card`, `.stat-label`, `.stat-value`
- `.txn-table` + `th`/`td` + `.txn-amount` (right-aligned)
- `.badge` base + one variant per category: `.badge-food { color: var(--cat-food);
  background: var(--cat-food-bg); }` … through `entertainment`
- `.breakdown-row`, `.bar` (`width: var(--pct)`, fill color `--accent`), percentage/total text styles

## Step 5 — `CLAUDE.md` housekeeping
Update the routes table (`CLAUDE.md:82`) for `GET /profile` from
`Stub — Step 4` → `Implemented — renders profile.html (hardcoded data; DB in Step 5)`, matching how
`/`, `/register`, `/login`, `/logout` are described.

## Files
- **Modify:** `app.py` (route), `static/css/style.css` (`:root` tokens), `CLAUDE.md` (routes table)
- **Create:** `templates/profile.html`, `static/css/profile.css`
- **Do NOT touch:** `database/db.py` (no DB this step), no new pip packages

## Verification (manual, port 5001)
Run: `cd /mnt/d/Claude-Code/expense-tracker && python app.py`
1. **Unauthed redirect:** `curl -si http://localhost:5001/profile | grep -i location` → `Location: /login`.
2. **Logged in:** log in via `/login` (seeded creds in `db.py` `seed_db()` → `demo@spendly.com` / `demo123`),
   then `/profile` renders with no errors.
3. **User card:** avatar shows "AS"; name, email, member-since visible.
4. **Stats:** total = ₹6,499 (sum of rows), count = 6, top category = "Food".
5. **Table:** 6 rows, 4 columns; each category a colored badge; view-source shows
   `class="badge badge-..."` and **no inline color/hex** `style=` attrs (only the bar's `--pct` width).
6. **Breakdown:** per-category totals + percentages (~100% total) + bars.
7. **Currency:** page shows `₹`; `curl -s ... | grep -E '£|\$'` returns nothing.
8. **No inline `<style>`** in `profile.html`; styling only via the `profile.css` link.
9. Per CLAUDE.md subagent policy, run tests via a subagent after implementation (`pytest`) to confirm
   nothing regressed.
