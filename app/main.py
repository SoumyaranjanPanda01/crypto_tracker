import os
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app import db, metrics
from app.pull import COINS, run_pull

WINDOW = int(os.getenv("ROLLING_WINDOW", 5))
ALERT_PCT = float(os.getenv("ALERT_PCT", 2))
PULL_EVERY_MIN = float(os.getenv("PULL_EVERY_MIN", 10))  # 0 turns the scheduler off

cache = {}  # coin -> computed summary, wiped after every pull


def do_pull(force_fail=False):
    result = run_pull(force_fail)
    cache.clear()
    return result


def scheduler():
    # simple background loop, fine for a single instance
    while True:
        do_pull()
        time.sleep(PULL_EVERY_MIN * 60)


@asynccontextmanager
async def lifespan(app):
    db.init_db()
    if PULL_EVERY_MIN > 0:
        threading.Thread(target=scheduler, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)


def check_coin(coin):
    if coin not in COINS:
        raise HTTPException(404, f"unknown coin, pick one of {COINS}")


def last_pull():
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM pulls ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


@app.get("/")
def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.get("/coins")
def coins():
    return COINS


@app.get("/latest")
def latest(coin: str = "bitcoin"):
    check_coin(coin)
    if coin not in cache:
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT price, pulled_at FROM prices WHERE coin = ? ORDER BY pull_id", (coin,)
            ).fetchall()
        summary = metrics.summarize([r["price"] for r in rows], WINDOW, ALERT_PCT)
        summary["as_of"] = rows[-1]["pulled_at"] if rows else None
        cache[coin] = summary
    # last_pull is not cached so a failed attempt shows up right away
    return {"coin": coin, **cache[coin], "last_pull": last_pull()}


@app.get("/history")
def history(coin: str = "bitcoin", start: str = None, end: str = None):
    check_coin(coin)
    sql = "SELECT pulled_at, price FROM prices WHERE coin = ?"
    args = [coin]
    if start:
        sql += " AND pulled_at >= ?"
        args.append(start)
    if end:
        if len(end) == 10:  # date only, so include that whole day
            end += " 23:59:59"
        sql += " AND pulled_at <= ?"
        args.append(end)
    with db.connect() as conn:
        rows = conn.execute(sql + " ORDER BY pull_id", args).fetchall()
    return {"coin": coin, "points": [dict(r) for r in rows]}


@app.post("/pull")
def pull(fail: bool = False):
    # fail=true fakes an api failure so you can test the dashboard error state
    return do_pull(force_fail=fail)
