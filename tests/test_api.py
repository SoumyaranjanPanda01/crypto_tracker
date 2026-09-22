import pytest
from fastapi.testclient import TestClient

from app import db, main, pull


@pytest.fixture
def client(tmp_path, monkeypatch):
    # fresh sqlite file per test, no scheduler (lifespan does not run here)
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    main.cache.clear()
    return TestClient(main.app)


def fake_prices(values):
    # returns a fake fetch that gives the next bitcoin price each call
    it = iter(values)

    def fetch():
        p = next(it)
        return {"bitcoin": p, "ethereum": 1.0, "solana": 1.0}
    return fetch


def test_latest_after_pulls(client, monkeypatch):
    monkeypatch.setattr(pull, "fetch_prices", fake_prices([100, 110]))
    client.post("/pull")
    client.post("/pull")
    d = client.get("/latest?coin=bitcoin").json()
    assert d["current"] == 110
    assert d["change"] == 10
    assert d["change_pct"] == pytest.approx(10.0)
    assert d["points"] == 2


def test_failed_pull_keeps_last_good_data(client, monkeypatch):
    monkeypatch.setattr(pull, "fetch_prices", fake_prices([100]))
    client.post("/pull")

    def broken():
        raise ConnectionError("api down")
    monkeypatch.setattr(pull, "fetch_prices", broken)

    r = client.post("/pull")
    assert r.status_code == 200 and r.json()["ok"] is False

    d = client.get("/latest?coin=bitcoin").json()
    assert d["current"] == 100  # still the last good value
    assert d["last_pull"]["status"] == "failed"


def test_history_date_filter(client):
    with db.connect() as conn:
        conn.execute("INSERT INTO pulls (pulled_at, status) VALUES ('x', 'ok')")
        for ts, price in [("2026-09-01 10:00:00", 1), ("2026-09-02 23:30:00", 2), ("2026-09-03 08:00:00", 3)]:
            conn.execute("INSERT INTO prices VALUES (1, 'bitcoin', ?, ?)", (price, ts))
    pts = client.get("/history?coin=bitcoin&start=2026-09-02&end=2026-09-02").json()["points"]
    assert [p["price"] for p in pts] == [2]  # end date includes the whole day


def test_unknown_coin(client):
    assert client.get("/latest?coin=dogecoin").status_code == 404
