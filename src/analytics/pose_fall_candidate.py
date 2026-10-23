"""Pose-based fall-candidate tier (PARTIAL stub).

When RTMPose ONNX is on disk and slow-tier pose keypoints are available, this
module can score collapse / near-horizontal torso candidates. Until then it
reports honest FUTURE→PARTIAL status without inventing alerts.

Not a certified life-safety system. Human review required.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def _hip_shoulder_aspect(keypoints: Sequence[Sequence[float]]) -> Optional[float]:
    """Rough torso aspect from COCO-ish keypoints if indices present.

    Expects list of (x, y[, conf]). Returns None when insufficient points.
    """
    if keypoints is None or len(keypoints) < 13:
        return None
    try:
        # COCO: 5=Lshoulder 6=Rshoulder 11=Lhip 12=Rhip
        ls, rs = keypoints[5], keypoints[6]
        lh, rh = keypoints[11], keypoints[12]
        mid_s_y = 0.5 * (ls[1] + rs[1])
        mid_h_y = 0.5 * (lh[1] + rh[1])
        mid_s_x = 0.5 * (ls[0] + rs[0])
        mid_h_x = 0.5 * (lh[0] + rh[0])
        dy = abs(mid_h_y - mid_s_y)
        dx = abs(mid_h_x - mid_s_x)
        if dy + dx < 1e-3:
            return None
        return dy / max(dx, 1.0)
    except (IndexError, TypeError, ValueError):
        return None


def evaluate_pose_falls(
    tracks_with_pose: Sequence[Dict[str, Any]],
    *,
    aspect_collapse: float = 0.55,
    min_still_seconds: float = 10.0,
) -> List[Dict[str, Any]]:
    """Return candidate-only pose fall events. Empty when pose missing."""
    out: List[Dict[str, Any]] = []
    for row in tracks_with_pose:
        kps = row.get("keypoints") or row.get("pose_keypoints")
        aspect = _hip_shoulder_aspect(kps) if kps else None
        still = float(row.get("still_seconds") or 0.0)
        if aspect is None:
            continue
        if aspect < aspect_collapse and still >= min_still_seconds:
            out.append({
                "alert_id": "SAFETY_FALL_CANDIDATE_POSE",
                "track_id": row.get("track_id"),
                "camera_id": row.get("camera_id"),
                "torso_aspect": round(aspect, 3),
                "still_seconds": round(still, 1),
                "severity": "warning",
                "data_status": "PARTIAL",
                "human_review_required": True,
                "disclaimer": (
                    "Pose candidate only — crouching/sitting also trip this heuristic. "
                    "Not a certified life-safety system."
                ),
                "recommended_action": "Possible fall (pose) — human review required.",
            })
    return out


def status(pose_weights_on_disk: bool = False, wired: bool = False) -> Dict[str, Any]:
    if pose_weights_on_disk and wired:
        st = "PARTIAL"
        note = "RTMPose/pose path available — candidate fires only; human review required."
    elif pose_weights_on_disk:
        st = "PARTIAL"
        note = "Pose weights on disk; slow-tier wire pending. SAFETY_FALL_CANDIDATE_POSE not LIVE."
    else:
        st = "FUTURE"
        note = "Awaiting RTMPose pack (phase-2). Bbox fall candidate remains separate LIVE heuristic."
    return {
        "alert_id": "SAFETY_FALL_CANDIDATE_POSE",
        "status": st,
        "model": "rtmpose",
        "note": note,
    }
