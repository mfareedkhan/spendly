import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash


def get_db():
    con = sqlite3.connect("spendly.db")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL NOT NULL,
            category    TEXT NOT NULL,
            date        TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    con.commit()
    con.close()


def create_user(name, email, password):
    password_hash = generate_password_hash(password)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = get_db()
    cur = con.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, created_at),
    )
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return new_id


def seed_db():
    con = get_db()
    row = con.execute(
        "SELECT COUNT(*) FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    if row[0] > 0:
        con.close()
        return

    con.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123"), "2026-01-01"),
    )
    con.commit()

    user_id = con.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()["id"]

    expenses = [
        (user_id, 12.50,  "Food",          "2026-05-01", "Lunch at café"),
        (user_id, 45.00,  "Bills",         "2026-05-03", "Electricity bill"),
        (user_id, 8.75,   "Transport",     "2026-05-05", "Bus pass top-up"),
        (user_id, 62.99,  "Shopping",      "2026-05-08", "New trainers"),
        (user_id, 20.00,  "Entertainment", "2026-05-10", "Cinema tickets"),
        (user_id, 35.40,  "Health",        "2026-05-14", "Pharmacy prescription"),
        (user_id, 18.90,  "Food",          "2026-05-18", "Grocery run"),
        (user_id, 9.99,   "Entertainment", "2026-05-22", "Streaming subscription"),
    ]
    con.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    con.commit()
    con.close()
