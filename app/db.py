import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "data.db")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read rows like dicts
    return conn


def init_db():
    # pulls = one row per attempt (ok or failed)
    # prices = one row per coin per successful pull, so history keeps growing
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS pulls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pulled_at TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS prices (
            pull_id INTEGER NOT NULL REFERENCES pulls(id),
            coin TEXT NOT NULL,
            price REAL NOT NULL,
            pulled_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_prices_coin ON prices(coin, pulled_at);
        """)
