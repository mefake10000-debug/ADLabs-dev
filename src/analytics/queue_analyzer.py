"""Queue analyzer — length/wait (LIVE) + join/leave episodes with honest abandon=null."""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from src.perception.tracker import Track
from src.analytics.zones import Zone


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + "Z"


class QueueAnalyzer:
    """Specialized queue analyzer for cashier and customer service counters."""

    def __init__(
        self,
        zone_id: str,
        name: str,
        polygon: List[List[float]],
        max_comfortable_queue: int = 4,
        congestion_threshold_seconds: float = 120.0,
        exit_grace_seconds: float = 3.0,
        service_point: Optional[List[float]] = None,
        service_radius_frac: float = 0.05,
        alert_wait_ms: Optional[int] = None,
        alert_length: Optional[int] = None,
        staff_zone_id: Optional[str] = None,
        min_samples_p95: int = 20,
        frame_min_dim: float = 720.0,
    ):
        self.zone = Zone(
            zone_id, name, polygon, zone_type="queue", exit_grace_seconds=exit_grace_seconds
        )
        self.zone_id = zone_id
        self.name = name
        self.max_comfortable_queue = max_comfortable_queue
        self.congestion_threshold_seconds = congestion_threshold_seconds
        self.service_point = (
            (float(service_point[0]), float(service_point[1])) if service_point else None
        )
        self.service_radius = float(service_radius_frac) * float(frame_min_dim)
        self.alert_wait_ms = alert_wait_ms or int(congestion_threshold_seconds * 1000)
        self.alert_length = alert_length or max_comfortable_queue
        self.staff_zone_id = staff_zone_id
        self.min_samples_p95 = min_samples_p95

        self.queue_length = 0
        self.avg_wait_seconds = 0.0
        self.alert_active = False
        self.alert_reason = ""

        self._episodes: Dict[int, Dict[str, Any]] = {}
        self._completed: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._series: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._last_series_t = 0.0
        self.pending_events: List[Dict[str, Any]] = []
        self._staff_on_post = 0
        self._inflight_ms: List[int] = []

    def update(self, tracks: List[Track], current_time: float, staff_on_post: int = 0):
        prev_ids = set(self.zone.active_tracks_in_zone.keys())
        self.zone.update(tracks, current_time)
        now_ids = set(self.zone.active_tracks_in_zone.keys())
        events: List[Dict[str, Any]] = []

        for tid in now_ids - prev_ids:
            join_ts = self.zone.active_tracks_in_zone[tid]
            self._episodes[tid] = {"join_ts": join_ts, "near_service": False, "path_feet": []}
            events.append({
                "event": "queue_join",
                "queue_id": self.zone_id,
                "track_id": tid,
                "join_ts": _iso(join_ts),
                "queue_length_at_join": len(now_ids),
                "wire_id": self.zone_id,
                "direction": "queue_join",
                "timestamp": join_ts,
            })

        by_id = {t.track_id: t for t in tracks}
        for tid in now_ids:
            ep = self._episodes.get(tid)
            if not ep:
                continue
            tr = by_id.get(tid)
            if tr is None:
                continue
            foot = tr.foot_point
            ep["path_feet"].append(foot)
            if len(ep["path_feet"]) > 120:
                ep["path_feet"] = ep["path_feet"][-120:]
            if self.service_point is not None:
                dx = foot[0] - self.service_point[0]
                dy = foot[1] - self.service_point[1]
                if (dx * dx + dy * dy) ** 0.5 <= self.service_radius:
                    ep["near_service"] = True

        for tid in prev_ids - now_ids:
            ep = self._episodes.pop(tid, None)
            if not ep:
                continue
            leave_ts = current_time
            wait_ms = int(max(0.0, leave_ts - ep["join_ts"]) * 1000)
            outcome = "unknown"
            abandon: Optional[bool] = None
            evidence = None
            if self.service_point is not None:
                if ep["near_service"]:
                    outcome, abandon, evidence = "served", False, "service_point"
                else:
                    outcome, abandon, evidence = "abandoned", True, "no_service_contact"
            row = {
                "track_id": tid,
                "join_ts": _iso(ep["join_ts"]),
                "leave_ts": _iso(leave_ts),
                "wait_ms": wait_ms,
                "outcome": outcome,
                "abandon": abandon,
                "service_evidence": evidence,
            }
            self._completed.append(row)
            events.append({
                "event": "queue_leave",
                "queue_id": self.zone_id,
                "track_id": tid,
                **row,
                "wire_id": self.zone_id,
                "direction": "queue_leave",
                "timestamp": leave_ts,
            })

        waiting_times: List[float] = []
        inflight_ms: List[int] = []
        for tid, entry_time in self.zone.active_tracks_in_zone.items():
            dwell = current_time - entry_time
            if dwell >= 5.0:
                waiting_times.append(dwell)
                inflight_ms.append(int(dwell * 1000))

        self.queue_length = len(waiting_times)
        if waiting_times:
            self.avg_wait_seconds = round(sum(waiting_times) / len(waiting_times), 1)
        elif self.zone.completed_dwells:
            self.avg_wait_seconds = round(
                sum(self.zone.completed_dwells[-10:]) / min(len(self.zone.completed_dwells), 10), 1
            )
        else:
            self.avg_wait_seconds = 0.0

        self.alert_active = False
        self.alert_reason = ""
        if self.queue_length > self.alert_length:
            self.alert_active = True
            self.alert_reason = (
                f"Queue length ({self.queue_length}) exceeded capacity ({self.alert_length})"
            )
        elif self.avg_wait_seconds > self.congestion_threshold_seconds:
            self.alert_active = True
            self.alert_reason = (
                f"Average wait time ({self.avg_wait_seconds}s) exceeded SLA "
                f"({self.congestion_threshold_seconds}s)"
            )

        if current_time - self._last_series_t >= 1.0:
            self._series.append({"t": _iso(current_time), "length": self.queue_length})
            self._last_series_t = current_time

        if inflight_ms and max(inflight_ms) > self.alert_wait_ms:
            events.append({
                "event": "queue_wait_ms_reached",
                "queue_id": self.zone_id,
                "value_ms": max(inflight_ms),
                "threshold_ms": self.alert_wait_ms,
                "wire_id": self.zone_id,
                "direction": "queue_wait_ms_reached",
                "timestamp": current_time,
            })

        self._staff_on_post = staff_on_post
        self._inflight_ms = inflight_ms
        self.pending_events.extend(events)
        return events

    def _kpi_window(self) -> Dict[str, Any]:
        completed = list(self._completed)
        served = sum(1 for e in completed if e.get("outcome") == "served")
        abandoned = sum(1 for e in completed if e.get("abandon") is True)
        unknown = sum(1 for e in completed if e.get("outcome") == "unknown")
        waits = [e["wait_ms"] for e in completed if e.get("wait_ms") is not None]
        avg_wait_ms = int(sum(waits) / len(waits)) if waits else None
        p95 = None
        p95_available = False
        if len(waits) >= self.min_samples_p95:
            ordered = sorted(waits)
            idx = max(0, int(round(0.95 * (len(ordered) - 1))))
            p95 = ordered[idx]
            p95_available = True
        service_rate = None
        basis = None
        abandon_rate = None
        empty = len(completed) == 0
        if self.service_point is not None:
            basis = "service_point"
            if (served + abandoned) > 0:
                service_rate = round(served / (served + abandoned), 3)
                abandon_rate = round(abandoned / (served + abandoned), 3)
            else:
                # Calibrated service point, no settled outcomes yet — measured empty 0
                service_rate = 0.0
                abandon_rate = 0.0
        return {
            "completed": len(completed),
            "served": served,
            "abandoned": abandoned,
            "unknown_outcome": unknown,
            "avg_wait_ms": avg_wait_ms if waits else (0 if empty else avg_wait_ms),
            "p95_wait_ms": p95,
            "p95_available": p95_available,
            "p95_sample_count": len(waits),
            "p95_empty": (not p95_available),
            "p95_note": (
                None
                if p95_available
                else f"p95 unlocks after {self.min_samples_p95} settled waits (have {len(waits)})"
            ),
            "service_rate": service_rate,
            "service_rate_basis": basis,
            "abandon_rate": abandon_rate,
            "empty": empty,
            "waiting_now": self.queue_length,
        }

    def get_metrics(self) -> Dict[str, Any]:
        inflight = self._inflight_ms or []
        return {
            "zone_id": self.zone_id,
            "id": self.zone_id,
            "name": self.name,
            "queue_length": self.queue_length,
            "avg_wait_seconds": self.avg_wait_seconds,
            "alert_active": self.alert_active,
            "alert_reason": self.alert_reason,
            "max_capacity": self.max_comfortable_queue,
            "alert_length": self.alert_length,
            "alert_wait_ms": self.alert_wait_ms,
            "staff_zone_id": self.staff_zone_id,
            "now": {
                "length": self.queue_length,
                "min_wait_ms": min(inflight) if inflight else None,
                "max_wait_ms": max(inflight) if inflight else None,
                "staff_on_post": self._staff_on_post,
                "staff_zone_id": self.staff_zone_id,
            },
            "kpi": self._kpi_window(),
            "series": list(self._series)[-60:],
            "recent_episodes": list(self._completed)[-12:],
            "abandon_status": "PARTIAL" if self.service_point is None else "LIVE",
            "abandon_note": (
                None
                if self.service_point is not None
                else "service_point_missing — abandon not distinguishable"
            ),
        }
