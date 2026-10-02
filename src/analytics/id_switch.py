from typing import Any, Dict, List

from src.perception.tracker import Track


class IdSwitchDetector:
    """Flags likely tracker ID switches using only the tracker's output, so it needs no labelled
    ground truth. The signature of every switch seen so far (e.g. a cashier going 96 -> 187 -> 96)
    is the same: one ID stops being visible, and shortly afterwards a *different* ID appears where
    it was last seen. That handoff is a candidate.

    In a crowded frame most such handoffs are just two neighbours whose detections flicker in and
    out, so a candidate is only reported once it survives the one test that separates "same person,
    new ID" from "two people": one person can't be on screen under two IDs at once. A candidate is
    dropped if the two IDs were ever visible in the same frame -- before it, or during the
    max_gap_seconds after it (so events are reported that much later than they happen; call flush()
    at the end of a clip).

    Online: feed it each frame's active tracks in order. Reported events are still suspicions to
    confirm by eye -- a person leaving and another arriving at the same spot within the window looks
    identical. Two people swapping IDs while both stay visible is not detectable this way at all.
    """

    def __init__(self, max_gap_seconds: float = 5.0, max_distance_heights: float = 1.0):
        # Gap: how long an ID may be gone and still be "the same person" as the next ID near it.
        # Distance: in units of the lost person's bbox height, so it scales with how close they are
        # to the camera instead of being a fixed pixel radius.
        self.max_gap_seconds = max_gap_seconds
        self.max_distance_heights = max_distance_heights
        self._visible: Dict[int, Dict[str, Any]] = {}  # track_id -> last sighting, for IDs visible last update
        self._ended: List[Dict[str, Any]] = []          # recent last-sightings of IDs that went invisible
        self._ever_seen = set()
        self._co_visible = set()   # frozenset({a, b}) for every pair of IDs ever on screen together
        self.pending: List[Dict[str, Any]] = []         # candidates still inside their confirmation window
        self.new_candidates: List[Dict[str, Any]] = []  # candidates created by the latest update()
        self.retracted = 0

    @staticmethod
    def _sighting(track: Track, current_time: float) -> Dict[str, Any]:
        return {
            "track_id": track.track_id,
            "time": current_time,
            "foot": track.foot_point,
            "bbox": list(track.bbox),
            "height": max(1.0, track.bbox[3] - track.bbox[1]),
            "stationary": getattr(track, "is_stationary", False),
        }

    def update(self, tracks: List[Track], current_time: float) -> List[Dict[str, Any]]:
        """Returns the events confirmed on this update (created up to max_gap_seconds ago)."""
        now_ids = {t.track_id for t in tracks}
        ordered = sorted(now_ids)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                self._co_visible.add(frozenset((a, b)))

        confirmed, still_pending = [], []
        for ev in self.pending:
            if ev["lost_id"] in now_ids and ev["new_id"] in now_ids:
                self.retracted += 1  # both on screen at once: two people after all
            elif current_time - ev["time"] >= self.max_gap_seconds:
                confirmed.append(ev)
            else:
                still_pending.append(ev)
        self.pending = still_pending

        for tid in [tid for tid in self._visible if tid not in now_ids]:
            self._ended.append(self._visible.pop(tid))
        self._ended = [e for e in self._ended if current_time - e["time"] <= self.max_gap_seconds]
        # An ID reappearing after a short gap is simply itself coming back -- it can't be taking over
        # someone else's identity. (If its own sighting was already used up by an earlier
        # candidate, e.g. 96 -> 187, it's free to be matched: that's the 187 -> 96 switch-back.)
        returning = {e["track_id"] for e in self._ended if e["track_id"] in now_ids}
        self._ended = [e for e in self._ended if e["track_id"] not in now_ids]

        appearing = [t for t in tracks if t.track_id not in self._visible and t.track_id not in returning]
        candidates = []
        for e in self._ended:
            for track in appearing:
                if frozenset((e["track_id"], track.track_id)) in self._co_visible:
                    continue
                fx, fy = track.foot_point
                d = ((fx - e["foot"][0]) ** 2 + (fy - e["foot"][1]) ** 2) ** 0.5
                if d <= self.max_distance_heights * e["height"]:
                    candidates.append((d, id(e), e, track))

        # Nearest pairs first; one disappearance explains at most one appearance and vice versa.
        self.new_candidates, used_ended, used_tracks = [], set(), set()
        for d, _, e, track in sorted(candidates, key=lambda c: (c[0], c[1])):
            if id(e) in used_ended or track.track_id in used_tracks:
                continue
            used_ended.add(id(e))
            used_tracks.add(track.track_id)
            self.new_candidates.append({
                "time": round(current_time, 2),
                "lost_id": e["track_id"],
                "new_id": track.track_id,
                # new_id: a never-seen ID took over. id_reused: an older ID came back in place of
                # this one -- the "switch back" half of a 96 -> 187 -> 96 flip.
                "kind": "id_reused" if track.track_id in self._ever_seen else "new_id",
                "gap_seconds": round(current_time - e["time"], 2),
                "distance_px": round(d, 1),
                "distance_heights": round(d / e["height"], 2),
                "lost_was_stationary": e["stationary"],
                "lost_bbox": e["bbox"],
                "new_bbox": list(track.bbox),
            })
        self.pending.extend(self.new_candidates)
        self._ended = [e for e in self._ended if id(e) not in used_ended]

        for track in tracks:
            self._ever_seen.add(track.track_id)
            self._visible[track.track_id] = self._sighting(track, current_time)
        return confirmed

    def flush(self) -> List[Dict[str, Any]]:
        """End of the clip: nothing more can contradict the remaining candidates."""
        remaining, self.pending = self.pending, []
        return remaining
