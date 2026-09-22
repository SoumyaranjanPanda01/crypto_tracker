# Crypto price tracker

Pulls BTC, ETH and SOL prices (USD) from the CoinGecko public API, stores every pull in SQLite, computes a few metrics from the history and shows them on a small dashboard.

Stack: Python, FastAPI, SQLite, one HTML page with Chart.js.

## Run it

Commands use the Windows `py` launcher. On Mac or Linux, use `python3` instead of `py`.

```bash
py -m pip install -r requirements.txt

# run the app (also starts a background pull every 10 min)
py -m uvicorn app.main:app --reload
```

Open http://localhost:8000 for the dashboard. API docs are at http://localhost:8000/docs.

Run a single pull by hand (no server needed):

```bash
py -m app.pull
```

Run the tests:

```bash
py -m pytest
```

### Settings (env vars)

| Var | Default | What it does |
|---|---|---|
| `PULL_EVERY_MIN` | 10 | minutes between scheduled pulls, `0` turns it off |
| `ROLLING_WINDOW` | 5 | how many pulls the rolling average uses |
| `ALERT_PCT` | 2 | flag on the dashboard if price moved this % or more since last pull |
| `DB_PATH` | data.db | sqlite file |

## Dashboard

- Coin dropdown to switch between bitcoin, ethereum, solana
- **Pull now** triggers a real pull
- **Simulate failed pull** records a fake failure so you can see the error state without breaking the network
- Metric tiles, a big-move alert, and a line chart with a date range filter

## API

- `GET /latest?coin=bitcoin` latest price, change, rolling average, min/max, alert flag and info on the last pull attempt
- `GET /history?coin=bitcoin&start=2026-09-01&end=2026-09-22` stored time series. `start`/`end` take `YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS` (UTC). A date-only `end` includes that whole day.
- `POST /pull` run a pull now. `?fail=true` fakes a failure for testing.
- `GET /coins` list of tracked coins

## Project layout

```
app/
  db.py        sqlite connection and schema
  pull.py      fetch from CoinGecko and store (the "pull" + "store" part)
  metrics.py   pure functions for the derived metrics (the "compute" part)
  main.py      FastAPI routes, scheduler, cache
  static/index.html   dashboard
tests/
  test_metrics.py  metric math
  test_api.py      endpoints, failure handling, date filter
```

## Decisions and tradeoffs

**Why CoinGecko.** Crypto prices change every minute, so repeated pulls actually show movement. Frankfurter only updates once a day, so every pull within a day would give 0% change.

**Schema.** Two tables. `pulls` has one row per attempt with status `ok` or `failed` and the error message. `prices` has one row per coin per successful pull, linked by `pull_id`. Nothing is overwritten, so history keeps growing and failed attempts are visible too.

**Scheduling.** A background thread inside the app pulls every `PULL_EVERY_MIN` minutes, plus you can pull manually from the UI or the CLI. This is fine for one instance. With more time I'd move it to a proper scheduler (cron, APScheduler, or a separate worker) so it doesn't run twice if the app is scaled to more than one process.

**Flaky API.** Each request has a 10 second timeout and is retried 3 times with a 2 second wait. If it still fails, the attempt is saved as `failed` and the app keeps running. The dashboard then shows a red banner with the time and error, and keeps showing the last good data with its timestamp. If there is no data at all it says so and points you to the Pull now button. Partial responses (a coin missing) are treated as a failed pull so we never store half a snapshot.

**Metrics.**
- Change since last pull: `last - prev` and `(last - prev) / prev * 100`, compared against the previous successful pull. Shows "needs 2 pulls" until there are two points.
- Rolling average: mean of the last 5 pulls (configurable). If fewer than 5 exist, it averages what's there.
- Min/max: over all stored history for that coin, not the date filter on the chart.
- Alert: shown when the absolute % change is at or above `ALERT_PCT`.

**Caching.** Computed metrics are cached in memory per coin and cleared after every pull, so repeated page loads don't recompute. Info about the last pull attempt is always read fresh.

**Known limits.**
- `/latest` loads the full history for a coin to compute min/max. Fine for thousands of rows. For much more I'd compute min/max in SQL and only fetch the last N rows.
- Timestamps are stored as UTC text in a fixed format so plain string comparison works for filtering.
- On free hosting (like Render free tier) the disk resets on redeploy, so the SQLite history is lost. A real deploy would use a persistent disk or Postgres.
- The "simulate failure" endpoint is open. In production it should be removed or put behind auth.

## Deploy

Docker:

```bash
docker build -t crypto-tracker .
docker run -p 8000:8000 crypto-tracker
```

Render: push the repo to GitHub, create a new Blueprint on Render and point it at the repo. It picks up `render.yaml` and the Dockerfile.

## Time spent

About 2 to 3 hours.

## Use of AI tools

I used an AI coding assistant (Claude) to speed up writing the code. I reviewed every file, ran the tests and checked the metric formulas by hand. I understand how each part works and can explain or modify any of it as needed.
