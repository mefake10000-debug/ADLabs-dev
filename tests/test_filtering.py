import unittest
import os
import sys
import time
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.detector import PersonDetector
from src.perception.tracker import Track, SimpleByteTracker
from src.analytics.tripwire import Tripwire


class TestFalsePositiveFiltering(unittest.TestCase):

    def test_anthropometric_filtering(self):
        detector = PersonDetector(
            model_name="yolov8n.pt",
            conf_thresh=0.50,
            min_height=85.0,
            min_width=30.0,
            min_aspect_ratio=1.0,
            max_aspect_ratio=4.2,
            min_area=3000.0
        )
        # Price tag on shelf: 40x40 px, area 1600
        w, h = 40, 40
        area = w * h
        aspect = h / max(1.0, w)
        self.assertTrue(h < detector.min_height or area < detector.min_area)

        # Wire basket / floor display: 150 wide x 80 tall, aspect 0.53
        w, h = 150, 80
        aspect = h / max(1.0, w)
        self.assertTrue(aspect < detector.min_aspect_ratio or h < detector.min_height)

        # Hair / head fragment at bottom border: 200 wide x 60 tall, aspect 0.3
        w, h = 200, 60
        aspect = h / max(1.0, w)
        self.assertTrue(aspect < detector.min_aspect_ratio or h < detector.min_height)

        # Real standing human: 70 wide x 220 tall, aspect 3.14, area 15400
        w, h = 70, 220
        area = w * h
        aspect = h / max(1.0, w)
        self.assertFalse(h < detector.min_height or w < detector.min_width)
        self.assertFalse(area < detector.min_area)
        self.assertFalse(aspect < detector.min_aspect_ratio or aspect > detector.max_aspect_ratio)

    def test_temporal_confirmation_and_stationary_suppress_policy(self):
        tracker = SimpleByteTracker(min_hits=4, stationary_policy="suppress")
        t0 = time.time()

        # Frame 1: Detection appears
        dets = [{"bbox": [100, 100, 160, 260], "confidence": 0.85, "class_id": 0}]
        active = tracker.update(dets, t0)
        # Hits = 1 -> Should be suppressed (min_hits=4)
        self.assertEqual(len(active), 0)

        # Frame 2 & 3: Hits = 2 & 3 -> Still suppressed
        tracker.update(dets, t0 + 0.1)
        active = tracker.update(dets, t0 + 0.2)
        self.assertEqual(len(active), 0)

        # Frame 4: Hits = 4 -> Now confirmed active!
        active = tracker.update(dets, t0 + 0.3)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].hits, 4)

        # Simulate stationary cardboard cutout: update 30 more times at exact same pixel position
        for i in range(30):
            active = tracker.update(dets, t0 + 0.4 + (i * 0.1))

        # After 25+ updates with 0 displacement, should be classified as static fixture
        track = tracker.tracks[0]
        self.assertTrue(track.is_stationary)
        # Suppressed from returned active list under the "suppress" policy
        self.assertEqual(len(active), 0)

        # When a real person starts moving (displacement >= 18px gradually over frames)
        for step in range(1, 6):
            shift = step * 6  # 6, 12, 18, 24, 30 px
            moving_dets = [{"bbox": [100 + shift, 100 + shift, 160 + shift, 260 + shift], "confidence": 0.88, "class_id": 0}]
            active = tracker.update(moving_dets, t0 + 5.0 + (step * 0.1))

        self.assertFalse(tracker.tracks[0].is_stationary)
        self.assertEqual(len(active), 1)

    def test_default_stationary_policy_tags_instead_of_hiding(self):
        # Regression coverage for the "fewer boxes than people in frame" / empty queue-zone
        # finding: hiding stationary tracks from the returned list made them invisible to
        # zones/queues too (a queueing customer standing still IS stationary), not just to
        # the tripwire (which already ignores the flag itself, unaffected either way).
        tracker = SimpleByteTracker(min_hits=4)  # default stationary_policy="tag"
        t0 = time.time()
        dets = [{"bbox": [100, 100, 160, 260], "confidence": 0.85, "class_id": 0}]
        for i in range(34):  # 4 to confirm (min_hits) + 30 to become stationary
            active = tracker.update(dets, t0 + i * 0.1)

        self.assertTrue(tracker.tracks[0].is_stationary)
        self.assertEqual(len(active), 1)              # NOT hidden, unlike "suppress"
        self.assertTrue(active[0].is_stationary)       # but the flag is there for callers to act on

    def test_invalid_stationary_policy_rejected(self):
        with self.assertRaises(ValueError):
            SimpleByteTracker(stationary_policy="bogus")

    def test_low_confidence_detection_never_starts_a_new_track(self):
        # ByteTrack's core anti-false-positive rule: a detection below track_thresh can extend
        # an existing track but must never spawn a new identity on its own -- otherwise every
        # noisy low-confidence blob becomes a phantom track.
        tracker = SimpleByteTracker(min_hits=1, track_thresh=0.5)
        low_det = [{"bbox": [100, 100, 160, 260], "confidence": 0.3, "class_id": 0}]
        active = tracker.update(low_det, time.time())
        self.assertEqual(active, [])
        self.assertEqual(len(tracker.tracks), 0)

    def test_low_confidence_detection_extends_an_existing_track(self):
        # This is the recovery this milestone is about: a partially-occluded person whose
        # detection confidence dips below track_thresh must still keep their track alive and
        # visible, not be dropped as an unmatched track for that frame.
        tracker = SimpleByteTracker(min_hits=1, track_thresh=0.5)
        t0 = time.time()

        high_det = [{"bbox": [100, 100, 160, 260], "confidence": 0.9, "class_id": 0}]
        active = tracker.update(high_det, t0)
        self.assertEqual(len(active), 1)
        track_id = active[0].track_id

        # Next frame: only a low-confidence detection near the same spot
        low_det = [{"bbox": [104, 104, 164, 264], "confidence": 0.3, "class_id": 0}]
        active = tracker.update(low_det, t0 + 0.1)

        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].track_id, track_id)   # same identity, not a miss
        self.assertEqual(active[0].time_since_update, 0)  # box rendered this frame, not marked missed
        self.assertEqual(len(tracker.tracks), 1)          # no phantom second track from the low-conf box

    def test_high_confidence_detection_preferred_over_low_confidence_for_the_same_track(self):
        # When both a high- and a low-confidence detection are candidates in the same frame
        # (e.g. a real person plus a weak duplicate/ghost box), the existing 3-stage matcher
        # already runs on the high-confidence set first, so it should win the match.
        tracker = SimpleByteTracker(min_hits=1, track_thresh=0.5)
        t0 = time.time()
        tracker.update([{"bbox": [100, 100, 160, 260], "confidence": 0.9, "class_id": 0}], t0)

        dets = [
            {"bbox": [500, 500, 560, 660], "confidence": 0.3, "class_id": 0},   # far away, low-conf
            {"bbox": [103, 103, 163, 263], "confidence": 0.9, "class_id": 0},   # near, high-conf
        ]
        active = tracker.update(dets, t0 + 0.1)
        self.assertEqual(len(active), 1)
        self.assertAlmostEqual(active[0].bbox[0], 103, delta=1)  # matched the high-conf box, not the low-conf one

    def test_detector_without_a_model_returns_nothing_but_says_so(self):
        # There is no lower-accuracy fallback detector any more (the HOG one recovered ~7-14% of people on
        # real footage). A detector whose model failed to load must not look like a working one.
        with patch.dict(sys.modules, {"ultralytics": None}):   # makes `from ultralytics import YOLO` fail
            detector = PersonDetector(model_name="yolov8n.pt")
        self.assertIsNone(detector.model)
        with self.assertLogs("src.perception.detector", level="ERROR") as logs:
            self.assertEqual(detector.detect(object()), [])
        self.assertIn("no model loaded", logs.output[0])

    def test_require_model_makes_a_failed_model_load_a_startup_error(self):
        with patch.dict(sys.modules, {"ultralytics": None}):
            with self.assertRaises(RuntimeError) as ctx:
                PersonDetector(model_name="yolov8n.pt", require_model=True)
        self.assertIn("Refusing to run without a working detector", str(ctx.exception))

    def test_tripwire_lifetime_deduping(self):
        tw = Tripwire(
            wire_id="tw_main",
            name="Entrance",
            line=[[500, 500], [1000, 500]],
            in_direction="top_to_bottom"
        )
        now = time.time()
        # Track walks across line
        track = Track(track_id=42, bbox=[600, 400, 660, 480], confidence=0.9, timestamp=now)
        track.update([600, 450, 660, 530], 0.9, now + 0.1)

        # First crossing: counted IN
        tw.update([track], now + 0.1)
        self.assertEqual(tw.in_count, 1)

        # Track stays near the line for 10 seconds (in old code, would re-trigger every 5s)
        track.update([600, 460, 660, 540], 0.9, now + 1.0)
        tw.update([track], now + 1.0)
        track.update([600, 440, 660, 520], 0.9, now + 6.0)
        tw.update([track], now + 6.0)

        # Count MUST remain exactly 1
        self.assertEqual(tw.in_count, 1)

if __name__ == "__main__":
    unittest.main()
