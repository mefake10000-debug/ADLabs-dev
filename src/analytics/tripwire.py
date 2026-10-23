import time
from typing import List, Tuple, Dict, Any, Set, Optional
from src.perception.tracker import Track

def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def intersect(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float], D: Tuple[float, float]) -> bool:
    """Returns True if line segment AB and CD intersect."""
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

class Tripwire:
    """Bidirectional virtual tripwire counter for entrances and exits.

    Crossing tests use each track's **ground point** (bbox bottom-center trail),
    never the box center — that keeps IN/OUT aligned with the red foot dot and
    zone occupancy. History is scanned fully so a crossing that happened during
    ``min_hits`` confirmation still fires when the ID becomes visible.
    """

    def __init__(self, wire_id: str, name: str, line: List[List[float]], in_direction: str = "top_to_bottom"):
        self.wire_id = wire_id
        self.name = name
        self.p1 = (float(line[0][0]), float(line[0][1]))
        self.p2 = (float(line[1][0]), float(line[1][1]))
        self.in_direction = in_direction

        self.in_count = 0
        self.out_count = 0
        # Session counters = same as in/out for live pass; reset_pass clears both.
        self.session_in = 0
        self.session_out = 0
        self._crossed_track_ids: Set[int] = set()

    def reset_pass(self):
        """Sample-video / session boundary: clear IN/OUT and crossing memory."""
        self.in_count = 0
        self.out_count = 0
        self.session_in = 0
        self.session_out = 0
        self._crossed_track_ids.clear()

    def _direction_is_in(self, curr_foot: Tuple[float, float]) -> bool:
        dx = self.p2[0] - self.p1[0]
        dy = self.p2[1] - self.p1[1]
        # In screen coordinates (y downwards):
        # Moving top-to-bottom across a left-to-right line yields cross < 0
        cross = (curr_foot[0] - self.p1[0]) * dy - (curr_foot[1] - self.p1[1]) * dx
        if self.in_direction == "top_to_bottom":
            return cross < 0
        return cross > 0

    def update(self, tracks: List[Track], current_time: float) -> List[Dict[str, Any]]:
        """Updates in/out counters and returns crossing events detected this call."""
        # Bound crossed history memory to last 5000 tracks
        if len(self._crossed_track_ids) > 5000:
            self._crossed_track_ids = set(list(self._crossed_track_ids)[-2500:])

        events: List[Dict[str, Any]] = []

        for track in tracks:
            # Stationary fixtures or already-counted tracks must not trigger crossings
            if track.track_id in self._crossed_track_ids:
                continue
            if getattr(track, "is_stationary", False):
                continue
            hist = getattr(track, "history", None) or []
            if len(hist) < 2:
                continue

            # Walk the full ground-point trail (not only the last segment) so a
            # crossing during temporal confirmation is still counted.
            crossed_at: Optional[Tuple[float, float]] = None
            for i in range(1, len(hist)):
                prev_foot = (float(hist[i - 1][0]), float(hist[i - 1][1]))
                curr_foot = (float(hist[i][0]), float(hist[i][1]))
                if intersect(prev_foot, curr_foot, self.p1, self.p2):
                    crossed_at = curr_foot
                    break

            if crossed_at is None:
                # Also accept an explicit ground_point hop vs prior history tip
                # when callers only append sparsely under infer_every_n.
                gp = getattr(track, "ground_point", None) or getattr(track, "foot_point", None)
                if gp is not None and len(hist) >= 2:
                    prev_foot = (float(hist[-2][0]), float(hist[-2][1]))
                    curr_foot = (float(gp[0]), float(gp[1]))
                    if intersect(prev_foot, curr_foot, self.p1, self.p2):
                        crossed_at = curr_foot

            if crossed_at is None:
                continue

            is_in = self._direction_is_in(crossed_at)
            direction = "in" if is_in else "out"
            if is_in:
                self.in_count += 1
                self.session_in += 1
            else:
                self.out_count += 1
                self.session_out += 1

            self._crossed_track_ids.add(track.track_id)
            events.append({
                "wire_id": self.wire_id,
                "track_id": track.track_id,
                "direction": direction,
                "timestamp": current_time,
                "ground_point": [round(float(crossed_at[0]), 1), round(float(crossed_at[1]), 1)],
            })

        return events

    def get_counts(self) -> Dict[str, Any]:
        return {
            "wire_id": self.wire_id,
            "name": self.name,
            "in_count": self.in_count,
            "out_count": self.out_count,
            "session_in": self.session_in,
            "session_out": self.session_out,
            "net_flow": self.in_count - self.out_count,
        }
