# Spec: Database Setup

## Overview
Implement the SQLite data layer for Spendly. This step creates the foundational database schema and helper functions that all subsequent features depend on. No routes change in this step — the goal is a working, tested database layer.

## Depends on
Nothing — this is Step 1.

## Routes
- No new routes. No route changes.
- Existing placeholder routes in `app.py remain unchanged

## Database changes
Create `database/db.py` with three functions:

- **`get_db()`** — opens a connection to `spendly.db`, sets `row_factory = sqlite3.Row` for dict-like access, and runs `PRAGMA foreign_keys = ON`
- **`init_db()`** — creates the `users` and `expenses` tables using `CREATE TABLE IF NOT EXISTS` (safe to call repeatedly)
- **`seed_db()`** — inserts one demo user and eight sample expenses; checks for existing data first to avoid duplicates on repeated runs

### `users` table schema
```sql
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
```

### `expenses` table schema
```sql
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL NOT NULL,
    category    TEXT NOT NULL,
    date        TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Seed data
- Demo user: `demo@spendly.com` / `demo123` (password hashed with werkzeug)
- Eight sample expenses across at least five of the seven categories
- Dates formatted as `YYYY-MM-DD`
- Categories: Food, Transport, Bills, Health, Entertainment, Shopping, Other

## Templates
None.

## Files to change
- `app.py` — import `init_db` and `seed_db` from `database/db.py`; call both inside `with app.app_context()` at startup

## Files to create
- `database/db.py` — implement `get_db()`, `init_db()`, `seed_db()`

## New dependencies
No new dependencies. `sqlite3` is stdlib; `werkzeug.security` is already in `requirements.txt`.

## Rules for implementation
- Use parameterized queries only — never f-strings or string concatenation in SQL
- Hash the demo password with `werkzeug.security.generate_password_hash` — never store plaintext
- `get_db()` must call `PRAGMA foreign_keys = ON` on every new connection
- `seed_db()` must be idempotent — running it twice must not create duplicate rows
- All dates must be stored as `TEXT` in `YYYY-MM-DD` format

## Definition of done
- [ ] `python app.py` starts without errors
- [ ] `spendly.db` is created on first run with `users` and `expenses` tables
- [ ] `seed_db()` inserts the demo user and eight expenses on first run
- [ ] Running the app a second time does not duplicate seed data
- [ ] The demo user's password is stored as a hash — never plaintext
- [ ] `get_db()` returns rows accessible by column name (sqlite3.Row)
- [ ] Foreign key enforcement is confirmed: inserting an expense with a non-existent user_id raises an error
