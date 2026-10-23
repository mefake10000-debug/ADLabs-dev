import time
from typing import List, Tuple, Dict, Any, Optional
from src.perception.tracker import Track

def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """Ray casting algorithm to determine if a point is inside a polygon."""
    x, y = point
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

class Zone:
    """Polygonal Region of Interest (ROI) for dwell time and occupancy tracking.

    Membership uses each track's **ground point** (bbox bottom-center), matching
    tripwire / overlay foot dots.
    """

    def __init__(self, zone_id: str, name: str, polygon: List[List[float]], zone_type: str = "dwell",
                exit_grace_seconds: float = 3.0):
        self.zone_id = zone_id
        self.name = name
        self.polygon: List[Tuple[float, float]] = [(float(p[0]), float(p[1])) for p in polygon]
        self.zone_type = zone_type
        # A track missing from the zone for less than this is still counted as present, so a
        # single dropped detection (occlusion, a frame the detector missed) doesn't reset dwell
        # time or make someone flicker in and out of a queue count.
        self.exit_grace_seconds = exit_grace_seconds

        # Track management
        self.active_tracks_in_zone: Dict[int, float] = {}  # track_id -> entry_time
        self.last_seen_in_zone: Dict[int, float] = {}       # track_id -> most recent time seen inside
        self.completed_dwells: List[float] = []             # past dwell durations in seconds
        self.current_occupancy = 0
        self._last_update_time: float = 0.0

    def update(self, tracks: List[Track], current_time: float):
        self._last_update_time = float(current_time)
        current_in_zone_ids = set()

        for track in tracks:
            # Ground point (foot), never box center — keeps dwell coherent with overlay.
            foot = getattr(track, "ground_point", None) or track.foot_point
            if point_in_polygon(foot, self.polygon):
                current_in_zone_ids.add(track.track_id)
                if track.track_id not in self.active_tracks_in_zone:
                    self.active_tracks_in_zone[track.track_id] = current_time
                self.last_seen_in_zone[track.track_id] = current_time
                # Live per-track dwell while inside this zone
                entry = self.active_tracks_in_zone[track.track_id]
                dwell_s = max(0.0, current_time - entry)
                prev = float(getattr(track, "dwell_s", 0.0) or 0.0)
                if dwell_s >= prev:
                    track.dwell_s = dwell_s
                    track.zone_id = self.zone_id

        # Only finalize an exit once a track has been missing from the zone for longer than the
        # grace period -- not the instant it's absent for a single frame.
        exited_ids = [
            tid for tid in self.active_tracks_in_zone
            if tid not in current_in_zone_ids
            and current_time - self.last_seen_in_zone.get(tid, current_time) > self.exit_grace_seconds
        ]
        for tid in exited_ids:
            entry_time = self.active_tracks_in_zone.pop(tid)
            self.last_seen_in_zone.pop(tid, None)
            dwell_seconds = max(0.5, current_time - entry_time)
            self.completed_dwells.append(dwell_seconds)
            # Keep rolling window of past 100 dwell sessions
            if len(self.completed_dwells) > 100:
                self.completed_dwells.pop(0)

        self.current_occupancy = len(self.active_tracks_in_zone)

    def get_metrics(self, now: Optional[float] = None) -> Dict[str, Any]:
        t_now = float(now if now is not None else self._last_update_time or time.time())
        inflight = [
            max(0.0, t_now - entry)
            for entry in self.active_tracks_in_zone.values()
        ]
        # Live avg includes in-progress dwells so Present/dwell KPIs move while
        # people are still in the zone (completed-only looked stuck at 0).
        blended = list(self.completed_dwells) + inflight
        avg_dwell = round(sum(blended) / len(blended), 1) if blended else 0.0

        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "type": self.zone_type,
            "current_occupancy": self.current_occupancy,
            "avg_dwell_seconds": avg_dwell,
            "active_dwell_seconds": [round(d, 1) for d in inflight],
            "completed_visits": len(self.completed_dwells),
            "total_visits": len(self.completed_dwells) + self.current_occupancy,
            "dwell_by_track": {
                int(tid): round(max(0.0, t_now - entry), 2)
                for tid, entry in self.active_tracks_in_zone.items()
            },
        }
