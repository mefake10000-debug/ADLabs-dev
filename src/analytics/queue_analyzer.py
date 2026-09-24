import time
from typing import List, Tuple, Dict, Any
from src.perception.tracker import Track
from src.analytics.zones import Zone, point_in_polygon

class QueueAnalyzer:
    """Specialized queue analyzer for cashier and customer service counters."""

    def __init__(
        self,
        zone_id: str,
        name: str,
        polygon: List[List[float]],
        max_comfortable_queue: int = 4,
        congestion_threshold_seconds: float = 120.0,
        exit_grace_seconds: float = 3.0
    ):
        self.zone = Zone(zone_id, name, polygon, zone_type="queue", exit_grace_seconds=exit_grace_seconds)
        self.max_comfortable_queue = max_comfortable_queue
        self.congestion_threshold_seconds = congestion_threshold_seconds

        self.queue_length = 0
        self.avg_wait_seconds = 0.0
        self.alert_active = False
        self.alert_reason = ""

    def update(self, tracks: List[Track], current_time: float):
        self.zone.update(tracks, current_time)

        # Queue length is based on tracks inside the polygon that are stationary or moving slowly
        waiting_times: List[float] = []
        for tid, entry_time in self.zone.active_tracks_in_zone.items():
            dwell = current_time - entry_time
            # Only count as 'in queue' if they have stood in the zone for at least 5 seconds
            if dwell >= 5.0:
                waiting_times.append(dwell)

        self.queue_length = len(waiting_times)
        if waiting_times:
            self.avg_wait_seconds = round(sum(waiting_times) / len(waiting_times), 1)
        elif self.zone.completed_dwells:
            # Fallback to recent completed checkouts
            self.avg_wait_seconds = round(sum(self.zone.completed_dwells[-10:]) / min(len(self.zone.completed_dwells), 10), 1)
        else:
            self.avg_wait_seconds = 0.0

        # Congestion Alert Trigger
        self.alert_active = False
        self.alert_reason = ""

        if self.queue_length > self.max_comfortable_queue:
            self.alert_active = True
            self.alert_reason = f"Queue length ({self.queue_length}) exceeded capacity ({self.max_comfortable_queue})"
        elif self.avg_wait_seconds > self.congestion_threshold_seconds:
            self.alert_active = True
            self.alert_reason = f"Average wait time ({self.avg_wait_seconds}s) exceeded SLA ({self.congestion_threshold_seconds}s)"

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone.zone_id,
            "name": self.zone.name,
            "queue_length": self.queue_length,
            "avg_wait_seconds": self.avg_wait_seconds,
            "alert_active": self.alert_active,
            "alert_reason": self.alert_reason,
            "max_capacity": self.max_comfortable_queue
        }

