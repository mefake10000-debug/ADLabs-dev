"""In-memory NFC tap buffer (optional hardware webhook).

No synthetic taps. Readers (or a webhook proxy) POST to /api/v1/nfc/tap;
GET /api/v1/live exposes recent_taps only when real events arrived this session.

Industry vertical taxonomy (fashion / restaurant / manufacturing / jewelry)
is retired from the Live IA — kept only as a deprecated alias for older clients.
Primary honest map is retail_roles (floor roles).
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
            "Optional hardware stub. No synthetic taps. Not a Live hub segment — "
            "wire a reader webhook if you need tagged product events."
            if not live
            else "Receiving real NFC tap events this session."
        ),
    }


def retail_roles_block(
    snap: Optional[Dict[str, Any]],
    nfc: Dict[str, Any],
) -> Dict[str, Any]:
    """Honest floor-role maturity map for Retail intelligence — never invents rates."""
    snap = snap or {}
    zones = snap.get("zones") or []
    dwell = [z for z in zones if (z.get("type") or "dwell") == "dwell"]
    staff_zones = snap.get("staff_zones") or []
    products = snap.get("products_top")
    models = snap.get("models") or {}
    queues = snap.get("queues") or []
    staff_now = snap.get("staff_now")
    entrance = snap.get("entrance") or {}
    journey = snap.get("journey") or {}
    jsum = journey.get("summary") or {}
    products_on = bool(models.get("products")) or bool(products)
    has_dwell = len(dwell) > 0
    has_queue = any(
        (q.get("avg_wait_seconds") is not None) or (q.get("queue_length") is not None)
        for q in queues
    ) or snap.get("queue_length") is not None

    stop = entrance.get("stop_rate") if isinstance(entrance, dict) else None

    return {
        "schema": "floor_roles_v1",
        "entrance": {
            "entries": "LIVE" if snap.get("total_visitors") is not None else "EMPTY",
            "stop_rate": "LIVE" if stop is not None else "FUTURE",
            "note": "Glass stop-rate stays FUTURE until a glass ROI is calibrated.",
        },
        "path": {
            "journey": "LIVE" if jsum else ("PARTIAL" if journey.get("stages") else "EMPTY"),
            "dead_aisles": "LIVE" if jsum else "EMPTY",
            "note": "Journey stages from zone tags; cold marked stages → dead_zone.",
        },
        "dwell": {
            "hotspots": "LIVE" if has_dwell else "EMPTY",
            "note": "Rank dwell polygons by occupancy × dwell — never invent visits.",
        },
        "queue": {
            "length_wait": "LIVE" if has_queue else "EMPTY",
            "p95": (
                "LIVE"
                if any((q.get("kpi") or {}).get("p95_available") for q in queues)
                else "EMPTY"
            ),
            "service_rate": (
                "LIVE"
                if any((q.get("kpi") or {}).get("service_rate") is not None for q in queues)
                else ("PARTIAL" if any(q.get("abandon_status") == "PARTIAL" for q in queues) else "EMPTY")
            ),
            "note": "p95/service_rate from episodes when samples exist; else empty 0/null — never fake.",
        },
        "staff": {
            "coverage": (
                "LIVE"
                if staff_now is not None or staff_zones
                else "EMPTY"
            ),
            "response_time_to_queue": (
                (snap.get("staff") or {}).get("status")
                if isinstance(snap.get("staff"), dict)
                else "EMPTY"
            )
            or "EMPTY",
            "note": "Geometry staff tags only — no facial identity. Response null until linked zone + arrival.",
        },
        "shelf": {
            "open_vocab": "LIVE" if products_on and products else ("PARTIAL" if products_on else "EMPTY"),
            "shelf_qa_moondream": "FUTURE",
            "accounting_join": "FUTURE",
            "nfc_optional": nfc.get("status", "NEEDS-HARDWARE"),
            "note": "Open-vocab interest when products model on; NFC webhook optional, not a tab.",
        },
    }


def industry_status_block(
    snap: Optional[Dict[str, Any]],
    nfc: Dict[str, Any],
) -> Dict[str, Any]:
    """Deprecated alias — old fashion/restaurant/manufacturing/jewelry map.

    Kept so older clients do not 500; Live hub no longer features these as tabs.
    Prefer retail_roles_block.
    """
    roles = retail_roles_block(snap, nfc)
    return {
        "_deprecated": True,
        "_replaced_by": "retail_roles",
        "fashion": {
            "nfc_taps": nfc.get("status", "NEEDS-HARDWARE"),
            "note": "Deprecated industry tab — use retail_roles.shelf.nfc_optional.",
        },
        "restaurant": {
            "tables": roles["dwell"]["hotspots"],
            "staff": roles["staff"]["coverage"],
            "service_timestamps": roles["queue"]["length_wait"],
            "food_served": "FUTURE",
            "note": "Deprecated — use dwell / queue / staff floor roles.",
        },
        "manufacturing": {
            "line_activity": roles["dwell"]["hotspots"],
            "boxes": roles["shelf"]["open_vocab"],
            "defects": "FUTURE",
            "note": "Deprecated — use shelf open-vocab; defects stay FUTURE.",
        },
        "jewelry": {
            "high_interaction_zones": roles["dwell"]["hotspots"],
            "touch_proxy_zone_revisits": "PARTIAL" if (snap or {}).get("zones") else "EMPTY",
            "hand_near_shelf_pose": "FUTURE",
            "note": "Deprecated — use dwell hotspots.",
        },
    }
