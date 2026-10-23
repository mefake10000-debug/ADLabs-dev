"""Debug / live MJPEG overlays for EdgeSight.

Person boxes default to track-aligned *parallel* parallelograms (sheared AABB +
ground footprint) so crowded retail CCTV is easier to read than axis-aligned
YOLO rectangles. Set ``OVERLAY_BOX_STYLE=aabb`` to restore classic boxes.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

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

# Motion below this (px/s) uses a mild isometric lean instead of velocity shear.
_SHEAR_SPEED_MIN = 8.0
_MAX_SHEAR_FRAC = 0.45
_ISO_SHEAR_FRAC = 0.18


def resolve_overlay_box_style(env: Optional[Dict[str, str]] = None) -> str:
    """``parallel`` (default) or ``aabb``. Unknown values fall back to parallel."""
    src = env if env is not None else os.environ
    raw = (src.get("OVERLAY_BOX_STYLE") or "parallel").strip().lower()
    return raw if raw in ("parallel", "aabb") else "parallel"


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


def parallel_body_quad(bbox: List[float], shear: float) -> Any:
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


def parallel_footprint_quad(bbox: List[float], shear: float) -> Any:
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
    ) -> Any:
        if cv2 is None or np is None or frame is None:
            return frame
        canvas = frame.copy()
        style = (box_style or resolve_overlay_box_style()).strip().lower()
        if style not in ("parallel", "aabb"):
            style = "parallel"

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

        # 4. Draw Tracks — parallel parallelograms (default) or AABB
        for track in tracks:
            b = [int(v) for v in track.bbox]
            is_stationary = getattr(track, "is_stationary", False)
            is_staff = track.track_id in staff_ids
            if is_staff:
                color = STAFF_COLOR
            else:
                color = (120, 160, 120) if is_stationary else (0, 255, 255)

            shear = 0.0
            if style == "aabb":
                cv2.rectangle(canvas, (b[0], b[1]), (b[2], b[3]), color, 2)
            else:
                width = max(1, b[2] - b[0])
                shear = heading_shear_px(track, width)
                body = parallel_body_quad(track.bbox, shear)
                foot_q = parallel_footprint_quad(track.bbox, shear)
                cv2.polylines(canvas, [body], isClosed=True, color=color, thickness=2)
                cv2.polylines(canvas, [foot_q], isClosed=True, color=color, thickness=1)

            gp = getattr(track, "ground_point", None) or track.foot_point
            foot = (int(gp[0]), int(gp[1]))
            cv2.circle(canvas, foot, 4, (0, 0, 255), -1)

            # Fade trajectory trail / LOS (older = dimmer)
            hist = track.history
            n = len(hist)
            for i in range(1, n):
                pt1 = (int(hist[i - 1][0]), int(hist[i - 1][1]))
                pt2 = (int(hist[i][0]), int(hist[i][1]))
                t = i / max(n - 1, 1)
                g = int(90 + 130 * t)
                cv2.line(canvas, pt1, pt2, (g, g, g), 1)

            dwell = float(getattr(track, "dwell_s", 0.0) or 0.0)
            label = f"ID:{track.track_id}"
            if is_staff:
                label += " STAFF"
            elif is_stationary:
                label += " (still)"
            if dwell >= 1.0:
                label += f" {dwell:.0f}s"
            label_x = int(b[0] + shear)
            cv2.putText(
                canvas,
                label,
                (label_x, b[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

        # 5. Draw HUD Bar at top
        cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 40), (20, 20, 20), -1)
        fps_text = f"FEED {fps:.1f} fps" if infer_fps is None else f"FEED {fps:.1f} | MODEL {infer_fps:.1f} fps"
        n_staff = sum(t.track_id in staff_ids for t in tracks)
        people = f"People: {len(tracks) - n_staff}" + (f" + {n_staff} staff" if n_staff else "")
        hud_text = f"AD Labs EdgeSight | {camera_name} | {fps_text} | {people}"
        cv2.putText(canvas, hud_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return canvas
