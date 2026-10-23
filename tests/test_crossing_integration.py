"""Integration: detections → ByteTrack → foot → tripwire / zone dwell.

Same order as ``EdgePipeline`` (early tracks on the line, staff left out).
No video and no weights.
"""
from __future__ import annotations

import importlib.util
import os
import time
import unittest

from src.analytics.tripwire import Tripwire
from src.analytics.zones import Zone
from src.perception.tracker import SimpleByteTracker, Track


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_PASS_THROUGH = [
    [200, 80, 260, 340],
    [210, 120, 270, 390],
    [220, 170, 280, 450],
]


def _drive(boxes, *, use_early: bool, min_hits: int = 4):
    tracker = SimpleByteTracker(min_hits=min_hits, iou_threshold=0.2, dist_gate=120, pred_dist_gate=160)
    tw = Tripwire("door", "Entrance", [[0, 400], [1000, 400]], in_direction="top_to_bottom")
    zone = Zone("welcome", "Welcome", [[0, 0], [500, 0], [500, 520], [0, 520]])
    t0 = time.time()
    events = []
    for i, bbox in enumerate(boxes):
        ts = t0 + i * 0.2
        confirmed = tracker.update([{"bbox": bbox, "confidence": 0.92, "class_id": 0}], ts)
        seen = tracker.early_tracks() if use_early else confirmed
        events.extend(tw.update(seen, ts))
        zone.update(seen, ts)
    return tw, zone, events


class CrossingIntegrationTests(unittest.TestCase):
    def test_early_tracks_count_crossing_confirmed_list_misses_it(self):
        early_tw, early_zone, early_events = _drive(_PASS_THROUGH, use_early=True)
        late_tw, late_zone, late_events = _drive(_PASS_THROUGH, use_early=False)
        self.assertEqual(len(early_events), 1)
        self.assertEqual(early_events[0]["direction"], "in")
        self.assertEqual(early_tw.in_count, 1)
        self.assertEqual(late_events, [])
        self.assertEqual(late_tw.in_count, 0)
        self.assertGreaterEqual(early_zone.get_metrics()["current_occupancy"], 1)
        self.assertEqual(late_zone.get_metrics()["current_occupancy"], 0)

    def test_staying_visitor_counts_once(self):
        boxes = _PASS_THROUGH + [[230, 180, 290, 470]]
        early_tw, early_zone, _ = _drive(boxes, use_early=True)
        late_tw, late_zone, _ = _drive(boxes, use_early=False)
        self.assertEqual(early_tw.in_count, 1)
        self.assertEqual(late_tw.in_count, 1)
        self.assertGreaterEqual(early_zone.get_metrics()["current_occupancy"], 1)
        self.assertGreaterEqual(late_zone.get_metrics()["current_occupancy"], 1)

    def test_staff_id_is_not_a_visitor_crossing(self):
        tracker = SimpleByteTracker(min_hits=2, iou_threshold=0.2, dist_gate=120)
        tw = Tripwire("door", "Entrance", [[0, 400], [1000, 400]], in_direction="top_to_bottom")
        t0 = time.time()
        staff_ids = set()
        for i, bbox in enumerate(_PASS_THROUGH):
            ts = t0 + i * 0.2
            tracker.update([{"bbox": bbox, "confidence": 0.95, "class_id": 0}], ts)
            seen = tracker.early_tracks()
            if seen:
                staff_ids.add(seen[0].track_id)
            customers = [t for t in seen if t.track_id not in staff_ids]
            self.assertEqual(tw.update(customers, ts), [])
        self.assertEqual(tw.in_count, 0)

    def test_ankle_rewrites_trail_and_crosses(self):
        tw = Tripwire("door", "Entrance", [[0, 400], [1000, 400]], in_direction="top_to_bottom")
        now = time.time()
        track = Track(4, [200, 80, 260, 340], 0.9, now - 0.2)
        track.update([200, 100, 260, 370], 0.9, now)
        self.assertEqual(tw.update([track], now), [])
        track.set_pose(foot=(230.0, 430.0))
        events = tw.update([track], now)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["direction"], "in")
        live = track.to_live_dict()
        self.assertEqual(live["ground_point"][1], 430.0)
        self.assertEqual(live["foot"][1], 430.0)

    def test_main_uses_one_annotator_and_early_line(self):
        with open(os.path.join(ROOT, "src", "main.py"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertEqual(text.count("DebugOverlay.draw_pipeline("), 1)
        self.assertIn("tw.update(early_customers", text)
        self.assertIn("self._update_analytics(", text)
        self.assertIn("_apply_rtmpose_feet(early_tracks", text)
        self.assertNotIn("draw_pipeline(**draw_kwargs)", text)


class LicenseSkipTests(unittest.TestCase):
    def test_nc_models_stay_skipped_rtmpose_is_apache(self):
        script = os.path.join(ROOT, "scripts", "download_pack_models_phase2.py")
        spec = importlib.util.spec_from_file_location("phase2_pack", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        skipped = {it["id"] for it in mod.ITEMS if it.get("skip")}
        self.assertIn("locateanything-3b", skipped)
        self.assertIn("sku110k", skipped)
        self.assertIn("p2pnet", skipped)
        rtm = next(it for it in mod.ITEMS if it["id"] == "rtmpose-t")
        self.assertFalse(rtm.get("skip"))
        self.assertIn("Apache", rtm["license"])


if __name__ == "__main__":
    unittest.main()
