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
    """Polygonal Region of Interest (ROI) for dwell time and occupancy tracking."""

    def __init__(self, zone_id: str, name: str, polygon: List[List[float]], zone_type: str = "dwell"):
        self.zone_id = zone_id
        self.name = name
        self.polygon: List[Tuple[float, float]] = [(float(p[0]), float(p[1])) for p in polygon]
        self.zone_type = zone_type

        # Track management
        self.active_tracks_in_zone: Dict[int, float] = {}  # track_id -> entry_time
        self.completed_dwells: List[float] = []             # past dwell durations in seconds
        self.current_occupancy = 0

    def update(self, tracks: List[Track], current_time: float):
        current_in_zone_ids = set()

        for track in tracks:
            foot = track.foot_point
            if point_in_polygon(foot, self.polygon):
                current_in_zone_ids.add(track.track_id)
                if track.track_id not in self.active_tracks_in_zone:
                    self.active_tracks_in_zone[track.track_id] = current_time

        # Detect tracks that have exited the zone
        exited_ids = [tid for tid in self.active_tracks_in_zone if tid not in current_in_zone_ids]
        for tid in exited_ids:
            entry_time = self.active_tracks_in_zone.pop(tid)
            dwell_seconds = max(0.5, current_time - entry_time)
            self.completed_dwells.append(dwell_seconds)
            # Keep rolling window of past 100 dwell sessions
            if len(self.completed_dwells) > 100:
                self.completed_dwells.pop(0)

        self.current_occupancy = len(self.active_tracks_in_zone)

    def get_metrics(self) -> Dict[str, Any]:
        avg_dwell = 0.0
        if self.completed_dwells:
            avg_dwell = round(sum(self.completed_dwells) / len(self.completed_dwells), 1)

        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "type": self.zone_type,
            "current_occupancy": self.current_occupancy,
            "avg_dwell_seconds": avg_dwell,
            "total_visits": len(self.completed_dwells) + self.current_occupancy
        }

