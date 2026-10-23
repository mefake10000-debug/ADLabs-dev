"""Debug / live MJPEG overlays for EdgeSight.

Default box style is **nvidia** (LocateAnything Parallel Box look-alike): clean
parallel / palletized framing drawn with OpenCV — sheared parallelogram body,
inset parallel rails, corner caps, and a solid class label. Visual only; do not
download LocateAnything-3B (NVIDIA NC).

Aliases: ``parallel`` / ``pallet`` → same as ``nvidia``. ``aabb`` restores
classic axis-aligned YOLO rectangles.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from src.perception.tracker import Track
from src.analytics.tripwire import Tripwire
from src.analytics.zones import Zone
from src.analytics.queue_analyzer import QueueAnalyzer

STAFF_COLOR = (255, 0, 255)  # BGR magenta
PERSON_COLOR = (0, 255, 255)  # cyan — person priority
STILL_COLOR = (120, 160, 120)
OBJECT_COLOR = (0, 200, 120)  # store objects

# Motion below this (px/s) uses a mild isometric lean instead of velocity shear.
_SHEAR_SPEED_MIN = 8.0
_MAX_SHEAR_FRAC = 0.45
_ISO_SHEAR_FRAC = 0.18

_NVIDIA_STYLES = frozenset({"nvidia", "parallel", "pallet"})
_VALID_STYLES = frozenset({"nvidia", "parallel", "pallet", "aabb"})


def resolve_overlay_box_style(env: Optional[Dict[str, str]] = None) -> str:
    """``nvidia`` (default; aliases parallel/pallet) or ``aabb``."""
    src = env if env is not None else os.environ
    raw = (src.get("OVERLAY_BOX_STYLE") or "nvidia").strip().lower()
    if raw not in _VALID_STYLES:
        return "nvidia"
    if raw in ("parallel", "pallet"):
        return "nvidia"
    return raw


def heading_shear_px(track: Track, width: float) -> float:
    """Horizontal top-edge shear (px) from track velocity, else isometric lean.

    Length of the body parallelogram stays the AABB height; width stays the AABB
    width. Shear tilts the vertical sides so opposite edges stay parallel — a
    cheap oriented footprint without a full OBB solver.
    """
    w = max(float(width), 1.0)
    vx, vy = getattr(track, "velocity", (0.0, 0.0)) or (0.0, 0.0)
    speed = (float(vx) * float(vx) + float(vy) * float(vy)) ** 0.5
    if speed >= _SHEAR_SPEED_MIN:
        unit_x = float(vx) / speed
        return max(-_MAX_SHEAR_FRAC * w, min(_MAX_SHEAR_FRAC * w, unit_x * 0.35 * w))
    # Prefer recent history if velocity is flat but the person has moved.
    hist = getattr(track, "history", None) or []
    if len(hist) >= 3:
        x0, y0, _ = hist[-3]
        x1, y1, _ = hist[-1]
        dx, dy = float(x1) - float(x0), float(y1) - float(y0)
        dist = (dx * dx + dy * dy) ** 0.5
        if dist >= 4.0:
            return max(-_MAX_SHEAR_FRAC * w, min(_MAX_SHEAR_FRAC * w, (dx / dist) * 0.28 * w))
    return _ISO_SHEAR_FRAC * w


def parallel_body_quad(bbox: Sequence[float], shear: float) -> Any:
    """Sheared AABB: bottom edge at feet, top edge shifted → parallelogram."""
    x1, y1, x2, y2 = [float(v) for v in bbox]
    s = float(shear)
    return np.array(
        [
            [x1 + s, y1],
            [x2 + s, y1],
            [x2, y2],
            [x1, y2],
        ],
        dtype=np.int32,
    )


def parallel_footprint_quad(bbox: Sequence[float], shear: float) -> Any:
    """Small isometric parallelogram under the person (ground occupancy cue)."""
    x1, y1, x2, y2 = [float(v) for v in bbox]
    w = max(x2 - x1, 1.0)
    h = max(y2 - y1, 1.0)
    cx = (x1 + x2) * 0.5
    fy = y2
    half = max(6.0, 0.32 * w)
    depth = max(8.0, 0.14 * h)
    sx = float(shear) * 0.45
    return np.array(
        [
            [cx - half, fy],
            [cx + half, fy],
            [cx + half + sx * 0.55, fy - depth],
            [cx - half + sx * 0.55, fy - depth],
        ],
        dtype=np.int32,
    )


def inset_parallel_quad(quad: Any, inset: float = 4.0) -> Any:
    """Shrink a parallelogram toward its centroid (inner pallet rail)."""
    pts = np.asarray(quad, dtype=np.float32)
    c = pts.mean(axis=0)
    out = []
    for p in pts:
        v = p - c
        n = float(np.linalg.norm(v)) or 1.0
        scale = max(0.55, 1.0 - float(inset) / n)
        out.append(c + v * scale)
    return np.asarray(out, dtype=np.int32)


def _draw_corner_caps(canvas: Any, quad: Any, color: Tuple[int, int, int], frac: float = 0.22) -> None:
    """Short L-caps at each parallelogram corner (NVIDIA / Metropolis cue)."""
    pts = np.asarray(quad, dtype=np.int32)
    n = len(pts)
    for i in range(n):
        p = pts[i]
        prev_p = pts[(i - 1) % n]
        next_p = pts[(i + 1) % n]
        for q in (prev_p, next_p):
            dx = int(q[0] - p[0])
            dy = int(q[1] - p[1])
            ex = int(p[0] + dx * frac)
            ey = int(p[1] + dy * frac)
            cv2.line(canvas, (int(p[0]), int(p[1])), (ex, ey), color, 2, cv2.LINE_AA)


def draw_nvidia_pallet_box(
    canvas: Any,
    bbox: Sequence[float],
    shear: float,
    color: Tuple[int, int, int],
    label: str,
) -> None:
    """LocateAnything-style parallel / palletized frame + class label (OpenCV)."""
    body = parallel_body_quad(bbox, shear)
    foot_q = parallel_footprint_quad(bbox, shear)
    inner = inset_parallel_quad(body, inset=max(3.0, 0.06 * max(float(bbox[2]) - float(bbox[0]), 1.0)))

    cv2.polylines(canvas, [body], isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)
    cv2.polylines(canvas, [inner], isClosed=True, color=color, thickness=1, lineType=cv2.LINE_AA)
    cv2.polylines(canvas, [foot_q], isClosed=True, color=color, thickness=1, lineType=cv2.LINE_AA)
    _draw_corner_caps(canvas, body, color)

    if label:
        _draw_label_bar(canvas, body, label, color)


def _draw_label_bar(canvas: Any, quad: Any, label: str, color: Tuple[int, int, int]) -> None:
    """Solid label strip above the top-left of the parallelogram."""
    pts = np.asarray(quad, dtype=np.int32)
    # Top edge is indices 0→1 in body quad.
    x = int(min(pts[0][0], pts[1][0]))
    y = int(min(pts[0][1], pts[1][1]))
    text = str(label)[:48]
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    pad_x, pad_y = 4, 3
    x1 = max(0, x)
    y1 = max(0, y - th - 2 * pad_y - 2)
    x2 = min(canvas.shape[1] - 1, x1 + tw + 2 * pad_x)
    y2 = min(canvas.shape[0] - 1, y1 + th + 2 * pad_y)
    cv2.rectangle(canvas, (x1, y1), (x2, y2), (18, 18, 18), -1)
    cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 1)
    cv2.putText(
        canvas,
        text,
        (x1 + pad_x, y2 - pad_y - 1),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (240, 240, 240),
        1,
        cv2.LINE_AA,
    )


def person_label(track: Track, is_staff: bool = False) -> str:
    """Person-priority label text for overlays (ID + optional dwell from track peer)."""
    base = f"person ID:{track.track_id}"
    dwell = float(getattr(track, "dwell_s", 0.0) or 0.0)
    if dwell >= 0.5:
        base = f"{base} {dwell:.0f}s"
    if is_staff:
        return f"{base} STAFF"
    if getattr(track, "is_stationary", False):
        return f"{base} (still)"
    return base


def object_label(det: Dict[str, Any]) -> str:
    """Store-object class name (COCO / YOLOE / YOLO-World)."""
    name = (
        det.get("label")
        or det.get("class_name")
        or det.get("name")
        or f"class_{det.get('class_id', '?')}"
    )
    return str(name).strip() or "object"


class DebugOverlay:
    """Renders visual overlays for debugging, calibration, and local display."""

    @staticmethod
    def draw_pipeline(
        frame: Any,
        tracks: List[Track],
        tripwires: List[Tripwire],
        zones: List[Zone],
        queues: List[QueueAnalyzer],
        staff_zones: Optional[List[Zone]] = None,
        staff_ids: Optional[Set[int]] = None,
        camera_name: str = "Camera",
        fps: float = 0.0,
        infer_fps: Optional[float] = None,
        box_style: Optional[str] = None,
        objects: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        if cv2 is None or np is None or frame is None:
            return frame
        canvas = frame.copy()
        style = (box_style or resolve_overlay_box_style()).strip().lower()
        if style in ("parallel", "pallet"):
            style = "nvidia"
        if style not in ("nvidia", "aabb"):
            style = "nvidia"

        # 1. Draw Zones (Polygons)
        for zone in zones:
            pts = np.array(zone.polygon, np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pts], isClosed=True, color=(255, 200, 0), thickness=2)
            cv2.putText(
                canvas,
                f"{zone.name} (Occ: {zone.current_occupancy})",
                (int(zone.polygon[0][0]), int(zone.polygon[0][1]) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 200, 0),
                2,
            )

        staff_ids = staff_ids or set()
        for sz in staff_zones or []:
            pts = np.array(sz.polygon, np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [pts], isClosed=True, color=STAFF_COLOR, thickness=2)
            cv2.putText(
                canvas,
                f"{sz.name} (staff)",
                (int(sz.polygon[0][0]), int(sz.polygon[0][1]) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                STAFF_COLOR,
                2,
            )

        # 2. Draw Queues
        for q in queues:
            pts = np.array(q.zone.polygon, np.int32).reshape((-1, 1, 2))
            color = (0, 0, 255) if q.alert_active else (0, 200, 255)
            cv2.polylines(canvas, [pts], isClosed=True, color=color, thickness=3)
            alert_text = " [ALERT]" if q.alert_active else ""
            cv2.putText(
                canvas,
                f"Queue: {q.queue_length} (Wait: {int(q.avg_wait_seconds)}s){alert_text}",
                (int(q.zone.polygon[0][0]), int(q.zone.polygon[0][1]) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        # 3. Draw Tripwires
        for tw in tripwires:
            p1 = (int(tw.p1[0]), int(tw.p1[1]))
            p2 = (int(tw.p2[0]), int(tw.p2[1]))
            cv2.line(canvas, p1, p2, (0, 255, 0), 3)
            counts = tw.get_counts()
            cv2.putText(
                canvas,
                f"{tw.name} | IN: {counts['in_count']} OUT: {counts['out_count']}",
                (p1[0], p1[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        # 4a. Store objects first (under people — person priority on top)
        for det in objects or []:
            bbox = det.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            label = object_label(det)
            # Never re-label a person-class hit here; people come from tracks.
            if label.lower() in ("person", "people"):
                continue
            b = [float(v) for v in bbox]
            shear = _ISO_SHEAR_FRAC * max(b[2] - b[0], 1.0)
            if style == "aabb":
                x1, y1, x2, y2 = [int(v) for v in b]
                cv2.rectangle(canvas, (x1, y1), (x2, y2), OBJECT_COLOR, 2)
                _draw_label_bar(
                    canvas,
                    np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32),
                    label,
                    OBJECT_COLOR,
                )
            else:
                draw_nvidia_pallet_box(canvas, b, shear, OBJECT_COLOR, label)

        # 4b. Person tracks — nvidia pallet (default) or AABB
        for track in tracks:
            b = [int(v) for v in track.bbox]
            is_stationary = getattr(track, "is_stationary", False)
            is_staff = track.track_id in staff_ids
            if is_staff:
                color = STAFF_COLOR
            else:
                color = STILL_COLOR if is_stationary else PERSON_COLOR

            shear = 0.0
            label = person_label(track, is_staff=is_staff)
            if style == "aabb":
                cv2.rectangle(canvas, (b[0], b[1]), (b[2], b[3]), color, 2)
                _draw_label_bar(
                    canvas,
                    np.array([[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]], dtype=np.int32),
                    label,
                    color,
                )
            else:
                width = max(1, b[2] - b[0])
                shear = heading_shear_px(track, width)
                draw_nvidia_pallet_box(canvas, track.bbox, shear, color, label)

            # Ground point = bbox bottom-center (same point tripwire/zones use).
            gp = getattr(track, "ground_point", None) or track.foot_point
            foot = (int(gp[0]), int(gp[1]))
            cv2.circle(canvas, foot, 4, (0, 0, 255), -1)

            # Fade trajectory trail / LOS (older = dimmer) — coherent with ground point
            hist = track.history
            n = len(hist)
            for i in range(1, n):
                pt1 = (int(hist[i - 1][0]), int(hist[i - 1][1]))
                pt2 = (int(hist[i][0]), int(hist[i][1]))
                t = i / max(n - 1, 1)
                g = int(90 + 130 * t)
                cv2.line(canvas, pt1, pt2, (g, g, g), 1)

        # 5. Draw HUD Bar at top
        cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 40), (20, 20, 20), -1)
        fps_text = f"FEED {fps:.1f} fps" if infer_fps is None else f"FEED {fps:.1f} | MODEL {infer_fps:.1f} fps"
        n_staff = sum(t.track_id in staff_ids for t in tracks)
        people = f"People: {len(tracks) - n_staff}" + (f" + {n_staff} staff" if n_staff else "")
        n_obj = len(objects or [])
        obj_bit = f" | Objects: {n_obj}" if n_obj else ""
        hud_text = f"AD Labs EdgeSight | {camera_name} | {fps_text} | {people}{obj_bit}"
        cv2.putText(canvas, hud_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        return canvas
