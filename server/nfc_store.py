"""In-memory NFC tap buffer for fashion / apparel use-case modes.

No synthetic taps. Readers (or a webhook proxy) POST to /api/v1/nfc/tap;
GET /api/v1/live exposes recent_taps only when real events arrived this session.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

_LOCK = threading.Lock()
_TAPS: Deque[Dict[str, Any]] = deque(maxlen=100)
_SESSION_COUNT = 0


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record_tap(
    product_id: str,
    *,
    zone: Optional[str] = None,
    zone_id: Optional[str] = None,
    tapped_at: Optional[str] = None,
    camera_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    global _SESSION_COUNT
    pid = (product_id or "").strip()
    if not pid:
        raise ValueError("product_id is required")

    tap = {
        "product_id": pid,
        "zone": (zone or "").strip() or None,
        "zone_id": (zone_id or "").strip() or None,
        "camera_id": (camera_id or "").strip() or None,
        "tapped_at": (tapped_at or "").strip() or _iso_now(),
        "received_at": _iso_now(),
        "meta": meta or {},
    }
    with _LOCK:
        _TAPS.appendleft(tap)
        _SESSION_COUNT += 1
        count = _SESSION_COUNT
    tap_out = dict(tap)
    tap_out["session_index"] = count
    return tap_out


def recent_taps(limit: int = 20) -> List[Dict[str, Any]]:
    n = max(0, min(int(limit), 100))
    with _LOCK:
        return [dict(t) for t in list(_TAPS)[:n]]


def session_count() -> int:
    with _LOCK:
        return _SESSION_COUNT


def clear_session() -> None:
    """Test helper — not exposed on the public API."""
    global _SESSION_COUNT
    with _LOCK:
        _TAPS.clear()
        _SESSION_COUNT = 0


def nfc_live_block(limit: int = 20) -> Dict[str, Any]:
    taps = recent_taps(limit)
    count = session_count()
    live = count > 0
    return {
        "status": "LIVE" if live else "NEEDS-HARDWARE",
        "recent_taps": taps,
        "tap_count_session": count,
        "connect_hint": (
            "POST /api/v1/nfc/tap  JSON: "
            "{product_id, zone?, zone_id?, camera_id?, tapped_at?}"
        ),
        "note": (
            "No synthetic taps. Wire an NFC reader webhook to this endpoint; "
            "the Live fashion panel fills only after real events."
            if not live
            else "Receiving real NFC tap events this session."
        ),
    }


def industry_status_block(
    snap: Optional[Dict[str, Any]],
    nfc: Dict[str, Any],
) -> Dict[str, Any]:
    """Honest LIVE|PARTIAL|EMPTY|FUTURE|NEEDS-HARDWARE map — never invents rates."""
    snap = snap or {}
    zones = snap.get("zones") or []
    dwell = [z for z in zones if (z.get("type") or "dwell") == "dwell"]
    staff_zones = snap.get("staff_zones") or []
    products = snap.get("products_top")
    models = snap.get("models") or {}
    queues = snap.get("queues") or []
    staff_now = snap.get("staff_now")
    pose_on = bool(models.get("pose"))
    products_on = bool(models.get("products")) or bool(products)

    occupied_tables = sum(1 for z in dwell if int(z.get("occupancy") or 0) > 0)
    has_dwell = len(dwell) > 0
    has_queue_wait = any(
        (q.get("avg_wait_seconds") is not None) or (q.get("queue_length") is not None)
        for q in queues
    )

    return {
        "fashion": {
            "nfc_taps": nfc.get("status", "NEEDS-HARDWARE"),
            "note": "Person tap → product_id · time · zone via NFC webhook only.",
        },
        "restaurant": {
            "tables": "LIVE" if has_dwell else "EMPTY",
            "staff": (
                "LIVE"
                if staff_now is not None or staff_zones
                else ("EMPTY" if has_dwell else "EMPTY")
            ),
            "service_timestamps": "PARTIAL" if has_queue_wait else "EMPTY",
            "food_served": "FUTURE",
            "tables_occupied": occupied_tables if has_dwell else None,
            "tables_calibrated": len(dwell) if has_dwell else None,
            "note": (
                "Dwell polygons act as table proxies when calibrated; "
                "food-served POS link is FUTURE."
            ),
        },
        "manufacturing": {
            "line_activity": "LIVE" if has_dwell else "EMPTY",
            "boxes": "LIVE" if products_on and products else ("PARTIAL" if products_on else "EMPTY"),
            "defects": "FUTURE",
            "note": (
                "Box/object classes from YOLO/RF-DETR/open-vocab when loaded; "
                "defect rates stay FUTURE until a defect model is present — never fake %."
            ),
        },
        "jewelry": {
            "high_interaction_zones": "LIVE" if has_dwell else "EMPTY",
            "touch_proxy_zone_revisits": "PARTIAL" if has_dwell else "EMPTY",
            "hand_near_shelf_pose": "PARTIAL" if pose_on else "FUTURE",
            "note": (
                "Rank zones by dwell/occupancy as interaction proxy; "
                "hand-near-shelf needs pose enrichment."
            ),
        },
    }
