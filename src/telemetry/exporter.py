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
        push_interval_seconds: int = 30,
        api_key: Optional[str] = None
    ):
        self.local_buffer = local_buffer
        self.cloud_endpoint = cloud_endpoint
        self.local_endpoint = local_endpoint
        self.push_interval = push_interval_seconds
        self.api_key = api_key

        self.running = False
        self._stop_event = threading.Event()
        self._last_maintenance = 0.0
        self.thread: Optional[threading.Thread] = None

    def start(self):
        if self.running:
            return
        self._stop_event.clear()
        self.running = True
        self.thread = threading.Thread(target=self._export_loop, name="TelemetryExporter", daemon=True)
        self.thread.start()
        logger.info(f"TelemetryExporter started. Pushing every {self.push_interval}s.")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=16.0)
        logger.info("TelemetryExporter stopped.")

    def _export_loop(self):
        while not self._stop_event.wait(self.push_interval):
            try:
                self.flush_once()
                self.flush_events_once()
                self.flush_products_once()
                if time.monotonic() - self._last_maintenance >= 3600 and hasattr(self.local_buffer, "maintenance"):
                    self.local_buffer.maintenance()
                    self._last_maintenance = time.monotonic()
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

    def flush_products_once(self) -> int:
        """Pushes pending unexported product-interest rows.

        These carry category, viewer count and dwell time. No face, no image and no
        person-level record is ever included -- a row is a per-category aggregate for
        one camera over one rollup window.
        """
        unexported = self.local_buffer.get_unexported_products(limit=200)
        return self._push_batch(
            endpoints=[e + "/products" for e in self._endpoints()],
            records=unexported,
            payload_key="products",
            mark_exported=self.local_buffer.mark_products_as_exported
        )

    def _endpoints(self) -> list:
        """Ordered fallback destinations; the first accepting receiver owns delivery."""
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
                headers = {"X-API-Key": self.api_key} if self.api_key else {}
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=5.0)
                if resp.status_code in (200, 201):
                    body = resp.json()
                    acknowledgements = body.get("accepted_record_ids") if isinstance(body, dict) else None
                    if isinstance(acknowledgements, list):
                        accepted = {value for value in acknowledgements if isinstance(value, str)}
                        ids = [r["id"] for r in records if r.get("record_id") in accepted]
                    elif any(r.get("record_id") for r in records):
                        logger.warning("Receiver did not acknowledge durable record IDs; keeping batch pending")
                        continue
                    else:
                        ids = [r["id"] for r in records]  # legacy sender compatibility
                    if not ids:
                        continue
                    mark_exported(ids)
                    logger.info(f"Successfully synced {len(ids)} {payload_key} to {endpoint}")
                    return len(ids)
            except Exception as e:
                logger.debug(f"Could not reach {endpoint}: {e}")

        logger.warning(f"Telemetry sync failed for {len(records)} {payload_key}. Keeping safe in local buffer.")
        return 0

