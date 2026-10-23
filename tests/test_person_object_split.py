"""Person tracks stay people. Objects never get a person ID or tripwire input."""
import unittest

from src.perception.detector import (
    drop_objects_on_people,
    is_person_detection,
    keep_person_detections,
)
from src.perception.tracker import SimpleByteTracker
from src.visualizer.debug_overlay import TRAIL_POINTS, trail_points
from src.perception.tracker import Track


class PersonObjectSplitTests(unittest.TestCase):
    def test_person_label_and_class(self):
        self.assertTrue(is_person_detection({"bbox": [0, 0, 10, 20], "class_id": 0, "label": "person"}))
        self.assertTrue(is_person_detection({"bbox": [0, 0, 10, 40], "confidence": 0.8}))
        self.assertFalse(is_person_detection({"bbox": [0, 0, 10, 10], "class_id": 56, "label": "chair"}))
        self.assertFalse(is_person_detection({"bbox": [0, 0, 10, 10], "label": "handbag", "class_id": 26}))

    def test_keep_person_drops_objects(self):
        dets = [
            {"bbox": [0, 0, 30, 80], "confidence": 0.9, "class_id": 0, "label": "person"},
            {"bbox": [40, 40, 80, 70], "confidence": 0.95, "class_id": 56, "label": "chair"},
        ]
        kept = keep_person_detections(dets)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["label"], "person")

    def test_object_on_person_is_dropped(self):
        people = [{"bbox": [10, 10, 80, 200], "label": "person", "class_id": 0}]
        objects = [
            {"bbox": [20, 40, 70, 120], "label": "chair", "class_id": 56, "confidence": 0.8},
            {"bbox": [200, 200, 260, 280], "label": "bottle", "class_id": 39, "confidence": 0.7},
        ]
        kept = drop_objects_on_people(objects, people)
        self.assertEqual([d["label"] for d in kept], ["bottle"])

    def test_bytetrack_ignores_objects(self):
        tracker = SimpleByteTracker(min_hits=1, track_thresh=0.3, max_age=5)
        tracks = tracker.update(
            [
                {"bbox": [10, 10, 50, 120], "confidence": 0.91, "class_id": 0, "label": "person"},
                {"bbox": [200, 200, 280, 260], "confidence": 0.99, "class_id": 56, "label": "chair"},
                {"bbox": [300, 10, 360, 40], "confidence": 0.88, "label": "tv", "class_id": 62},
            ],
            1.0,
        )
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracker._next_id, 2)

    def test_short_trail(self):
        t = Track(1, [0, 0, 10, 40], 0.9, 0.0)
        for i in range(1, 30):
            t.update([i, 0, i + 10, 40], 0.9, float(i))
        pts = trail_points(t)
        self.assertEqual(len(pts), TRAIL_POINTS)
        self.assertLessEqual(TRAIL_POINTS, 16)


if __name__ == "__main__":
    unittest.main()
