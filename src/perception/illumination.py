"""Small, conditional exposure correction for person inference frames."""
from __future__ import annotations

from typing import Any, Tuple

import cv2
import numpy as np


def normalize_illumination(frame: Any) -> Tuple[Any, str]:
    """Lift dark frames and compress very bright frames before inference only.

    Typical frames are returned untouched. The caller should keep the original frame
    for display so exposure correction never changes the footage or its overlay.
    """
    if frame is None or not hasattr(frame, "shape") or len(frame.shape) < 2:
        return frame, "normal"

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    mean_luma = float(np.mean(gray))
    if mean_luma < 70:
        gamma, mode = 0.72, "low_light"
    elif mean_luma > 205:
        gamma, mode = 1.18, "high_light"
    else:
        return frame, "normal"

    lut = np.clip(((np.arange(256, dtype=np.float32) / 255.0) ** gamma) * 255.0, 0, 255).astype(np.uint8)
    return cv2.LUT(frame, lut), mode
