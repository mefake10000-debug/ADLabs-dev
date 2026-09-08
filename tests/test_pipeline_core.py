import unittest
import os
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.local_buffer import LocalBuffer
from src.ingestion.frame_buffer import FrameBuffer
from src.perception.tracker import Track, SimpleByteTracker
from src.analytics.tripwire import Tripwire, intersect
from src.analytics.zones import Zone, point_in_polygon
from src.analytics.queue_analyzer import QueueAnalyzer

class TestEdgeSightCore(unittest.TestCase):

    def test_local_buffer_storage(self):
        db_path = "data/storage/test_edgesight.db"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

        buffer = LocalBuffer(db_path=db_path)
        rollup = {
            "store_id": "test_store",
            "device_id": "test_mac_01",
            "camera_id": "cam_entrance",
            "timestamp_start": "2026-09-07 10:00:00",
            "timestamp_end": "2026-09-07 10:00:30",
            "in_count": 12,
            "out_count": 5,
            "current_occupancy": 7,
            "avg_dwell_seconds": 45.2,
            "queue_length": 2,
            "avg_queue_wait_seconds": 30.0,
            "queue_alert_active": 0
        }
        row_id = buffer.save_rollup(rollup)
        self.assertGreater(row_id, 0)

        unexported = buffer.get_unexported_rollups(limit=10)
        self.assertEqual(len(unexported), 1)
        self.assertEqual(unexported[0]["in_count"], 12)
        self.assertEqual(unexported[0]["out_count"], 5)

        buffer.mark_as_exported([row_id])
        remaining = buffer.get_unexported_rollups(limit=10)
        self.assertEqual(len(remaining), 0)

        # Allow garbage collection to release SQLite lock on Windows
        del buffer
        import gc
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_frame_buffer_ring_drop(self):
        fb = FrameBuffer(maxsize=3)
        fb.put(1, 100.0, "frame1")
        fb.put(2, 101.0, "frame2")
        fb.put(3, 102.0, "frame3")
        fb.put(4, 103.0, "frame4")  # Should drop frame1

        self.assertEqual(fb.size(), 3)
        idx, ts, f = fb.get()
        self.assertEqual(idx, 2)

    def test_tripwire_crossing(self):
        # Line at y=360 from x=400 to x=880
        tw = Tripwire(
            wire_id="tw_01",
            name="Main Door",
            line=[[400, 360], [880, 360]],
            in_direction="top_to_bottom"
        )

        now = time.time()
        # Track moving downwards from y=300 to y=420 (entering)
        track_in = Track(track_id=1, bbox=[580, 250, 620, 350], confidence=0.9, timestamp=now - 0.1)
        track_in.update([580, 320, 620, 420], 0.9, now)

        tw.update([track_in], now)
        counts = tw.get_counts()
        self.assertEqual(counts["in_count"], 1)
        self.assertEqual(counts["out_count"], 0)

        # Track moving upwards from y=420 to y=300 (exiting)
        track_out = Track(track_id=2, bbox=[680, 320, 720, 420], confidence=0.9, timestamp=now - 0.1)
        track_out.update([680, 250, 720, 350], 0.9, now)

        tw.update([track_out], now)
        counts = tw.get_counts()
        self.assertEqual(counts["out_count"], 1)

    def test_zone_point_in_polygon_and_dwell(self):
        # Polygon square from (100, 100) to (300, 300)
        poly = [[100, 100], [300, 100], [300, 300], [100, 300]]
        self.assertTrue(point_in_polygon((200, 200), [(100, 100), (300, 100), (300, 300), (100, 300)]))
        self.assertFalse(point_in_polygon((50, 50), [(100, 100), (300, 100), (300, 300), (100, 300)]))

        zone = Zone("z_01", "Promo Area", poly, "dwell")
        t0 = time.time()
        # Track inside polygon (foot point at 200, 200)
        track = Track(track_id=10, bbox=[180, 100, 220, 200], confidence=0.85, timestamp=t0)

        zone.update([track], t0)
        self.assertEqual(zone.current_occupancy, 1)

        # 3 seconds later, track is still inside
        zone.update([track], t0 + 3.0)
        self.assertEqual(zone.current_occupancy, 1)

        # Track leaves polygon
        track.update([500, 500, 540, 600], 0.85, t0 + 5.0)
        zone.update([track], t0 + 5.0)
        self.assertEqual(zone.current_occupancy, 0)
        metrics = zone.get_metrics()
        self.assertGreaterEqual(metrics["avg_dwell_seconds"], 3.0)

    def test_queue_analyzer_alert(self):
        poly = [[400, 200], [800, 200], [800, 600], [400, 600]]
        qa = QueueAnalyzer("q_01", "Counter", poly, max_comfortable_queue=2, congestion_threshold_seconds=10.0)

        t0 = time.time()
        # Create 3 waiting people inside queue polygon (foot points at y=350, within 200..600)
        t1 = Track(1, [450, 250, 500, 350], 0.9, t0)
        t2 = Track(2, [550, 250, 600, 350], 0.9, t0)
        t3 = Track(3, [650, 250, 700, 350], 0.9, t0)

        # Initial entry into queue at t0
        qa.update([t1, t2, t3], t0)
        # After 6 seconds of standing still in queue
        qa.update([t1, t2, t3], t0 + 6.0)

        self.assertEqual(qa.queue_length, 3)
        self.assertTrue(qa.alert_active)  # Exceeded max_comfortable_queue (2)

if __name__ == "__main__":
    unittest.main()
