# all functions take prices ordered oldest -> newest


def change(values):
    # change between the last two pulls, returns (absolute, percent)
    if len(values) < 2:
        return None, None
    prev, last = values[-2], values[-1]
    diff = last - prev
    pct = diff / prev * 100 if prev != 0 else None
    return diff, pct


def rolling_avg(values, n):
    # mean of the last n values, or of all of them if we have fewer than n
    if not values:
        return None
    window = values[-n:]
    return sum(window) / len(window)


def summarize(values, n=5, alert_pct=2.0):
    diff, pct = change(values)
    return {
        "current": values[-1] if values else None,
        "change": diff,
        "change_pct": pct,
        "rolling_avg": rolling_avg(values, n),
        "window": n,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "points": len(values),
        "alert": pct is not None and abs(pct) >= alert_pct,
    }
