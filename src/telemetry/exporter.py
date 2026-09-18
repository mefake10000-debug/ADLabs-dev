import time
import logging
import requests
import threading
from typing import Optional
from src.storage.local_buffer import LocalBuffer

logger = logging.getLogger(__name__)

class TelemetryExporter:
    """Periodically pushes local SQLite rollups to the cloud telemetry endpoint."""

    def __init__(
        self,
        local_buffer: LocalBuffer,
        cloud_endpoint: str,
        local_endpoint: Optional[str] = None,
        push_interval_seconds: int = 30
    ):
        self.local_buffer = local_buffer
        self.cloud_endpoint = cloud_endpoint
        self.local_endpoint = local_endpoint
        self.push_interval = push_interval_seconds

        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._export_loop, name="TelemetryExporter", daemon=True)
        self.thread.start()
        logger.info(f"TelemetryExporter started. Pushing every {self.push_interval}s.")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info("TelemetryExporter stopped.")

    def _export_loop(self):
        while self.running:
            time.sleep(self.push_interval)
            try:
                self.flush_once()
                self.flush_events_once()
            except Exception as e:
                logger.error(f"Error in telemetry export loop: {e}")

    def flush_once(self) -> int:
        """Pushes pending unexported rollups. Returns count of successfully exported items."""
        unexported = self.local_buffer.get_unexported_rollups(limit=50)
        return self._push_batch(
            endpoints=self._endpoints(),
            records=unexported,
            payload_key="rollups",
            mark_exported=self.local_buffer.mark_as_exported
        )

    def flush_events_once(self) -> int:
        """Pushes pending unexported crossing events, independent of rollup sync."""
        unexported = self.local_buffer.get_unexported_events(limit=200)
        return self._push_batch(
            endpoints=[e + "/events" for e in self._endpoints()],
            records=unexported,
            payload_key="events",
            mark_exported=self.local_buffer.mark_events_as_exported
        )

    def _endpoints(self) -> list:
        endpoints = [self.cloud_endpoint]
        if self.local_endpoint and self.local_endpoint != self.cloud_endpoint:
            endpoints.append(self.local_endpoint)
        return endpoints

    def _push_batch(self, endpoints: list, records: list, payload_key: str, mark_exported) -> int:
        if not records:
            return 0

        for endpoint in endpoints:
            try:
                payload = {
                    "batch_size": len(records),
                    payload_key: records,
                    "exported_at": time.time()
                }
                resp = requests.post(endpoint, json=payload, timeout=5.0)
                if resp.status_code in (200, 201):
                    ids = [r["id"] for r in records]
                    mark_exported(ids)
                    logger.info(f"Successfully synced {len(ids)} {payload_key} to {endpoint}")
                    return len(ids)
            except Exception as e:
                logger.debug(f"Could not reach {endpoint}: {e}")

        logger.warning(f"Telemetry sync failed for {len(records)} {payload_key}. Keeping safe in local buffer.")
        return 0

