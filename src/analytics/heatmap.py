from typing import Any, List, Optional

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None


class Heatmap:
    """Where people spend time on the floor: person-seconds accumulated per grid cell, at each
    track's foot point (where they're standing, not their head).

    Time-weighted, not frame-counted, so it reads the same whether the tracker processes 3 or 13
    frames a second: someone standing still for 30s adds 30 person-seconds to their spot, someone
    walking through spreads a little along their path.
    """

    MAX_STEP_SECONDS = 1.0  # a stall in processing shouldn't dump a long gap onto whoever is visible

    def __init__(self, width: int, height: int, cell: int = 16):
        self.width, self.height, self.cell = width, height, cell
        self.grid = np.zeros(((height + cell - 1) // cell, (width + cell - 1) // cell), np.float32)
        self.last_time: Optional[float] = None
        self.started_at: Optional[float] = None

    def add(self, tracks: List[Any], current_time: float):
        if self.last_time is None:
            self.started_at = current_time
            dt = 0.0
        else:
            dt = min(max(0.0, current_time - self.last_time), self.MAX_STEP_SECONDS)
        self.last_time = current_time
        if dt == 0.0:
            return
        rows, cols = self.grid.shape
        for track in tracks:
            x, y = track.foot_point
            row = min(rows - 1, max(0, int(y) // self.cell))
            col = min(cols - 1, max(0, int(x) // self.cell))
            self.grid[row, col] += dt

    @property
    def total_person_seconds(self) -> float:
        return float(self.grid.sum())

    def render(self, frame: Any, alpha: float = 0.55) -> Any:
        """The heatmap blended over `frame` (a clean camera frame, same size it was built for).
        Blue = little time, red = the most time spent anywhere in this heatmap. Areas nobody stood
        in are left untinted."""
        if cv2 is None:
            raise RuntimeError("OpenCV is required to render a heatmap")
        out = frame.copy()
        peak = self.grid.max()
        if peak > 0:
            smooth = cv2.GaussianBlur(self.grid, (0, 0), sigmaX=1.2)
            # Square root, so one very busy spot (a till) doesn't wash every other area out to blue.
            heat = np.sqrt(smooth / smooth.max())
            heat = cv2.resize(heat, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
            colour = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_JET)
            # Colour fades in with intensity: quiet areas stay close to the plain camera image instead
            # of the whole floor turning blue, and busy areas stand out.
            weight = (alpha * np.clip(heat / 0.5, 0.0, 1.0))[..., None]
            weight[heat < 0.06] = 0.0
            out = (out * (1 - weight) + colour * weight).astype(np.uint8)

        minutes = 0.0 if self.started_at is None else (self.last_time - self.started_at) / 60.0
        caption = (f"Time spent: {self.total_person_seconds / 60:.1f} person-min over {minutes:.1f} min"
                   f"  |  blue = little, red = most")
        cv2.rectangle(out, (0, 0), (out.shape[1], 34), (20, 20, 20), -1)
        cv2.putText(out, caption, (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return out
