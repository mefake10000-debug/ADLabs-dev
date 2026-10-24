"""Bounded-window per-camera FPS and detector-work measurements."""

import threading
from typing import Any, Dict, Optional


class PerformanceWindow:
    def __init__(self, window_seconds: float = 2.0):
        self.window_seconds = max(0.25, float(window_seconds))
        self._window_started: Optional[float] = None
        self._frames = 0
        self._detector_calls = 0
        self._skipped = 0
        self._rendered = 0
        self._detector_ms = 0.0
        self._motion_score: Optional[float] = None
        self._last_schedule_reason: Optional[str] = None
        self._lock = threading.Lock()
        self._measured = False
        self._rates: Dict[str, Any] = {
            "model_inference_fps": None,
            "effective_fps": None,
            "skip_rate": None,
            "detector_ms_avg": None,
        }

    def record_frame(self):
        with self._lock:
            self._frames += 1

    def record_inference(self, duration_ms: float, motion_score: Optional[float], reason: str):
        with self._lock:
            self._detector_calls += 1
            self._detector_ms += max(0.0, float(duration_ms))
            self._motion_score = motion_score
            self._last_schedule_reason = reason

    def record_skip(self, motion_score: Optional[float], reason: str):
        with self._lock:
            self._skipped += 1
            self._motion_score = motion_score
            self._last_schedule_reason = reason

    def record_render(self):
        with self._lock:
            self._rendered += 1

    def snapshot(self, now: float, feed_fps: Optional[float]) -> Dict[str, Any]:
        """Return the last completed measurement window plus the current feed rate."""
        with self._lock:
            if self._window_started is None:
                self._window_started = float(now)
            elapsed = float(now) - self._window_started
            if elapsed >= self.window_seconds:
                self._rates = {
                    "model_inference_fps": round(self._detector_calls / elapsed, 2),
                    "effective_fps": round(self._rendered / elapsed, 2),
                    "skip_rate": round(100.0 * self._skipped / max(1, self._frames), 1),
                    "detector_ms_avg": round(self._detector_ms / max(1, self._detector_calls), 1) if self._detector_calls else None,
                }
                self._measured = True
                self._frames = self._detector_calls = self._skipped = self._rendered = 0
                self._detector_ms = 0.0
                self._window_started = float(now)
            return {
                "feed_fps": round(float(feed_fps), 2) if feed_fps is not None and feed_fps > 0 else None,
                **self._rates,
                "motion_score": round(self._motion_score, 4) if self._motion_score is not None else None,
                "last_schedule_reason": self._last_schedule_reason,
            }
