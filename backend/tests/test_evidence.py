import datetime as dt
from types import SimpleNamespace

from app.db.enums import AccountRole
from app.evidence.chat import normalize, vader_sentiment
from app.evidence.fare import compute_fare
from app.evidence.history import compute_history_profile
from app.evidence.noshow import compute_noshow
from app.evidence.route import compute_route_deviation

T0 = dt.datetime(2026, 1, 1, 8, 0, 0, tzinfo=dt.timezone.utc)


def _t(sec):
    return T0 + dt.timedelta(seconds=sec)


def _lerp(p, q, f):
    return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)


def _straight_route(n=20):
    return [_lerp((1.30, 103.85), (1.34, 103.91), i / (n - 1)) for i in range(n)]


def _deviation_scenario():
    route = _straight_route()
    pts = []
    k = 0
    for i in range(8):
        pts.append((route[i][0], route[i][1], _t(k * 20), 30.0))
        k += 1
    detour = (route[10][0] + 0.027, route[10][1])
    for f in (0.33, 0.66, 1.0):
        p = _lerp(route[7], detour, f)
        pts.append((p[0], p[1], _t(k * 20), 30.0))
        k += 1
    for f in (0.33, 0.66, 1.0):
        p = _lerp(detour, route[13], f)
        pts.append((p[0], p[1], _t(k * 20), 30.0))
        k += 1
    for i in range(14, 20):
        pts.append((route[i][0], route[i][1], _t(k * 20), 30.0))
        k += 1
    return route, pts


def _detour_scenario():
    route = _straight_route()
    pts = []
    k = 0
    for i in range(6):
        pts.append((route[i][0], route[i][1], _t(k * 20), 28.0))
        k += 1
    for i in range(6, 12):
        pts.append((route[i][0], route[i][1], _t(k * 20), 7.0))
        k += 1
    detour = (route[15][0] + 0.006, route[15][1])
    for f in (0.5, 1.0):
        p = _lerp(route[12], detour, f)
        pts.append((p[0], p[1], _t(k * 20), 30.0))
        k += 1
    for f in (0.5, 1.0):
        p = _lerp(detour, route[17], f)
        pts.append((p[0], p[1], _t(k * 20), 30.0))
        k += 1
    for i in range(18, 20):
        pts.append((route[i][0], route[i][1], _t(k * 20), 28.0))
        k += 1
    return route, pts


def _normal_scenario():
    route = _straight_route()
    pts = [(p[0], p[1], _t(i * 20), 28.0) for i, p in enumerate(route)]
    return route, pts


def test_route_deviation_flagged_bad_faith():
    route, pts = _deviation_scenario()
    result = compute_route_deviation(route, pts)
    assert result["data"]["bad_faith_deviation"] is True
    assert result["supports"] == "rider"
    assert result["data"]["extra_distance_km"] >= 2.0


def test_legit_detour_not_bad_faith():
    route, pts = _detour_scenario()
    result = compute_route_deviation(route, pts)
    assert result["data"]["traffic_signal"] is True
    assert result["data"]["bad_faith_deviation"] is False


def test_normal_route_neutral():
    route, pts = _normal_scenario()
    result = compute_route_deviation(route, pts)
    assert result["data"]["bad_faith_deviation"] is False
    assert result["supports"] == "neutral"


def _trip(**overrides):
    defaults = dict(
        base_fare=3.0,
        per_km_rate=0.9,
        per_min_rate=0.3,
        estimated_distance_km=5.0,
        estimated_duration_min=20.0,
        surge_multiplier=1.0,
        promo_discount=0.0,
        estimated_fare=13.5,
        actual_fare=13.5,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_fare_surge_applied():
    result = compute_fare(_trip(surge_multiplier=2.5, estimated_fare=13.5, actual_fare=33.75))
    assert result["data"]["likely_cause"] == "surge_applied"
    assert result["supports"] == "rider"
    assert result["data"]["surge_premium"] > 0


def test_fare_consistent():
    result = compute_fare(_trip())
    assert result["data"]["likely_cause"] == "none"
    assert result["supports"] == "neutral"
    assert result["data"]["arithmetic_discrepancy"] == 0.0


def test_fare_miscalculation():
    result = compute_fare(_trip(actual_fare=20.0))
    assert result["data"]["likely_cause"] == "fare_miscalculation"
    assert result["data"]["arithmetic_discrepancy"] > 0


def _driver_no_show():
    pickup = (1.30, 103.85)
    pts = [(pickup[0] + 0.0036, pickup[1], _t(i * 25), 0.0) for i in range(10)]
    return pickup, pts


def _rider_no_show():
    pickup = (1.30, 103.85)
    start = (pickup[0] - 0.016, pickup[1])
    pts = []
    k = 0
    for f in (0.25, 0.5, 0.75, 1.0):
        p = _lerp(start, pickup, f)
        pts.append((p[0], p[1], _t(k * 30), 25.0))
        k += 1
    for s in range(0, 360, 30):
        pts.append((pickup[0], pickup[1], _t(k * 30 + s), 0.0))
    return pickup, pts


def test_noshow_driver_never_arrived():
    pickup, pts = _driver_no_show()
    result = compute_noshow(pickup, pts)
    assert result["data"]["driver_arrived"] is False
    assert result["data"]["cancellation_fee_valid"] is False
    assert result["supports"] == "rider"


def test_noshow_rider_waited_5min():
    pickup, pts = _rider_no_show()
    result = compute_noshow(pickup, pts)
    assert result["data"]["driver_arrived"] is True
    assert result["data"]["wait_duration_min"] >= 5.0
    assert result["data"]["cancellation_fee_valid"] is True
    assert result["supports"] == "driver"


def _account(account_id, rating, created_at=T0):
    return SimpleNamespace(id=account_id, name="Account", role=AccountRole.rider, rating=rating, created_at=created_at)


def test_history_abuser_scores_higher():
    abuser = compute_history_profile(_account(10, 3.4), dispute_count=8, won_count=0, resolved_count=0)
    normal = compute_history_profile(_account(1, 4.8), dispute_count=3, won_count=0, resolved_count=0)
    assert abuser["data"]["abuse_risk_score"] > normal["data"]["abuse_risk_score"]
    assert abuser["data"]["dispute_count"] == 8


def test_history_win_rate_lowers_risk():
    loser = compute_history_profile(_account(2, 4.0), dispute_count=5, won_count=1, resolved_count=5)
    winner = compute_history_profile(_account(3, 4.0), dispute_count=5, won_count=5, resolved_count=5)
    assert winner["data"]["abuse_risk_score"] < loser["data"]["abuse_risk_score"]


def test_chat_normalize_strips_and_dedupes():
    messages = [(1, "  hi  "), (2, "hi"), (3, "   "), (4, "hello")]
    assert normalize(messages) == [(1, "hi"), (4, "hello")]


def test_chat_vader_sentiment_direction():
    pos = vader_sentiment(["I love this ride, thank you very much!"])
    neg = vader_sentiment(["I hate this, worst driver ever!"])
    assert pos["compound"] > 0
    assert neg["compound"] < 0
