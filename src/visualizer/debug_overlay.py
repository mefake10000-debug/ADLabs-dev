"""Debug / live MJPEG overlays for EdgeSight.

Default person UI is **foot** tracking: red ground-contact mark + faint ID + trail.
Heavy AABB / pallet boxes are optional (``parallel`` / ``aabb``). ``skeleton`` draws
thin joint lines when RTMPose / YOLO-pose keypoints are on the track.

``OVERLAY_BOX_STYLE=foot|skeleton|parallel|aabb`` (default **foot**).
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
from src.perception.rtmpose_estimator import COCO17_SKELETON

STAFF_COLOR = (255, 0, 255)  # BGR magenta
PERSON_COLOR = (0, 255, 255)  # cyan
STILL_COLOR = (120, 160, 120)
FOOT_COLOR = (0, 0, 255)  # red — primary position mark
SKELETON_COLOR = (180, 180, 180)

_SHEAR_SPEED_MIN = 8.0
_MAX_SHEAR_FRAC = 0.45
_ISO_SHEAR_FRAC = 0.18

_VALID_STYLES = frozenset({"foot", "skeleton", "parallel", "aabb"})
# Aliases kept for peers / older compose files
_ALIAS = {"nvidia": "parallel", "pallet": "parallel"}


def resolve_overlay_box_style(env: Optional[Dict[str, str]] = None) -> str:
    """Default ``foot``. Accepts foot|skeleton|parallel|aabb (+ nvidia/pallet → parallel)."""
    src = env if env is not None else os.environ
    raw = (src.get("OVERLAY_BOX_STYLE") or "foot").strip().lower()
    raw = _ALIAS.get(raw, raw)
    return raw if raw in _VALID_STYLES else "foot"


def heading_shear_px(track: Track, width: float) -> float:
    """Horizontal top-edge shear (px) from track velocity, else isometric lean."""
    w = max(float(width), 1.0)
    vx, vy = getattr(track, "velocity", (0.0, 0.0)) or (0.0, 0.0)
    speed = (float(vx) * float(vx) + float(vy) * float(vy)) ** 0.5
    if speed >= _SHEAR_SPEED_MIN:
        unit_x = float(vx) / speed
        return max(-_MAX_SHEAR_FRAC * w, min(_MAX_SHEAR_FRAC * w, unit_x * 0.35 * w))
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


def _draw_skeleton(canvas: Any, track: Track, color: Tuple[int, int, int] = SKELETON_COLOR) -> None:
    """Thin joint lines from keypoints_xy (COCO-17) or named ankles/hips when present."""
    xy = getattr(track, "keypoints_xy", None)
    if xy and len(xy) >= 17:
        pts = [(int(p[0]), int(p[1])) for p in xy]
        for a, b in COCO17_SKELETON:
            if a >= len(pts) or b >= len(pts):
                continue
            pa, pb = pts[a], pts[b]
            if pa[0] <= 1 and pa[1] <= 1:
                continue
            if pb[0] <= 1 and pb[1] <= 1:
                continue
            cv2.line(canvas, pa, pb, color, 1, lineType=cv2.LINE_AA)
            cv2.circle(canvas, pa, 2, color, -1, lineType=cv2.LINE_AA)
        return
    # Named keypoints fallback (partial)
    kps = getattr(track, "keypoints", None) or {}
    pairs = (
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_hip"),
        ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
        ("left_hip", "left_knee"),
        ("left_knee", "left_ankle"),
        ("right_hip", "right_knee"),
        ("right_knee", "right_ankle"),
    )
    for a, b in pairs:
        if a not in kps or b not in kps:
            continue
        pa = (int(kps[a][0]), int(kps[a][1]))
        pb = (int(kps[b][0]), int(kps[b][1]))
        cv2.line(canvas, pa, pb, color, 1, lineType=cv2.LINE_AA)


def _draw_foot_mark(canvas: Any, track: Track) -> Tuple[int, int]:
    """Primary red ground-contact mark. Returns integer foot xy."""
    fx, fy = track.foot_point
    foot = (int(fx), int(fy))
    cv2.circle(canvas, foot, 5, FOOT_COLOR, -1, lineType=cv2.LINE_AA)
    cv2.circle(canvas, foot, 7, FOOT_COLOR, 1, lineType=cv2.LINE_AA)
    return foot


def _draw_trail(canvas: Any, track: Track) -> None:
    hist = track.history
    n = len(hist)
    for i in range(1, n):
        pt1 = (int(hist[i - 1][0]), int(hist[i - 1][1]))
        pt2 = (int(hist[i][0]), int(hist[i][1]))
        t = i / max(n - 1, 1)
        g = int(70 + 110 * t)
        cv2.line(canvas, pt1, pt2, (g, g, g), 1, lineType=cv2.LINE_AA)


def _draw_faint_id(canvas: Any, track: Track, foot: Tuple[int, int], is_staff: bool) -> None:
    label = f"{track.track_id}" + ("S" if is_staff else "")
    cv2.putText(
        canvas,
        label,
        (foot[0] + 6, foot[1] - 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (160, 160, 160),
        1,
        lineType=cv2.LINE_AA,
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
        objects: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        if cv2 is None or np is None or frame is None:
            return frame
        canvas = frame.copy()
        style = (box_style or resolve_overlay_box_style()).strip().lower()
        style = _ALIAS.get(style, style)
        if style not in _VALID_STYLES:
            style = "foot"

        # 1. Zones
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

        # 2. Queues
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

        # 3. Tripwires
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

        # 4a. Optional store objects (never person) — light AABB only
        for det in objects or []:
            bbox = det.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            name = str(
                det.get("label") or det.get("class_name") or det.get("name") or "object"
            ).strip()
            if name.lower() in ("person", "people"):
                continue
            x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 200, 120), 1)
            cv2.putText(
                canvas, name[:18], (x1, max(12, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 120), 1,
            )

        # 4b. People — style-dependent (foot default = no heavy boxes)
        for track in tracks:
            b = [int(v) for v in track.bbox]
            is_stationary = getattr(track, "is_stationary", False)
            is_staff = track.track_id in staff_ids
            if is_staff:
                color = STAFF_COLOR
            else:
                color = STILL_COLOR if is_stationary else PERSON_COLOR

            if style == "aabb":
                cv2.rectangle(canvas, (b[0], b[1]), (b[2], b[3]), color, 2)
            elif style == "parallel":
                width = max(1, b[2] - b[0])
                shear = heading_shear_px(track, width)
                body = parallel_body_quad(track.bbox, shear)
                foot_q = parallel_footprint_quad(track.bbox, shear)
                cv2.polylines(canvas, [body], isClosed=True, color=color, thickness=2)
                cv2.polylines(canvas, [foot_q], isClosed=True, color=color, thickness=1)
            elif style == "skeleton":
                _draw_skeleton(canvas, track)

            # Primary UX for all styles: red foot + trail + faint id
            foot = _draw_foot_mark(canvas, track)
            _draw_trail(canvas, track)
            _draw_faint_id(canvas, track, foot, is_staff)

            # Heavier ID only for box styles (foot/skeleton stay faint)
            if style in ("aabb", "parallel"):
                label = f"ID:{track.track_id}" + (
                    " STAFF" if is_staff else " (still)" if is_stationary else ""
                )
                cv2.putText(
                    canvas, label, (b[0], max(14, b[1] - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                )

        # 5. HUD
        cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 40), (20, 20, 20), -1)
        fps_text = f"FEED {fps:.1f} fps" if infer_fps is None else f"FEED {fps:.1f} | MODEL {infer_fps:.1f} fps"
        n_staff = sum(t.track_id in staff_ids for t in tracks)
        people = f"People: {len(tracks) - n_staff}" + (f" + {n_staff} staff" if n_staff else "")
        hud_text = f"AD Labs EdgeSight | {camera_name} | {fps_text} | {people} | {style}"
        cv2.putText(canvas, hud_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        return canvas
