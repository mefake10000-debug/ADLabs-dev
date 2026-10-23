"""Staff response_time_to_queue — alert/join → linked staff-zone presence.

Honest nulls when queue has no staff_zone_id, staff zone is missing, or nobody
arrives within the observation window. Never invents a fake 0s response.
No facial identity — geometry sticky staff tags only.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + "Z"


class StaffQueueResponseTracker:
    """Pairs queue alert/join with first staff presence in the linked zone."""

    def __init__(self, response_timeout_seconds: float = 600.0, maxlen: int = 40):
        self.response_timeout_seconds = float(response_timeout_seconds)
        self._open: Dict[str, Dict[str, Any]] = {}
        self._settled: Deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self._prev_alert: Dict[str, bool] = {}
        self._prev_join_len: Dict[str, int] = {}

    def observe(
        self,
        queues: List[Dict[str, Any]],
        staff_zones: List[Any],
        now: float,
    ) -> Dict[str, Any]:
        staff_by_id: Dict[str, Any] = {}
        for z in staff_zones or []:
            zid = getattr(z, "zone_id", None) or (z.get("id") if isinstance(z, dict) else None)
            if zid:
                staff_by_id[str(zid)] = z

        for q in queues or []:
            qid = str(q.get("id") or q.get("zone_id") or "")
            if not qid:
                continue
            staff_zone_id = q.get("staff_zone_id")
            # Also accept reverse link from staff zone → queue
            if not staff_zone_id:
                for sz in staff_zones or []:
                    linked = list(getattr(sz, "linked_queue_ids", None) or [])
                    if isinstance(sz, dict):
                        linked = list(sz.get("linked_queue_ids") or [])
                    if qid in [str(x) for x in linked]:
                        staff_zone_id = getattr(sz, "zone_id", None) or (
                            sz.get("id") if isinstance(sz, dict) else None
                        )
                        break
            alert_active = bool(q.get("alert_active"))
            length = int(q.get("queue_length") or (q.get("now") or {}).get("length") or 0)
            prev_alert = self._prev_alert.get(qid, False)
            prev_len = self._prev_join_len.get(qid, 0)

            # Open episode on rising alert edge, or first person joining an empty queue
            open_reason = None
            if alert_active and not prev_alert:
                open_reason = "queue_alert"
            elif length > 0 and prev_len == 0 and staff_zone_id:
                open_reason = "queue_join"

            if open_reason and qid not in self._open:
                self._open[qid] = {
                    "queue_id": qid,
                    "staff_zone_id": str(staff_zone_id) if staff_zone_id else None,
                    "alert_ts": now,
                    "alert_iso": _iso(now),
                    "reason": open_reason,
                    "first_staff_seen_ts": None,
                    "response_time_s": None,
                    "basis": "awaiting_staff" if staff_zone_id else "no_staff_zone_link",
                }

            self._prev_alert[qid] = alert_active
            self._prev_join_len[qid] = length

        # Settle open episodes
        for qid, ep in list(self._open.items()):
            szid = ep.get("staff_zone_id")
            if not szid:
                # Cannot measure — settle as null once, avoid sticky forever
                if now - float(ep["alert_ts"]) >= min(30.0, self.response_timeout_seconds):
                    row = {
                        **ep,
                        "first_staff_seen_ts": None,
                        "response_time_s": None,
                        "basis": "no_staff_zone_link",
                        "settled_at": _iso(now),
                    }
                    self._settled.append(row)
                    del self._open[qid]
                continue

            sz = staff_by_id.get(str(szid))
            present = 0
            if sz is not None:
                if isinstance(sz, dict):
                    present = int(sz.get("staff_present") or sz.get("tagged_ids") or 0)
                else:
                    present = len(getattr(sz, "active_tracks_in_zone", {}) or {})

            if present > 0 and ep.get("first_staff_seen_ts") is None:
                rt = max(0.0, now - float(ep["alert_ts"]))
                ep["first_staff_seen_ts"] = _iso(now)
                ep["response_time_s"] = round(rt, 1)
                ep["basis"] = "session_track_arrival"
                row = {**ep, "settled_at": _iso(now)}
                self._settled.append(row)
                del self._open[qid]
                continue

            if now - float(ep["alert_ts"]) >= self.response_timeout_seconds:
                row = {
                    **ep,
                    "first_staff_seen_ts": None,
                    "response_time_s": None,
                    "basis": "no_staff_arrived_in_window",
                    "settled_at": _iso(now),
                }
                self._settled.append(row)
                del self._open[qid]

        settled = list(self._settled)
        times = [
            float(r["response_time_s"])
            for r in settled
            if r.get("response_time_s") is not None
        ]
        median = None
        if times:
            ordered = sorted(times)
            mid = len(ordered) // 2
            if len(ordered) % 2:
                median = ordered[mid]
            else:
                median = round((ordered[mid - 1] + ordered[mid]) / 2.0, 1)

        status = "LIVE" if times else ("PARTIAL" if self._open or settled else "EMPTY")
        return {
            "queue_response": settled[-12:] + [
                {
                    **ep,
                    "response_time_s": None,
                    "first_staff_seen_ts": None,
                }
                for ep in self._open.values()
            ],
            "response_time_to_queue": median,
            "response_sample_count": len(times),
            "open_unanswered": sum(
                1 for ep in self._open.values() if ep.get("staff_zone_id")
            ),
            "status": status,
            "note": (
                "Median response from settled alert/join → staff-zone presence. "
                "Null until a linked staff zone exists and a session track arrives "
                "(never a fake 0s)."
                if status != "LIVE"
                else "Geometry sticky staff tag; no facial ID."
            ),
        }


def build_staff_block(
    staff_zone_rows: List[Dict[str, Any]],
    tracker: Optional[StaffQueueResponseTracker],
    queues_out: List[Dict[str, Any]],
    staff_zone_objs: List[Any],
    now: float,
) -> Dict[str, Any]:
    """Assemble live.staff with honest response_time_to_queue."""
    resp: Dict[str, Any]
    if tracker is None:
        resp = {
            "queue_response": [],
            "response_time_to_queue": None,
            "response_sample_count": 0,
            "open_unanswered": 0,
            "status": "EMPTY",
            "note": "Staff response tracker not initialized.",
        }
    else:
        resp = tracker.observe(queues_out, staff_zone_objs, now)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "zones": staff_zone_rows,
        "queue_response": resp.get("queue_response") or [],
        "response_time_to_queue": resp.get("response_time_to_queue"),
        "response_sample_count": resp.get("response_sample_count", 0),
        "open_unanswered": resp.get("open_unanswered", 0),
        "status": resp.get("status", "EMPTY"),
        "note": resp.get("note")
        or "Geometry-based sticky staff tag; no facial ID.",
    }
