"""Retail grocery alerts catalog — fire LIVE rows only when deps exist.

Never fabricates FUTURE/PARTIAL alerts. Industry action text comes from the
handoff catalog JSON.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + "Z"


def load_alerts_catalog(path: Optional[str] = None) -> Dict[str, Any]:
    candidates = []
    if path:
        candidates.append(path)
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    candidates.extend([
        os.path.join(here, "data", "alerts_catalog.json"),
        os.path.join(root, "server", "alerts_catalog.json"),
        os.path.join(root, "docs", "handoff", "alerts-catalog-retail-grocery.json"),
        os.path.join(root, "docs", "handoff", "alerts-retail.json"),
        "/app/server/alerts_catalog.json",
    ])
    for p in candidates:
        if p and os.path.isfile(p):
            with open(p, "r") as f:
                data = json.load(f)
            if "alerts" in data:
                return data
            if "sections" in data:
                return {
                    "catalog": "alerts-retail",
                    "alerts": [],
                    "sections": data["sections"],
                    "_source": p,
                }
    return {"catalog": "empty", "alerts": [], "_source": None}


class AlertsEngine:
    """Evaluate catalog rules against a live snapshot dict."""

    def __init__(self, catalog_path: Optional[str] = None):
        self.catalog = load_alerts_catalog(catalog_path)
        self._active: Dict[str, Dict[str, Any]] = {}
        self._cooldown_until: Dict[str, float] = {}

    def catalog_entries(self) -> List[Dict[str, Any]]:
        return list(self.catalog.get("alerts") or [])

    def evaluate(self, snap: Dict[str, Any], now: Optional[float] = None) -> Dict[str, Any]:
        now = now or time.time()
        fired: List[Dict[str, Any]] = []
        pending: List[Dict[str, Any]] = []
        unavailable: List[Dict[str, Any]] = []

        for rule in self.catalog_entries():
            status = (rule.get("data_status") or "FUTURE").upper()
            rid = rule.get("id", "UNKNOWN")
            if status == "FUTURE":
                unavailable.append({
                    "id": rid,
                    "title": rule.get("title"),
                    "data_status": "FUTURE",
                    "recommended_action": rule.get("recommended_action"),
                    "chip": "requires external data source",
                })
                continue
            if status == "PARTIAL":
                pending.append({
                    "id": rid,
                    "title": rule.get("title"),
                    "data_status": "PARTIAL",
                    "recommended_action": rule.get("recommended_action"),
                    "chip": "pending calibration/upgrade",
                    "data_dependency": rule.get("data_dependency"),
                })
                continue

            hit, reason, value = self._eval_live(rule, snap)
            dedupe = (rule.get("dedupe_key") or rid).replace("<queue_id>", "store")
            cooldown_m = float(rule.get("cooldown_minutes") or 5)

            if hit:
                if now < self._cooldown_until.get(dedupe, 0):
                    continue
                if dedupe in self._active:
                    row = dict(self._active[dedupe])
                    row["still_active"] = True
                    fired.append(row)
                    continue
                row = {
                    "id": rid,
                    "title": rule.get("title"),
                    "severity": rule.get("severity", "warning"),
                    "data_status": "LIVE",
                    "active": True,
                    "since_ts": _iso(now),
                    "value": value,
                    "reason": reason,
                    "recommended_action": rule.get("recommended_action"),
                    "dedupe_key": dedupe,
                    "human_review_required": bool(rule.get("human_review_required")),
                }
                self._active[dedupe] = row
                self._cooldown_until[dedupe] = now + cooldown_m * 60
                fired.append(row)
            else:
                if dedupe in self._active:
                    self._active.pop(dedupe)

        for extra in self._eval_safety_heuristics(snap, now):
            fired.append(extra)

        return {
            "generated_at": _iso(now),
            "active": fired,
            "fired": fired,  # alias for older callers
            "partial_catalog": pending,
            "pending": pending,
            "future_catalog": unavailable,
            "unavailable": unavailable,
            "catalog_version": self.catalog.get("version") or self.catalog.get("catalog"),
            "rule": "runtime gate = LIVE AND deps present; never invent FUTURE fires",
        }

    def _eval_live(self, rule: Dict[str, Any], snap: Dict[str, Any]):
        rid = rule.get("id")
        queues = snap.get("queues") or []
        if rid == "QUEUE_LENGTH_OVER":
            for q in queues:
                length = q.get("queue_length")
                if length is None:
                    continue
                cap = q.get("max_capacity") or q.get("alert_length") or 4
                if length > cap:
                    return True, f"queue_length {length} > {cap}", length
            if snap.get("queue_alert_active") and snap.get("queue_length") is not None:
                if int(snap.get("queue_length") or 0) > 4:
                    return True, "store queue_alert_active + length", snap.get("queue_length")
            return False, None, None

        if rid == "QUEUE_WAIT_OVER":
            for q in queues:
                now_block = q.get("now") or {}
                max_wait = now_block.get("max_wait_ms")
                thr = (
                    q.get("alert_wait_ms")
                    or int(float(q.get("congestion_threshold_seconds", 120) or 120) * 1000)
                )
                if max_wait is not None and max_wait > thr:
                    return True, f"max_wait_ms {max_wait} > {thr}", max_wait
            return False, None, None

        if rid == "STAFF_ABSENT_ZONE_BUSY":
            staff_zones = snap.get("staff") or snap.get("staff_zones") or []
            for z in staff_zones:
                present = z.get("staff_present", z.get("tagged_ids"))
                expected = z.get("expected_on_post")
                state = z.get("state")
                if expected is None:
                    continue
                if state == "UNDERSTAFFED" or (present is not None and present < expected):
                    busy = int(snap.get("queue_length") or 0) > 0 or bool(snap.get("queue_alert_active"))
                    if busy:
                        return True, f"staff_present {present} < expected {expected}", present
            return False, None, None

        if rid in ("SAFETY_CROWD_DENSITY", "SAFETY_EXIT_BLOCKED", "SAFETY_RESTRICTED_ENTRY"):
            safety = snap.get("safety") or {}
            for a in safety.get("active") or []:
                if a.get("alert_id") == rid:
                    return True, a.get("reason"), a.get("value")
            return False, None, None

        return False, None, None

    def _eval_safety_heuristics(self, snap: Dict[str, Any], now: float) -> List[Dict[str, Any]]:
        out = []
        safety = snap.get("safety") or {}
        for a in safety.get("active") or []:
            out.append({
                "id": a.get("alert_id"),
                "title": a.get("title") or a.get("alert_id"),
                "severity": a.get("severity", "warning"),
                "data_status": "LIVE",
                "active": True,
                "since_ts": a.get("started_ts") or _iso(now),
                "value": a.get("value"),
                "reason": a.get("reason"),
                "recommended_action": a.get("recommended_action"),
                "human_review_required": True,
            })
        return out
