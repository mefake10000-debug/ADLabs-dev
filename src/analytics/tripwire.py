import time
from typing import List, Tuple, Dict, Any, Set
from src.perception.tracker import Track

def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def intersect(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float], D: Tuple[float, float]) -> bool:
    """Returns True if line segment AB and CD intersect."""
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

class Tripwire:
    """Bidirectional virtual tripwire counter for entrances and exits."""

    def __init__(self, wire_id: str, name: str, line: List[List[float]], in_direction: str = "top_to_bottom"):
        self.wire_id = wire_id
        self.name = name
        self.p1 = (float(line[0][0]), float(line[0][1]))
        self.p2 = (float(line[1][0]), float(line[1][1]))
        self.in_direction = in_direction

        self.in_count = 0
        self.out_count = 0
        self._crossed_track_ids: Set[int] = set()

    def update(self, tracks: List[Track], current_time: float):
        # Bound crossed history memory to last 5000 tracks
        if len(self._crossed_track_ids) > 5000:
            self._crossed_track_ids = set(list(self._crossed_track_ids)[-2500:])

        for track in tracks:
            # Stationary fixtures or already-counted tracks must not trigger crossings
            if track.track_id in self._crossed_track_ids:
                continue
            if getattr(track, "is_stationary", False):
                continue
            if len(track.history) < 2:
                continue

            # Check trajectory between previous position and current position
            prev_foot = (track.history[-2][0], track.history[-2][1])
            curr_foot = (track.history[-1][0], track.history[-1][1])

            if intersect(prev_foot, curr_foot, self.p1, self.p2):
                # Determine direction via 2D cross-product
                dx = self.p2[0] - self.p1[0]
                dy = self.p2[1] - self.p1[1]
                # In screen coordinates (y downwards):
                # Moving top-to-bottom across a left-to-right line yields cross < 0
                cross = (curr_foot[0] - self.p1[0]) * dy - (curr_foot[1] - self.p1[1]) * dx

                # When moving top-to-bottom across horizontal/near-horizontal line
                if self.in_direction == "top_to_bottom":
                    is_in = cross < 0
                else:
                    is_in = cross > 0

                if is_in:
                    self.in_count += 1
                else:
                    self.out_count += 1

                self._crossed_track_ids.add(track.track_id)

    def get_counts(self) -> Dict[str, Any]:
        return {
            "wire_id": self.wire_id,
            "name": self.name,
            "in_count": self.in_count,
            "out_count": self.out_count,
            "net_flow": self.in_count - self.out_count
        }
