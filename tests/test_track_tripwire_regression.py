"""Regressions: track IDs under infer skip, ground-point tripwire, zone dwell."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.tracker import (
    Track,
    SimpleByteTracker,
    tracker_params_for_infer_gap,
)
from src.analytics.tripwire import Tripwire
from src.analytics.zones import Zone


class TrackerInferGapTests(unittest.TestCase):
    def test_balanced_infer_loosens_association(self):
        base = tracker_params_for_infer_gap(1, track_buffer=60, match_thresh=0.45, min_hits=3)
        bal = tracker_params_for_infer_gap(2, track_buffer=60, match_thresh=0.45, min_hits=3)
        fast = tracker_params_for_infer_gap(3, track_buffer=60, match_thresh=0.45, min_hits=3)
        self.assertGreater(bal["dist_gate"], base["dist_gate"])
        self.assertGreater(fast["dist_gate"], bal["dist_gate"])
        self.assertLessEqual(bal["iou_threshold"], base["iou_threshold"])
        self.assertGreaterEqual(bal["max_age"], base["max_age"])

    def test_large_gap_keeps_same_id_via_ground_point(self):
        """Simulate infer_every_n=2: person moves ~70px between updates."""
        params = tracker_params_for_infer_gap(2, track_buffer=60, match_thresh=0.45, min_hits=2)
        tracker = SimpleByteTracker(**{
            k: params[k]
            for k in ("max_age", "iou_threshold", "min_hits", "track_thresh", "dist_gate", "pred_dist_gate", "infer_every_n")
        })
        t0 = time.time()
        # Confirm track
        for i in range(3):
            x = 100 + i * 5
            dets = [{"bbox": [x, 100, x + 60, 280], "confidence": 0.9, "class_id": 0}]
            active = tracker.update(dets, t0 + i * 0.13)
        self.assertEqual(len(active), 1)
        tid = active[0].track_id

        # Big hop (skipped frame) — IoU low, but ground-point distance within scaled gate
        dets = [{"bbox": [175, 105, 235, 285], "confidence": 0.88, "class_id": 0}]
        active = tracker.update(dets, t0 + 0.5)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].track_id, tid)

    def test_track_live_dict_exposes_contract(self):
        t0 = time.time()
        tr = Track(7, [10, 20, 50, 120], 0.9, t0)
        tr.dwell_s = 4.5
        tr.zone_id = "welcome"
        d = tr.to_live_dict()
        self.assertEqual(d["id"], 7)
        self.assertEqual(d["first_seen"], t0)
        self.assertEqual(d["dwell_s"], 4.5)
        self.assertEqual(d["ground_point"], [30.0, 120.0])
        self.assertEqual(d["zone_id"], "welcome")


class TripwireGroundPointTests(unittest.TestCase):
    def test_crossing_uses_foot_not_box_center(self):
        # Horizontal wire at y=400. Box center stays above line; feet cross it.
        tw = Tripwire("ent", "Entrance", [[100, 400], [900, 400]], in_direction="top_to_bottom")
        now = time.time()
        # Tall person: center y≈300, feet at 380 then 420
        track = Track(1, [200, 200, 260, 380], 0.9, now - 0.2)
        track.update([200, 240, 260, 420], 0.9, now)
        events = tw.update([track], now)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["direction"], "in")
        self.assertIn("ground_point", events[0])

    def test_history_scan_catches_crossing_during_warmup(self):
        """Crossing happened on early history segments before min_hits would show the ID."""
        tw = Tripwire("ent", "Entrance", [[100, 400], [900, 400]], in_direction="top_to_bottom")
        now = time.time()
        track = Track(3, [200, 200, 260, 360], 0.9, now - 0.4)
        track.update([200, 220, 260, 390], 0.9, now - 0.3)  # still above
        track.update([200, 250, 260, 430], 0.9, now - 0.2)  # feet crossed
        track.update([200, 270, 260, 460], 0.9, now - 0.1)  # both sides below
        # Only last segment is same-side; full history scan must still fire once
        events = tw.update([track], now)
        self.assertEqual(len(events), 1)
        self.assertEqual(tw.in_count, 1)
        self.assertEqual(tw.session_in, 1)
        # Second call: already counted
        self.assertEqual(tw.update([track], now + 0.1), [])

    def test_reset_pass_clears_session_and_allows_recount(self):
        tw = Tripwire("ent", "Entrance", [[100, 400], [900, 400]], in_direction="top_to_bottom")
        now = time.time()
        track = Track(9, [200, 200, 260, 350], 0.9, now - 0.1)
        track.update([200, 250, 260, 450], 0.9, now)
        tw.update([track], now)
        self.assertEqual(tw.session_in, 1)
        tw.reset_pass()
        self.assertEqual(tw.in_count, 0)
        self.assertEqual(tw.session_in, 0)
        self.assertEqual(len(tw._crossed_track_ids), 0)
        # Same ID can cross again after session reset
        track2 = Track(9, [200, 200, 260, 350], 0.9, now + 1)
        track2.update([200, 250, 260, 450], 0.9, now + 1.1)
        self.assertEqual(len(tw.update([track2], now + 1.1)), 1)


class ZoneDwellTests(unittest.TestCase):
    def test_inflight_dwell_appears_in_metrics(self):
        zone = Zone("z1", "Welcome", [[0, 0], [200, 0], [200, 200], [0, 200]], zone_type="dwell")
        t0 = time.time()
        track = Track(5, [40, 40, 80, 100], 0.9, t0)  # ground point (60, 100) inside
        zone.update([track], t0)
        zone.update([track], t0 + 5.0)
        self.assertGreaterEqual(track.dwell_s, 4.9)
        m = zone.get_metrics(now=t0 + 5.0)
        self.assertEqual(m["current_occupancy"], 1)
        self.assertGreaterEqual(m["avg_dwell_seconds"], 4.9)
        self.assertIn(5, m["dwell_by_track"])


if __name__ == "__main__":
    unittest.main()
