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
from src.main import EdgePipeline

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

    def test_frame_buffer_put_drops_oldest_when_full(self):
        fb = FrameBuffer(maxsize=3)
        fb.put(1, 100.0, "frame1")
        fb.put(2, 101.0, "frame2")
        fb.put(3, 102.0, "frame3")
        fb.put(4, 103.0, "frame4")  # queue already at maxsize -> oldest (1) dropped

        self.assertEqual(fb.size(), 3)

    def test_frame_buffer_get_returns_newest_and_drains_backlog(self):
        # Regression: get() used to be FIFO. If inference (the consumer) is slower than
        # decode (the producer), a FIFO consumer permanently lags by the whole backlog and
        # never catches up to real time. Returning the newest frame and dropping the rest
        # bounds that lag to at most one buffer's worth of time.
        fb = FrameBuffer(maxsize=5)
        fb.put(1, 100.0, "frame1")
        fb.put(2, 101.0, "frame2")
        fb.put(3, 102.0, "frame3")

        idx, ts, frame = fb.get()
        self.assertEqual(idx, 3)
        self.assertEqual(frame, "frame3")
        self.assertEqual(fb.size(), 0)  # the stale backlog was discarded, not queued for later

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

    def test_tripwire_crossing_emits_persistable_event(self):
        # Regression coverage for M1: Tripwire.update must return a discrete
        # crossing event (not just update in-memory counters) so main.py can
        # persist it durably, independent of the 10s rollup cycle.
        tw = Tripwire(
            wire_id="tw_01",
            name="Main Door",
            line=[[400, 360], [880, 360]],
            in_direction="top_to_bottom"
        )
        now = time.time()
        track_in = Track(track_id=42, bbox=[580, 250, 620, 350], confidence=0.9, timestamp=now - 0.1)
        track_in.update([580, 320, 620, 420], 0.9, now)

        events = tw.update([track_in], now)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["track_id"], 42)
        self.assertEqual(events[0]["direction"], "in")
        self.assertEqual(events[0]["wire_id"], "tw_01")

        # A track that doesn't cross produces no event
        self.assertEqual(tw.update([track_in], now), [])

        db_path = "data/storage/test_events.db"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass
        buffer = LocalBuffer(db_path=db_path)
        row_id = buffer.save_event({
            "store_id": "test_store",
            "device_id": "test_mac_01",
            "camera_id": "cam_entrance",
            "wire_id": events[0]["wire_id"],
            "track_id": events[0]["track_id"],
            "direction": events[0]["direction"],
            "event_timestamp": "2026-09-18 10:00:00"
        })
        self.assertGreater(row_id, 0)
        saved = buffer.get_unexported_events(limit=10)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["track_id"], 42)
        self.assertEqual(saved[0]["camera_id"], "cam_entrance")
        self.assertEqual(saved[0]["direction"], "in")

        del buffer
        import gc
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_crossing_events_survive_independent_of_rollup(self):
        # Regression/crash-recovery coverage for M1: events must be durable as
        # soon as they occur, not only once a rollup happens to flush.
        db_path = "data/storage/test_events_independent.db"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

        pipeline = EdgePipeline.__new__(EdgePipeline)
        pipeline.store_id = "test_store"
        pipeline.device_id = "test_mac_01"
        pipeline.local_buffer = LocalBuffer(db_path=db_path)

        tw = Tripwire("tw_01", "Main Door", [[400, 360], [880, 360]], in_direction="top_to_bottom")
        now = time.time()
        track_in = Track(track_id=7, bbox=[580, 250, 620, 350], confidence=0.9, timestamp=now - 0.1)
        track_in.update([580, 320, 620, 420], 0.9, now)
        events = tw.update([track_in], now)
        self.assertEqual(len(events), 1)

        # Persist the crossing event only -- deliberately never call
        # _generate_and_save_rollup, simulating a crash before the next
        # rollup boundary.
        pipeline._persist_crossing_events("cam_01", events)

        saved_events = pipeline.local_buffer.get_unexported_events(limit=10)
        saved_rollups = pipeline.local_buffer.get_unexported_rollups(limit=10)
        self.assertEqual(len(saved_events), 1)
        self.assertEqual(saved_events[0]["direction"], "in")
        self.assertEqual(saved_events[0]["track_id"], 7)
        self.assertEqual(len(saved_rollups), 0)

        del pipeline
        import gc
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

    def test_zone_point_in_polygon_and_dwell(self):
        # Polygon square from (100, 100) to (300, 300)
        poly = [[100, 100], [300, 100], [300, 300], [100, 300]]
        self.assertTrue(point_in_polygon((200, 200), [(100, 100), (300, 100), (300, 300), (100, 300)]))
        self.assertFalse(point_in_polygon((50, 50), [(100, 100), (300, 100), (300, 300), (100, 300)]))

        # exit_grace_seconds=0 here to test polygon/dwell mechanics in isolation --
        # see test_zone_exit_grace_period below for the grace-period behavior itself.
        zone = Zone("z_01", "Promo Area", poly, "dwell", exit_grace_seconds=0)
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

    def test_zone_exit_grace_period_survives_a_brief_detection_gap(self):
        # Regression coverage for the empty-queue-columns finding: a single missed detection
        # (occlusion, one bad frame) used to immediately reset dwell/occupancy. A person who
        # briefly drops out of detection and reappears in the same spot should read as having
        # never left.
        poly = [[100, 100], [300, 100], [300, 300], [100, 300]]
        zone = Zone("z_01", "Promo Area", poly, "dwell", exit_grace_seconds=3.0)
        t0 = time.time()
        track = Track(track_id=10, bbox=[180, 100, 220, 200], confidence=0.85, timestamp=t0)

        zone.update([track], t0)
        self.assertEqual(zone.current_occupancy, 1)

        # Detection missed for 1 second (well within the 3s grace period) -- track absent from
        # the `tracks` list passed to update() entirely, as if the detector missed that frame
        zone.update([], t0 + 1.0)
        self.assertEqual(zone.current_occupancy, 1)          # still counted as present
        self.assertIn(10, zone.active_tracks_in_zone)          # entry_time preserved, not reset

        # Reappears at t0+1.5s, still inside the polygon
        track.update([180, 100, 220, 200], 0.85, t0 + 1.5)
        zone.update([track], t0 + 1.5)
        self.assertEqual(zone.current_occupancy, 1)
        self.assertEqual(zone.active_tracks_in_zone[10], t0)  # dwell clock never reset

        # Now genuinely gone for longer than the grace period -> exit finalizes
        zone.update([], t0 + 5.0)
        self.assertEqual(zone.current_occupancy, 0)
        self.assertGreaterEqual(zone.completed_dwells[-1], 3.9)  # ~t0+5.0 minus entry at t0

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

    def test_rollup_includes_queue_metrics(self):
        # Regression test for M0: _generate_and_save_rollup used to hardcode
        # queue_length/avg_queue_wait_seconds/queue_alert_active to zero instead
        # of reading them from the camera's QueueAnalyzer instances.
        db_path = "data/storage/test_rollup_queue.db"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

        pipeline = EdgePipeline.__new__(EdgePipeline)
        pipeline.store_id = "test_store"
        pipeline.device_id = "test_mac_01"
        pipeline.local_buffer = LocalBuffer(db_path=db_path)

        poly = [[400, 200], [800, 200], [800, 600], [400, 600]]
        qa = QueueAnalyzer("q_01", "Counter", poly, max_comfortable_queue=2, congestion_threshold_seconds=10.0)
        t0 = time.time()
        t1 = Track(1, [450, 250, 500, 350], 0.9, t0)
        t2 = Track(2, [550, 250, 600, 350], 0.9, t0)
        t3 = Track(3, [650, 250, 700, 350], 0.9, t0)
        qa.update([t1, t2, t3], t0)
        qa.update([t1, t2, t3], t0 + 6.0)  # 3 people waiting >5s -> non-zero queue metrics

        ctx = {
            "tripwires": [],
            "zones": [],
            "queues": [qa],
            "tracked_ids_today": {1, 2, 3},
            "last_unique_count": 0,
            "current_active_tracks": [t1, t2, t3],
            "rollup_start_time": t0,
        }

        pipeline._generate_and_save_rollup("cam_01", ctx, t0 + 6.0)

        saved = pipeline.local_buffer.get_unexported_rollups(limit=10)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["queue_length"], 3)
        self.assertGreater(saved[0]["avg_queue_wait_seconds"], 0.0)
        self.assertEqual(saved[0]["queue_alert_active"], 1)

        del pipeline
        import gc
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

if __name__ == "__main__":
    unittest.main()
