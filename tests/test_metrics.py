import pytest

from app.metrics import change, rolling_avg, summarize


def test_change_uses_last_two_values():
    diff, pct = change([50, 100, 110])
    assert diff == 10
    assert pct == pytest.approx(10.0)  # 10 / 100, not 10 / 110


def test_change_negative():
    diff, pct = change([200, 150])
    assert diff == -50
    assert pct == pytest.approx(-25.0)


def test_change_needs_two_points():
    assert change([]) == (None, None)
    assert change([5]) == (None, None)


def test_change_prev_zero():
    assert change([0, 5]) == (5, None)


def test_rolling_avg_uses_last_n_not_first_n():
    assert rolling_avg([1, 2, 3, 4, 5, 6], 3) == pytest.approx(5.0)


def test_rolling_avg_fewer_than_n():
    assert rolling_avg([2, 4], 5) == pytest.approx(3.0)


def test_rolling_avg_empty():
    assert rolling_avg([], 5) is None


def test_summarize_min_max_and_alert():
    s = summarize([100, 90, 120, 95], n=2, alert_pct=10)
    assert s["current"] == 95
    assert s["min"] == 90 and s["max"] == 120
    assert s["rolling_avg"] == pytest.approx(107.5)
    assert s["alert"] is True  # 120 -> 95 is about -20.8%


def test_summarize_small_move_no_alert():
    assert summarize([100, 101], alert_pct=2)["alert"] is False


def test_summarize_empty():
    s = summarize([])
    assert s["current"] is None and s["points"] == 0 and s["alert"] is False
