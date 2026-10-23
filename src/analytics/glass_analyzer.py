"""Glass ROI + stop-rate (entrance glass view).

Computes glass_enter / stop_without_entry from foot-point membership.
Stop-rate is null when no glass ROI is calibrated (honest FUTURE/PARTIAL).
No facial identity — session track IDs only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.analytics.zones import Zone, point_in_polygon
from src.perception.tracker import Track


def _iso(ts: float) -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + "Z"


class GlassROIAnalyzer:
    """One glass polygon + stop threshold; pairs with entry tripwire track IDs."""

    def __init__(
        self,
        glass_id: str,
        name: str,
        polygon: List[List[float]],
        min_stop_seconds: float = 5.0,
        entry_attribution_seconds: float = 90.0,
        exit_grace_seconds: float = 3.0,
    ):
        self.glass_id = glass_id
        self.name = name
        self.zone = Zone(
            glass_id, name, polygon, zone_type="glass", exit_grace_seconds=exit_grace_seconds
        )
        self.min_stop_seconds = float(min_stop_seconds)
        self.entry_attribution_seconds = float(entry_attribution_seconds)

        # track_id -> episode state
        self._episodes: Dict[int, Dict[str, Any]] = {}
        self.glass_entrants = 0
        self.stops_final = 0
        self.stops_converted = 0
        self.pending_events: List[Dict[str, Any]] = []

    def update(
        self,
        tracks: List[Track],
        current_time: float,
        recent_trip_in_ids: Optional[Dict[int, float]] = None,
    ) -> List[Dict[str, Any]]:
        """Update membership; return durable-ish events to persist."""
        recent_trip_in_ids = recent_trip_in_ids or {}
        before = set(self.zone.active_tracks_in_zone.keys())
        self.zone.update(tracks, current_time)
        after = set(self.zone.active_tracks_in_zone.keys())

        events: List[Dict[str, Any]] = []

        for tid in after - before:
            entered = self.zone.active_tracks_in_zone[tid]
            self.glass_entrants += 1
            self._episodes[tid] = {
                "entered_at": entered,
                "stop_reached": False,
                "converted": False,
            }
            events.append({
                "event": "glass_enter",
                "glass_id": self.glass_id,
                "track_id": tid,
                "entered_at": _iso(entered),
                "min_stop_seconds": self.min_stop_seconds,
                "wire_id": self.glass_id,
                "direction": "glass_enter",
                "timestamp": entered,
            })

        # In-flight stop threshold
        for tid, ep in list(self._episodes.items()):
            if tid not in after:
                continue
            dwell = current_time - ep["entered_at"]
            if not ep["stop_reached"] and dwell >= self.min_stop_seconds:
                ep["stop_reached"] = True
                events.append({
                    "event": "glass_stop_reached",
                    "glass_id": self.glass_id,
                    "track_id": tid,
                    "dwell_ms": int(dwell * 1000),
                    "wire_id": self.glass_id,
                    "direction": "glass_stop_reached",
                    "timestamp": current_time,
                })
            # Convert if same track crossed IN after glass enter
            crossed_at = recent_trip_in_ids.get(tid)
            if (
                crossed_at is not None
                and not ep["converted"]
                and 0 <= (crossed_at - ep["entered_at"]) <= self.entry_attribution_seconds
            ):
                ep["converted"] = True
                self.stops_converted += 1
                events.append({
                    "event": "stop_converted",
                    "glass_id": self.glass_id,
                    "track_id": tid,
                    "entered_at": _iso(ep["entered_at"]),
                    "crossed_at": _iso(crossed_at),
                    "dwell_ms": int((crossed_at - ep["entered_at"]) * 1000),
                    "wire_id": self.glass_id,
                    "direction": "stop_converted",
                    "timestamp": crossed_at,
                })

        # Finalized exits
        for tid in before - after:
            ep = self._episodes.pop(tid, None)
            if not ep:
                continue
            left_at = current_time
            dwell = max(0.0, left_at - ep["entered_at"])
            events.append({
                "event": "glass_dwell_ms",
                "glass_id": self.glass_id,
                "track_id": tid,
                "entered_at": _iso(ep["entered_at"]),
                "left_at": _iso(left_at),
                "dwell_ms": int(dwell * 1000),
                "wire_id": self.glass_id,
                "direction": "glass_dwell_ms",
                "timestamp": left_at,
            })
            if ep["stop_reached"] and not ep["converted"]:
                # Attribution window: if still open, keep as settling (don't finalize yet)
                age = left_at - ep["entered_at"]
                if age >= self.entry_attribution_seconds or tid not in recent_trip_in_ids:
                    self.stops_final += 1
                    events.append({
                        "event": "stop_without_entry",
                        "status": "final",
                        "glass_id": self.glass_id,
                        "track_id": tid,
                        "entered_at": _iso(ep["entered_at"]),
                        "left_at": _iso(left_at),
                        "dwell_ms": int(dwell * 1000),
                        "redacted_face_detections_count": 0,
                        "wire_id": self.glass_id,
                        "direction": "stop_without_entry",
                        "timestamp": left_at,
                    })

        self.pending_events.extend(events)
        return events

    def get_metrics(self) -> Dict[str, Any]:
        entrants = self.glass_entrants
        # Measured zero when ROI exists but no entrants yet — not "unknown"
        if entrants <= 0:
            stop_rate = 0.0
            conversion = 0.0
        else:
            stop_rate = round(self.stops_final / entrants, 4)
            conversion = round(self.stops_converted / entrants, 4)

        pending = sum(
            1
            for ep in self._episodes.values()
            if ep.get("stop_reached") and not ep.get("converted")
        )
        return {
            "id": self.glass_id,
            "name": self.name,
            "occupancy": self.zone.current_occupancy,
            "glass_entrants": entrants,
            "stops_final": self.stops_final,
            "stops_converted": self.stops_converted,
            "stop_rate": stop_rate,
            "conversion_glass_to_entry": conversion,
            "pending_stops": pending,
            "min_stop_seconds": self.min_stop_seconds,
            "status": "LIVE",
        }


def build_glass_block(analyzers: List[GlassROIAnalyzer]) -> Optional[Dict[str, Any]]:
    """Aggregate entrance glass KPIs for live snapshot. None when uncalibrated."""
    if not analyzers:
        return None
    rows = [g.get_metrics() for g in analyzers]
    entrants = sum(r["glass_entrants"] for r in rows)
    stops = sum(r["stops_final"] for r in rows)
    converted = sum(r["stops_converted"] for r in rows)
    stop_rate = round(stops / entrants, 4) if entrants > 0 else 0.0
    conversion = round(converted / entrants, 4) if entrants > 0 else 0.0
    pending = sum(r["pending_stops"] for r in rows)
    return {
        "rois": rows,
        "glass_entrants": entrants,
        "stops_final": stops,
        "stop_rate": stop_rate,
        "conversion_glass_to_entry": conversion,
        "pending_stops": pending,
        "settling": pending > 0,
        "status": "LIVE",
        "badge_copy": None,
    }
