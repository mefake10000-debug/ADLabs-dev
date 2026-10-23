"""Helper handoff wiring — queue episodes, glass null honesty, alerts LIVE gate."""
from src.analytics.queue_analyzer import QueueAnalyzer
from src.analytics.glass_analyzer import build_glass_block
from src.analytics.alerts_engine import AlertsEngine, load_alerts_catalog
from src.perception.tracker import Track


def _track(tid, x, y, t, stationary=False):
    tr = Track(tid, [x - 10, y - 80, x + 10, y], 0.9, t)
    tr.is_stationary = stationary
    return tr


def test_queue_episodes_abandon_null_without_service_point():
    q = QueueAnalyzer(
        "q1", "Checkout",
        polygon=[[0, 0], [200, 0], [200, 200], [0, 200]],
        exit_grace_seconds=0.1,
    )
    t0 = 1000.0
    q.update([_track(1, 50, 50, t0)], t0)
    # dwell ≥5s to count in length
    q.update([_track(1, 50, 50, t0 + 6)], t0 + 6)
    m = q.get_metrics()
    assert m["now"]["length"] >= 1
    assert m["now"]["max_wait_ms"] is not None
    # leave beyond grace
    q.update([], t0 + 10)
    m2 = q.get_metrics()
    assert m2["recent_episodes"]
    ep = m2["recent_episodes"][-1]
    assert ep["join_ts"] and ep["leave_ts"] and ep["wait_ms"] >= 0
    assert ep["abandon"] is None
    assert m2["abandon_status"] == "PARTIAL"
    assert m2["kpi"]["p95_wait_ms"] is None  # below sample threshold
    assert m2["kpi"]["p95_empty"] is True
    assert m2["kpi"]["service_rate"] is None  # no service_point


def test_queue_service_rate_zero_when_calibrated_but_empty():
    q = QueueAnalyzer(
        "q1", "Checkout",
        polygon=[[0, 0], [200, 0], [200, 200], [0, 200]],
        service_point=[100, 100],
        exit_grace_seconds=0.1,
    )
    kpi = q.get_metrics()["kpi"]
    assert kpi["empty"] is True
    assert kpi["service_rate"] == 0.0
    assert kpi["abandon_rate"] == 0.0
    assert kpi["service_rate_basis"] == "service_point"


def test_glass_block_none_when_uncalibrated():
    assert build_glass_block([]) is None


def test_alerts_catalog_loads_and_future_never_fires():
    cat = load_alerts_catalog()
    assert cat.get("alerts") is not None
    engine = AlertsEngine()
    out = engine.evaluate({
        "queues": [{"id": "q1", "queue_length": 9, "max_capacity": 4}],
        "queue_length": 9,
        "queue_alert_active": True,
        "staff_zones": [],
        "safety": {"active": []},
    })
    assert any(a.get("id") == "QUEUE_LENGTH_OVER" for a in out["active"])
    # FUTURE rows must not appear in active
    future_ids = {r["id"] for r in out["future_catalog"]}
    assert not any(a["id"] in future_ids for a in out["active"])
