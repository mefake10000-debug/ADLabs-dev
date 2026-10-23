"""Person boxes are the only ByteTrack input; objects stay labels."""
import unittest

from src.perception.detector import PersonDetector
from src.perception.tracker import SimpleByteTracker, is_person_detection


class PersonObjectSplitTests(unittest.TestCase):
    def test_is_person_detection(self):
        self.assertTrue(is_person_detection({"bbox": [0, 0, 10, 40], "confidence": 0.4}))
        self.assertTrue(is_person_detection({"bbox": [0, 0, 10, 40], "confidence": 0.4, "class_id": 0, "label": "person"}))
        self.assertFalse(is_person_detection({"bbox": [0, 0, 10, 40], "confidence": 0.9, "class_id": 56, "label": "chair"}))
        self.assertFalse(is_person_detection({"bbox": [0, 0, 10, 40], "confidence": 0.9, "label": "backpack"}))

    def test_tracker_ignores_objects(self):
        tracker = SimpleByteTracker(min_hits=1, track_thresh=0.25, max_age=5)
        tracks = tracker.update(
            [
                {"bbox": [10, 10, 40, 120], "confidence": 0.8, "class_id": 56, "label": "chair"},
                {"bbox": [100, 20, 160, 200], "confidence": 0.4, "class_id": 0, "label": "person"},
            ],
            1.0,
        )
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].track_id, 1)
        tracker.update(
            [{"bbox": [12, 12, 42, 122], "confidence": 0.95, "class_id": 62, "label": "tv"}],
            1.2,
        )
        self.assertEqual(len(tracker.tracks), 1)
        self.assertEqual(tracker._next_id, 2)

    def test_object_on_person_is_dropped(self):
        people = [{"bbox": [0, 0, 100, 200], "label": "person"}]
        objects = [
            {"bbox": [5, 5, 95, 190], "label": "chair"},
            {"bbox": [180, 40, 230, 90], "label": "bottle"},
            {"bbox": [20, 40, 50, 80], "label": "person"},
        ]
        kept = PersonDetector._drop_objects_on_people(people, objects)
        self.assertEqual([o["label"] for o in kept], ["bottle"])


if __name__ == "__main__":
    unittest.main()
