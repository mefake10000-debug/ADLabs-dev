from typing import List, Dict, Any, Optional

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

class DebugOverlay:
    """Renders visual overlays for debugging, calibration, and local display."""

    @staticmethod
    def draw_pipeline(
        frame: Any,
        tracks: List[Track],
        tripwires: List[Tripwire],
        zones: List[Zone],
        queues: List[QueueAnalyzer],
        camera_name: str = "Camera",
        fps: float = 0.0,
        infer_fps: Optional[float] = None
    ) -> Any:
        if cv2 is None or np is None or frame is None:
            return frame
        canvas = frame.copy()

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
                2
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
                2
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
                2
            )

        # 4. Draw Tracks & Bounding Boxes
        for track in tracks:
            b = [int(v) for v in track.bbox]
            is_stationary = getattr(track, "is_stationary", False)
            # Dim, muted color for stationary/tagged tracks (queueing customers, etc.) so the
            # video visually matches the numbers: these ARE counted (stationary_policy="tag"),
            # just distinguishable from people actively walking.
            color = (120, 160, 120) if is_stationary else (0, 255, 255)
            cv2.rectangle(canvas, (b[0], b[1]), (b[2], b[3]), color, 2)
            foot = (int(track.foot_point[0]), int(track.foot_point[1]))
            cv2.circle(canvas, foot, 4, (0, 0, 255), -1)

            # Draw trajectory tail
            for i in range(1, len(track.history)):
                pt1 = (int(track.history[i - 1][0]), int(track.history[i - 1][1]))
                pt2 = (int(track.history[i][0]), int(track.history[i][1]))
                cv2.line(canvas, pt1, pt2, (200, 200, 200), 1)

            label = f"ID:{track.track_id}" + (" (still)" if is_stationary else "")
            cv2.putText(
                canvas,
                label,
                (b[0], b[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

        # 5. Draw HUD Bar at top
        cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 40), (20, 20, 20), -1)
        fps_text = f"FPS: {fps:.1f}" if infer_fps is None else f"Decode {fps:.1f} | Infer {infer_fps:.1f} FPS"
        hud_text = f"AD Labs EdgeSight | {camera_name} | {fps_text} | People Count: {len(tracks)}"
        cv2.putText(canvas, hud_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return canvas

