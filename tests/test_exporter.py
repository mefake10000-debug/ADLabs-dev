import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.telemetry.exporter import TelemetryExporter

class FakeLocalBuffer:
    def __init__(self, rollups=None, events=None):
        self._rollups = rollups or []
        self._events = events or []
        self.marked_rollups = None
        self.marked_events = None

    def get_unexported_rollups(self, limit=50):
        return self._rollups

    def get_unexported_events(self, limit=200):
        return self._events

    def mark_as_exported(self, ids):
        self.marked_rollups = ids

    def mark_events_as_exported(self, ids):
        self.marked_events = ids

class TestTelemetryExporterRouting(unittest.TestCase):
    """M1: events must sync to a distinct endpoint from rollups and be marked
    exported independently, so a failure in one never blocks the other."""

    def test_flush_once_posts_rollups_to_base_telemetry_endpoint(self):
        buffer = FakeLocalBuffer(rollups=[{"id": 1, "in_count": 1}])
        exporter = TelemetryExporter(buffer, cloud_endpoint="http://cloud/api/v1/telemetry")

        with patch("src.telemetry.exporter.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            count = exporter.flush_once()

        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "http://cloud/api/v1/telemetry")
        self.assertEqual(count, 1)
        self.assertEqual(buffer.marked_rollups, [1])

    def test_flush_events_once_posts_to_events_subpath(self):
        buffer = FakeLocalBuffer(events=[{"id": 5, "track_id": 42}])
        exporter = TelemetryExporter(buffer, cloud_endpoint="http://cloud/api/v1/telemetry")

        with patch("src.telemetry.exporter.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            count = exporter.flush_events_once()

        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        called_payload = mock_post.call_args[1]["json"]
        self.assertEqual(called_url, "http://cloud/api/v1/telemetry/events")
        self.assertEqual(called_payload["events"], [{"id": 5, "track_id": 42}])
        self.assertEqual(count, 1)
        self.assertEqual(buffer.marked_events, [5])
        self.assertIsNone(buffer.marked_rollups)  # rollup sync untouched

    def test_events_sync_failure_does_not_affect_rollups(self):
        buffer = FakeLocalBuffer(rollups=[{"id": 1}], events=[{"id": 5}])
        exporter = TelemetryExporter(buffer, cloud_endpoint="http://cloud/api/v1/telemetry")

        def fail_events_only(url, **kwargs):
            if url.endswith("/events"):
                raise ConnectionError("cloud unreachable")
            return MagicMock(status_code=200)

        with patch("src.telemetry.exporter.requests.post", side_effect=fail_events_only):
            rollup_count = exporter.flush_once()
            event_count = exporter.flush_events_once()

        self.assertEqual(rollup_count, 1)
        self.assertEqual(buffer.marked_rollups, [1])
        self.assertEqual(event_count, 0)
        self.assertIsNone(buffer.marked_events)  # kept safe locally, not marked exported

if __name__ == "__main__":
    unittest.main()
