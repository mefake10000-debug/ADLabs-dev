import logging
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ProductInterestAnalyzer:
    """Attributes product interest to people.

    An open-vocabulary detector finds product categories in the frame ("shoe", "handbag",
    "backpack", ...). This class answers the retail question the raw detection cannot:
    *who* was looking at it, and how long were they near it.

    Two signals are produced per category:
      * `viewers`    -- distinct tracked people who were within engagement distance of
                        an instance of the category. This is the "how many people looked
                        at the display" number, and it is deduplicated per person so a
                        single shopper lingering in front of a shelf is counted once.
      * `dwell`      -- total person-seconds spent near an instance, which distinguishes
                        a glance from a browse.
    """

    def __init__(self, engagement_radius_px: float = 160.0, min_dwell_seconds: float = 1.0):
        self.engagement_radius_px = engagement_radius_px
        self.min_dwell_seconds = min_dwell_seconds

        # category -> {track_id -> dwell seconds}
        self._dwell: Dict[str, Dict[int, float]] = defaultdict(dict)
        # category -> set of track ids that ever engaged
        self._viewers: Dict[str, Set[int]] = defaultdict(set)
        # (track_id, category) -> last timestamp seen together
        self._last_seen: Dict[Tuple[int, str], float] = {}
        self._detection_counts: Counter = Counter()
        self._current_detection_counts: Counter = Counter()
        self._active_track_ids: Set[int] = set()

    def observe(
        self,
        detections: List[Dict[str, Any]],
        tracks: List[Any],
        timestamp: float,
    ):
        """Folds one frame of product detections + active tracks into the interest model.

        `detections` entries need `bbox` and `label`. `tracks` are tracker objects
        exposing `track_id` and `foot_point`.
        """
        self._current_detection_counts = Counter(
            d.get("label") for d in detections if d.get("label")
        )
        self._active_track_ids = {int(track.track_id) for track in tracks}
        if not detections:
            return
        self._detection_counts.update(d["label"] for d in detections)

        for det in detections:
            label = det.get("label")
            if not label:
                continue
            dx1, dy1, dx2, dy2 = det["bbox"]
            det_cx = (dx1 + dx2) / 2.0
            det_cy = (dy1 + dy2) / 2.0

            for track in tracks:
                fx, fy = track.foot_point
                dist = ((fx - det_cx) ** 2 + (fy - det_cy) ** 2) ** 0.5
                if dist > self.engagement_radius_px:
                    continue

                key = (track.track_id, label)
                last = self._last_seen.get(key)
                if last is not None and timestamp > last:
                    delta = timestamp - last
                    self._dwell[label][track.track_id] = (
                        self._dwell[label].get(track.track_id, 0.0) + delta
                    )
                self._last_seen[key] = timestamp

                dwell = self._dwell[label].get(track.track_id, 0.0)
                if dwell >= self.min_dwell_seconds:
                    self._viewers[label].add(track.track_id)

    def prune(self, active_track_ids: Iterable[int]):
        active = set(active_track_ids)
        self._active_track_ids = {int(track_id) for track_id in active}
        for key in list(self._last_seen.keys()):
            if key[0] not in active:
                del self._last_seen[key]
        for label, per_track in list(self._dwell.items()):
            for tid in list(per_track.keys()):
                if tid not in active:
                    del per_track[tid]

    def reset(self):
        self._dwell.clear()
        self._viewers.clear()
        self._last_seen.clear()
        self._detection_counts.clear()
        self._current_detection_counts.clear()
        self._active_track_ids.clear()

    def snapshot(self) -> Dict[str, Any]:
        products: List[Dict[str, Any]] = []
        # A category that was detected but drew no viewers still matters: "a shoe
        # display nobody looked at" is a merchandising signal in its own right.
        for label, detection_count in self._current_detection_counts.items():
            per_track = self._dwell.get(label, {})
            viewers = self._viewers.get(label, set()) & self._active_track_ids
            total_dwell = sum(per_track.values())
            products.append({
                "category": label,
                "viewers": len(viewers),
                "detections": detection_count,
                "total_dwell_seconds": round(total_dwell, 1),
                "avg_dwell_seconds": round(total_dwell / len(per_track), 1) if per_track else 0.0,
            })

        products.sort(key=lambda p: (-p["viewers"], -p["total_dwell_seconds"]))

        return {
            "categories_tracked": len(products),
            "products": products[:20],
            "top_category": products[0]["category"] if products else None,
            "total_viewers": len(set().union(*self._viewers.values())) if self._viewers else 0,
        }
