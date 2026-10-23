"""Staff response_time_to_queue — honest nulls / measured deltas."""
from src.analytics.staff_response import StaffQueueResponseTracker, build_staff_block
from src.analytics.zones import Zone


def test_response_null_without_staff_zone_link():
    tr = StaffQueueResponseTracker(response_timeout_seconds=30.0)
    t0 = 1000.0
    out = tr.observe(
        [{"id": "q1", "alert_active": True, "queue_length": 3, "staff_zone_id": None}],
        [],
        t0,
    )
    assert out["response_time_to_queue"] is None
    assert out["status"] in ("PARTIAL", "EMPTY")
    # After timeout without link → settled null
    out2 = tr.observe(
        [{"id": "q1", "alert_active": True, "queue_length": 3, "staff_zone_id": None}],
        [],
        t0 + 35,
    )
    assert out2["response_time_to_queue"] is None
    assert any(r.get("basis") == "no_staff_zone_link" for r in out2["queue_response"])


def test_response_time_from_alert_to_staff_presence():
    tr = StaffQueueResponseTracker(response_timeout_seconds=600.0)
    sz = Zone("staff_1", "Back", [[0, 0], [100, 0], [100, 100], [0, 100]], zone_type="staff")
    t0 = 2000.0
    tr.observe(
        [{"id": "q1", "alert_active": True, "queue_length": 4, "staff_zone_id": "staff_1"}],
        [sz],
        t0,
    )
    # Staff arrives 12s later
    from src.perception.tracker import Track

    track = Track(9, [40, 20, 60, 100], 0.9, t0 + 12)
    sz.update([track], t0 + 12)
    out = tr.observe(
        [{"id": "q1", "alert_active": True, "queue_length": 4, "staff_zone_id": "staff_1"}],
        [sz],
        t0 + 12,
    )
    assert out["response_time_to_queue"] == 12.0
    assert out["status"] == "LIVE"
    assert out["queue_response"][-1]["basis"] == "session_track_arrival"


def test_build_staff_block_passthrough():
    tr = StaffQueueResponseTracker()
    block = build_staff_block([], tr, [], [], 1000.0)
    assert block["response_time_to_queue"] is None
    assert "zones" in block
    assert block["queue_response"] == [] or isinstance(block["queue_response"], list)
