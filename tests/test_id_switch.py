import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analytics.id_switch import IdSwitchDetector
from src.perception.tracker import Track


def person(tid, x, y=300, t=0.0):
    """A 100px-tall person whose feet are at (x + 25, y)."""
    return Track(tid, [x, y - 100, x + 50, y], 0.9, t)


class TestIdSwitchDetector(unittest.TestCase):
    def setUp(self):
        self.det = IdSwitchDetector(max_gap_seconds=5.0, max_distance_heights=1.0)

    def feed(self, *frames):
        """frames: (time, [tracks]) pairs, fed in order; returns every event reported, including the
        ones still pending at the end of the clip."""
        return self.feed_no_flush(*frames) + self.det.flush()

    def feed_no_flush(self, *frames):
        events = []
        for t, tracks in frames:
            events += self.det.update(tracks, t)
        return events

    def test_ids_present_from_the_start_are_not_switches(self):
        self.assertEqual(self.feed((0.0, [person(1, 100), person(2, 400)])), [])

    def test_new_id_where_a_lost_one_was_is_flagged(self):
        events = self.feed((0.0, [person(1, 100)]), (1.0, [person(1, 100)]),
                           (2.0, []), (3.0, [person(2, 110)]))
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual((e["lost_id"], e["new_id"], e["kind"]), (1, 2, "new_id"))
        self.assertEqual(e["gap_seconds"], 2.0)
        self.assertEqual(e["distance_px"], 10.0)
        self.assertEqual(e["distance_heights"], 0.1)

    def test_switch_back_to_an_older_id_is_flagged_as_reused(self):
        # The live cashier pattern: 96 -> 187 -> 96.
        events = self.feed((0.0, [person(96, 100)]), (1.0, [person(187, 105)]), (2.0, [person(96, 100)]))
        self.assertEqual([(e["lost_id"], e["new_id"], e["kind"]) for e in events],
                         [(96, 187, "new_id"), (187, 96, "id_reused")])

    def test_same_id_coming_back_is_not_a_switch(self):
        self.assertEqual(self.feed((0.0, [person(1, 100)]), (1.0, []), (2.0, [person(1, 100)])), [])

    def test_too_far_or_too_late_is_not_flagged(self):
        far = self.feed((0.0, [person(1, 100)]), (1.0, [person(2, 300)]))  # 200px = 2 heights away
        self.det = IdSwitchDetector(max_gap_seconds=5.0)
        late = self.feed((0.0, [person(3, 100)]), (1.0, []), (7.0, [person(4, 100)]))
        self.assertEqual((far, late), ([], []))

    def test_neighbour_flickering_out_and_back_is_not_a_switch(self):
        # Two people side by side, one detection drops for a frame: the same ID coming back is itself.
        events = self.feed((0.0, [person(1, 100), person(2, 160)]), (0.1, [person(2, 160)]),
                           (0.2, [person(1, 100), person(2, 160)]))
        self.assertEqual(events, [])

    def test_ids_ever_on_screen_together_are_two_people(self):
        # 1 and 2 were both visible at t=0, so 2 later appearing where 1 vanished can't be 1's new ID.
        frames = [(0.0, [person(1, 100), person(2, 700)])]
        frames += [(float(t), [person(1, 100)]) for t in range(1, 8)]
        frames += [(8.0, []), (9.0, [person(2, 110)])]
        self.assertEqual(self.feed(*frames), [])

    def test_candidate_withdrawn_when_lost_id_returns_alongside_the_new_one(self):
        # Looks like 1 -> 3, until 1 reappears while 3 is still there: two people.
        events = self.feed((0.0, [person(1, 100)]), (1.0, [person(3, 120)]),
                           (2.0, [person(1, 100), person(3, 120)]))
        self.assertEqual(events, [])
        self.assertEqual(self.det.retracted, 1)

    def test_events_are_reported_once_the_confirmation_window_passes(self):
        early = self.feed_no_flush((0.0, [person(1, 100)]), (1.0, [person(2, 105)]), (3.0, [person(2, 105)]))
        on_time = self.det.update([person(2, 105)], 6.0)  # 5s after the candidate at t=1
        self.assertEqual((early, [(e["lost_id"], e["new_id"]) for e in on_time]), ([], [(1, 2)]))

    def test_new_id_next_to_someone_still_visible_is_not_flagged(self):
        # Person 1 never disappears, so person 3 appearing beside them is a new person, not a switch.
        events = self.feed((0.0, [person(1, 100), person(2, 400)]), (1.0, [person(1, 100), person(2, 400), person(3, 120)]))
        self.assertEqual(events, [])

    def test_one_disappearance_explains_only_one_appearance_the_nearest(self):
        # Both new IDs are within range; the nearer one wins no matter which comes first in the list.
        events = self.feed((0.0, [person(1, 100)]), (1.0, [person(3, 140), person(2, 105)]))
        self.assertEqual([(e["lost_id"], e["new_id"]) for e in events], [(1, 2)])


if __name__ == "__main__":
    unittest.main()
