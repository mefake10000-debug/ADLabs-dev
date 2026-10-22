import logging
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class GroupAnalyzer:
    """Infers who is shopping together, from track geometry alone.

    Social grouping is not a perception problem -- it is a relation between tracks. Two
    people standing together for several seconds are a party; the same two people
    passing each other on the aisle are not. The test used here is *sustained*
    co-proximity: a link only counts once the pair has been close for a minimum number
    of co-observed frames, which separates "shopping together" from "crossing paths".

    No model is involved, and no face is needed -- grouping works from foot points, so
    it keeps working for people whose faces are turned away or out of frame.
    """

    def __init__(
        self,
        proximity_px: float = 110.0,
        min_shared_frames: int = 8,
        max_group_size: int = 12,
    ):
        self.proximity_px = proximity_px
        self.min_shared_frames = min_shared_frames
        self.max_group_size = max_group_size

        # track_id -> set of partner track_ids that have been close for long enough
        self._links: Dict[int, Set[int]] = {}
        self._shared_counts: Dict[Tuple[int, int], int] = {}
        self._assignment: Dict[int, int] = {}

    def update(self, tracks: List[Any]) -> Dict[int, int]:
        """Recomputes group membership from the current set of active tracks.

        Returns a mapping of track_id -> group_id (a group of one still gets an id,
        so the caller can distinguish "solo" from "with others").
        """
        track_ids = [t.track_id for t in tracks]
        points = {t.track_id: t.foot_point for t in tracks}

        # Count co-proximity this frame.
        for i in range(len(track_ids)):
            for j in range(i + 1, len(track_ids)):
                a, b = track_ids[i], track_ids[j]
                pa, pb = points[a], points[b]
                dist = ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5
                if dist <= self.proximity_px:
                    key = (a, b) if a < b else (b, a)
                    self._shared_counts[key] = self._shared_counts.get(key, 0) + 1
                    if self._shared_counts[key] >= self.min_shared_frames:
                        self._links.setdefault(a, set()).add(b)
                        self._links.setdefault(b, set()).add(a)

        # Connected components over the sustained-link graph.
        parent: Dict[int, int] = {tid: tid for tid in track_ids}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for a, partners in self._links.items():
            if a not in parent:
                continue
            for b in partners:
                if b in parent:
                    union(a, b)

        groups: Dict[int, List[int]] = {}
        for tid in track_ids:
            groups.setdefault(find(tid), []).append(tid)

        assignment: Dict[int, int] = {}
        group_records: List[Dict[str, Any]] = []
        for group_id, (root, members) in enumerate(groups.items()):
            for tid in members:
                assignment[tid] = group_id
            group_records.append({
                "group_id": group_id,
                "size": len(members),
                "members": members,
            })

        self._assignment = assignment
        self._groups = group_records
        return assignment

    def prune(self, active_track_ids: Iterable[int]):
        active = set(active_track_ids)
        for tid in list(self._links.keys()):
            if tid not in active:
                del self._links[tid]
        for key in list(self._shared_counts.keys()):
            if key[0] not in active or key[1] not in active:
                del self._shared_counts[key]

    def reset(self):
        self._links.clear()
        self._shared_counts.clear()
        self._assignment.clear()
        self._groups = []

    def snapshot(self) -> Dict[str, Any]:
        groups = getattr(self, "_groups", [])
        sizes = [g["size"] for g in groups]
        size_counts = Counter(sizes)
        individuals = sum(1 for s in sizes if s == 1)
        pairs = sum(1 for s in sizes if s == 2)
        larger = sum(1 for s in sizes if s >= 3)
        people_in_groups = sum(s for s in sizes if s >= 2)

        return {
            "group_count": len(groups),
            "individual_count": individuals,
            "pair_count": pairs,
            "larger_group_count": larger,
            "people_in_companies": people_in_groups,
            "avg_party_size": round(people_in_groups / max(1, pairs + larger), 2),
            "size_histogram": {str(k): v for k, v in sorted(size_counts.items())},
            "groups": [
                {"group_id": g["group_id"], "size": g["size"]}
                for g in sorted(groups, key=lambda x: -x["size"])[:12]
            ],
            "party_split": {
                "individual": individuals,
                "pair": pairs,
                "group": larger,
            },
        }
