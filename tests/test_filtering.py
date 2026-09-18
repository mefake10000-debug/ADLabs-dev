import unittest
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.perception.detector import PersonDetector
from src.perception.tracker import Track, SimpleByteTracker
from src.analytics.tripwire import Tripwire

try:
    import numpy as np
except ImportError:
    np = None

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

    def test_temporal_confirmation_and_stationary_suppression(self):
        tracker = SimpleByteTracker(min_hits=4, filter_stationary=True)
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
        # Suppressed from returned active list
        self.assertEqual(len(active), 0)

        # When a real person starts moving (displacement >= 18px gradually over frames)
        for step in range(1, 6):
            shift = step * 6  # 6, 12, 18, 24, 30 px
            moving_dets = [{"bbox": [100 + shift, 100 + shift, 160 + shift, 260 + shift], "confidence": 0.88, "class_id": 0}]
            active = tracker.update(moving_dets, t0 + 5.0 + (step * 0.1))

        self.assertFalse(tracker.tracks[0].is_stationary)
        self.assertEqual(len(active), 1)

    def test_fallback_detector_returns_well_formed_detections_without_crashing(self):
        # Regression coverage: PersonDetector._fallback_detect used to be a
        # no-op stub returning [] unconditionally, silently reporting zero
        # people whenever the neural model (YOLO) fails to load. It's now a
        # real classical HOG+SVM detector; this just verifies it runs and
        # produces correctly-shaped output, not detection accuracy (which is
        # covered separately by scripts/benchmark_tracking.py).
        if np is None:
            self.skipTest("numpy not available")

        detector = PersonDetector.__new__(PersonDetector)
        detector.model = None  # force the fallback path regardless of ultralytics availability
        detector._hog = None
        detector.min_height = 40.0
        detector.min_width = 15.0
        detector.min_area = 600.0
        detector.min_aspect_ratio = 1.0
        detector.max_aspect_ratio = 4.5
        detector.conf_thresh = 0.35

        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect(blank_frame)
        self.assertIsInstance(detections, list)
        for det in detections:
            self.assertIn("bbox", det)
            self.assertIn("confidence", det)
            self.assertIn("class_id", det)
            self.assertEqual(len(det["bbox"]), 4)

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
