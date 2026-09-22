import time
from datetime import datetime, timezone

import requests

from app import db

COINS = ["bitcoin", "ethereum", "solana"]
URL = "https://api.coingecko.com/api/v3/simple/price"


def fetch_prices():
    # try 3 times with a short wait, 10s timeout so a slow api can't hang us
    for attempt in range(3):
        try:
            r = requests.get(URL, params={"ids": ",".join(COINS), "vs_currencies": "usd"}, timeout=10)
            r.raise_for_status()
            data = r.json()
            return {c: float(data[c]["usd"]) for c in COINS}
        except (requests.RequestException, KeyError, ValueError):
            if attempt == 2:
                raise
            time.sleep(2)


def run_pull(force_fail=False):
    # timestamps are UTC, stored as "YYYY-MM-DD HH:MM:SS" so string compare works for date filters
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        if force_fail:
            raise RuntimeError("forced failure from the test button")
        prices = fetch_prices()
    except Exception as e:
        # log the failed attempt and return, never crash the app
        with db.connect() as conn:
            conn.execute("INSERT INTO pulls (pulled_at, status, error) VALUES (?, 'failed', ?)", (now, str(e)))
        return {"ok": False, "pulled_at": now, "error": str(e)}

    with db.connect() as conn:
        cur = conn.execute("INSERT INTO pulls (pulled_at, status) VALUES (?, 'ok')", (now,))
        rows = [(cur.lastrowid, coin, price, now) for coin, price in prices.items()]
        conn.executemany("INSERT INTO prices VALUES (?, ?, ?, ?)", rows)
    return {"ok": True, "pulled_at": now, "prices": prices}


if __name__ == "__main__":
    # manual pull: python -m app.pull
    db.init_db()
    print(run_pull())
