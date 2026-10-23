"""Safety operational aids — LIVE only when calibrated zone signals exist.

Not a certified life-safety system. Human review required on every fire.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from src.analytics.zones import Zone
from src.perception.tracker import Track


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + "Z"


class SafetyAnalytics:
    def __init__(
        self,
        fall_bbox_min_still_seconds: float = 10.0,
        density_alert_min_seconds: float = 180.0,
    ):
        self.fall_bbox_min_still = fall_bbox_min_still_seconds
        self.density_min_seconds = density_alert_min_seconds
        self._density_since: Dict[str, float] = {}
        self._restricted_since: Dict[str, float] = {}
        self._exit_since: Dict[str, float] = {}
        self._fall_since: Dict[int, float] = {}
        self.active: List[Dict[str, Any]] = []

    def update(
        self,
        tracks: List[Track],
        zones: List[Zone],
        current_time: float,
        camera_id: str,
    ) -> List[Dict[str, Any]]:
        active: List[Dict[str, Any]] = []
        by_id = {t.track_id: t for t in tracks}

        for z in zones:
            ztype = getattr(z, "zone_type", "dwell")
            cap = getattr(z, "zone_capacity_people", None)
            blocked_grace = float(getattr(z, "blocked_grace_seconds", 30.0) or 30.0)
            entry_grace = float(getattr(z, "entry_grace_seconds", 5.0) or 5.0)

            # Crowd density — only when capacity calibrated
            if cap is not None and z.current_occupancy >= int(cap):
                since = self._density_since.setdefault(z.zone_id, current_time)
                if current_time - since >= self.density_min_seconds:
                    active.append({
                        "alert_id": "SAFETY_CROWD_DENSITY",
                        "title": "Crowd density over calibrated cap",
                        "camera_id": camera_id,
                        "zone_id": z.zone_id,
                        "severity": "warning" if z.current_occupancy < int(cap) * 1.5 else "critical",
                        "value": z.current_occupancy,
                        "threshold": int(cap),
                        "started_ts": _iso(since),
                        "reason": f"occupancy {z.current_occupancy} ≥ cap {cap} for ≥{int(self.density_min_seconds)}s",
                        "recommended_action": f"Crowd building in {z.name} — open a lane / direct foot traffic.",
                        "human_review_required": True,
                    })
            else:
                self._density_since.pop(z.zone_id, None)

            # Restricted entry
            if ztype == "restricted" and z.current_occupancy > 0:
                # longest dwell among active
                max_dwell = 0.0
                for tid, entered in z.active_tracks_in_zone.items():
                    max_dwell = max(max_dwell, current_time - entered)
                if max_dwell >= entry_grace:
                    since = self._restricted_since.setdefault(z.zone_id, current_time - max_dwell)
                    active.append({
                        "alert_id": "SAFETY_RESTRICTED_ENTRY",
                        "title": "Person in restricted zone",
                        "camera_id": camera_id,
                        "zone_id": z.zone_id,
                        "severity": "critical",
                        "value": int(max_dwell),
                        "threshold": entry_grace,
                        "started_ts": _iso(since),
                        "reason": f"dwell {int(max_dwell)}s in restricted zone (session track; no identity)",
                        "recommended_action": (
                            f"Person in restricted zone {z.name} — check authorization "
                            "(session-based; no identity)."
                        ),
                        "human_review_required": True,
                    })
            else:
                self._restricted_since.pop(z.zone_id, None)

            # Exit corridor blocked — stationary dwell
            if ztype == "exit_corridor":
                stationary_dwell = 0.0
                for tid, entered in z.active_tracks_in_zone.items():
                    tr = by_id.get(tid)
                    if tr is not None and getattr(tr, "is_stationary", False):
                        stationary_dwell = max(stationary_dwell, current_time - entered)
                if stationary_dwell >= blocked_grace:
                    since = self._exit_since.setdefault(z.zone_id, current_time - stationary_dwell)
                    active.append({
                        "alert_id": "SAFETY_EXIT_BLOCKED",
                        "title": "Emergency exit corridor occupied",
                        "camera_id": camera_id,
                        "zone_id": z.zone_id,
                        "severity": "critical",
                        "value": int(stationary_dwell),
                        "threshold": blocked_grace,
                        "started_ts": _iso(since),
                        "reason": f"stationary dwell {int(stationary_dwell)}s in exit corridor",
                        "recommended_action": (
                            f"Emergency exit corridor occupied for {int(stationary_dwell)}s — "
                            "dispatch someone to clear the fire exit."
                        ),
                        "human_review_required": True,
                    })
                else:
                    self._exit_since.pop(z.zone_id, None)

        # Fall candidate (bbox heuristic) — high FP disclaimer
        for tr in tracks:
            x1, y1, x2, y2 = tr.bbox
            w = max(1.0, x2 - x1)
            h = max(1.0, y2 - y1)
            aspect = h / w
            # collapse toward horizontal + stationary
            if aspect < 0.55 and getattr(tr, "is_stationary", False):
                since = self._fall_since.setdefault(tr.track_id, current_time)
                if current_time - since >= self.fall_bbox_min_still:
                    active.append({
                        "alert_id": "SAFETY_FALL_CANDIDATE_BBOX",
                        "title": "Possible fall (bbox candidate)",
                        "camera_id": camera_id,
                        "zone_id": None,
                        "severity": "warning",
                        "value": round(aspect, 2),
                        "threshold": 0.55,
                        "started_ts": _iso(since),
                        "reason": "bbox aspect collapse + stillness — candidate only",
                        "recommended_action": (
                            f"Possible fall — cam {camera_id} — human review required."
                        ),
                        "human_review_required": True,
                        "disclaimer": "Candidate only; crouching/sitting also trip this heuristic.",
                    })
            else:
                self._fall_since.pop(tr.track_id, None)

        self.active = active
        return active

    def snapshot(self) -> Dict[str, Any]:
        return {
            "active": list(self.active),
            "status": "LIVE" if self.active else "LIVE",
            "note": (
                "Operational aid only — not a certified life-safety system. "
                "Human review required. Density/restricted fire only when zones calibrated."
            ),
            "future": [
                "SAFETY_FALL_CANDIDATE_POSE (pose weights)",
                "SAFETY_WEAPON_CANDIDATE (excluded)",
                "SAFETY_AGE_RESTRICTED_ZONE (excluded by policy)",
            ],
        }
