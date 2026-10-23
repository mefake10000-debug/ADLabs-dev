"""License-free shelf gap / OSA alerts from existing product boxes.

Zero new weights. Prefer this over SKU-110K (non-commercial) weights.
PARTIAL stub — returns candidates only; needs calibrated shelf-face zones for LIVE.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

Box = Tuple[float, float, float, float]  # x1,y1,x2,y2


@dataclass
class GapCandidate:
    row_y: float
    gap_x1: float
    gap_x2: float
    width: float
    median_box_w: float
    ratio: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_y": round(self.row_y, 1),
            "gap_x1": round(self.gap_x1, 1),
            "gap_x2": round(self.gap_x2, 1),
            "width": round(self.width, 1),
            "median_box_w": round(self.median_box_w, 1),
            "ratio": round(self.ratio, 2),
            "reason": self.reason,
            "alert_id": "SHELF_GAP_GEOMETRY",
            "data_status": "PARTIAL",
            "disclaimer": "Geometry candidate from boxes only — not SKU identity.",
        }


def _median(vals: Sequence[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    mid = len(s) // 2
    if len(s) % 2:
        return float(s[mid])
    return 0.5 * (s[mid - 1] + s[mid])


def detect_shelf_gaps(
    boxes: Sequence[Box],
    *,
    row_y_tol_frac: float = 0.04,
    gap_ratio: float = 0.8,
    frame_h: float = 720.0,
) -> List[GapCandidate]:
    """Cluster boxes into horizontal rows; flag inter-box gaps ≥ gap_ratio × row median width.

    Inspired by common planogram gap heuristics (~80% of row-median box width) without
    depending on SKU-110K weights.
    """
    if len(boxes) < 2:
        return []

    items = []
    for x1, y1, x2, y2 in boxes:
        w = max(1.0, x2 - x1)
        cy = 0.5 * (y1 + y2)
        items.append((cy, x1, x2, w))
    items.sort(key=lambda t: t[0])

    tol = max(8.0, row_y_tol_frac * frame_h)
    rows: List[List[Tuple[float, float, float, float]]] = []
    for cy, x1, x2, w in items:
        placed = False
        for row in rows:
            if abs(row[0][0] - cy) <= tol:
                row.append((cy, x1, x2, w))
                placed = True
                break
        if not placed:
            rows.append([(cy, x1, x2, w)])

    gaps: List[GapCandidate] = []
    for row in rows:
        row.sort(key=lambda t: t[1])
        widths = [t[3] for t in row]
        med_w = _median(widths)
        if med_w <= 1.0:
            continue
        row_y = _median([t[0] for t in row])
        for i in range(len(row) - 1):
            _, _, x2_a, _ = row[i]
            _, x1_b, _, _ = row[i + 1]
            gap_w = x1_b - x2_a
            if gap_w >= gap_ratio * med_w:
                gaps.append(
                    GapCandidate(
                        row_y=row_y,
                        gap_x1=x2_a,
                        gap_x2=x1_b,
                        width=gap_w,
                        median_box_w=med_w,
                        ratio=gap_w / med_w,
                        reason=f"inter-box gap {gap_w:.0f}px ≥ {gap_ratio:.0%}× median box {med_w:.0f}px",
                    )
                )
    return gaps


def snapshot(boxes: Optional[Sequence[Box]] = None, **kwargs: Any) -> Dict[str, Any]:
    """Honest PARTIAL payload for live aggregate / model-stack consumers."""
    cands = detect_shelf_gaps(boxes or [], **kwargs)
    return {
        "status": "PARTIAL",
        "model": "shelf_gap_geometry",
        "license": "N/A (no new weights)",
        "active": [c.to_dict() for c in cands],
        "note": (
            "Geometry OSA from existing product boxes. "
            "Not LIVE until shelf-face zones + operator review path are calibrated. "
            "SKU-110K weights intentionally SKIPPED (non-commercial)."
        ),
    }
