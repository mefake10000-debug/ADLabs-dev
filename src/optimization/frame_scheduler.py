"""Per-camera motion-aware scheduling for expensive person-detector calls."""

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional

try:
    import cv2
    import numpy as np
except ImportError:  # A missing motion dependency must reduce optimization, never accuracy.
    cv2 = None
    np = None


@dataclass(frozen=True)
class ScheduleDecision:
    run_inference: bool
    reason: str
    motion_score: Optional[float]
    cadence_frames: int


class FrameScheduler:
    """Chooses detector cadence while enforcing a wall-clock inference deadline.

    Frame differences use a tiny grayscale thumbnail. Prediction is only useful for
    keeping an overlay responsive between real detector calls; callers must not feed
    predicted tracks into analytics.
    """

    _MODE_MOTION_MULTIPLIER = {"conservative": 0.75, "balanced": 1.0, "aggressive": 1.5}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.enabled = bool(config.get("enabled", True))
        self.mode = config.get("mode", "balanced")
        if self.mode not in self._MODE_MOTION_MULTIPLIER:
            self.mode = "balanced"
        self.min_inference_fps = max(0.1, float(config.get("min_inference_fps", 5)))
        self.motion_threshold = max(0.0, float(config.get("motion_threshold", 0.01)))
        self.fast_track_velocity_px_s = max(0.0, float(config.get("fast_track_velocity_px_s", 180.0)))
        self.use_prediction = bool(config.get("use_prediction", True))
        self._previous_gray = None
        self._last_inference_at: Optional[float] = None
        self._last_inference_frame = -1
        self._frame_index = 0

    def _motion(self, frame: Any):
        if cv2 is None or np is None or frame is None:
            return None, False
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            thumb = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
            if self._previous_gray is None:
                self._previous_gray = thumb
                return None, False
            score = float(np.mean(cv2.absdiff(self._previous_gray, thumb)) / 255.0)
            self._previous_gray = thumb
            scene_cut_threshold = max(self.motion_threshold * 4.0, 0.08)
            return score, score >= scene_cut_threshold
        except (AttributeError, TypeError, ValueError, cv2.error):
            self._previous_gray = None
            return None, False

    def decide(self, frame: Any, tracks: List[Any], now: float, feed_fps: float) -> ScheduleDecision:
        """Return an inference decision for one newly consumed source frame."""
        self._frame_index += 1
        motion_score, scene_change = self._motion(frame)
        target_interval = max(1, int(math.floor(max(feed_fps, 1.0) / self.min_inference_fps)))
        if tracks and all(getattr(track, "is_stationary", False) for track in tracks):
            # Stable people can use the full configured safety interval; moving tracks
            # keep a denser frame cadence when the feed/minimum ratio is fractional.
            target_interval = max(target_interval, int(math.ceil(max(feed_fps, 1.0) / self.min_inference_fps)))
        if self.mode == "conservative":
            target_interval = min(target_interval, 2)
        if not self.use_prediction:
            target_interval = 1
        target_interval = max(1, target_interval)

        reason = None
        max_track_speed = max(
            (math.hypot(*getattr(track, "velocity", (0.0, 0.0))) for track in tracks),
            default=0.0,
        )
        if not self.enabled:
            reason = "scheduler_disabled"
        elif self._last_inference_at is None:
            reason = "startup"
        elif motion_score is None:
            reason = "motion_unavailable"
        elif scene_change:
            reason = "scene_change"
        elif not tracks:
            reason = "no_tracks"
        elif any(
            getattr(track, "state", "active") != "active"
            or getattr(track, "time_since_update", 0) > 0
            or getattr(track, "hits", 1) < 2
            for track in tracks
        ):
            reason = "track_recovery"
        elif max_track_speed >= self.fast_track_velocity_px_s:
            reason = "fast_track_motion"
        elif motion_score >= self.motion_threshold * self._MODE_MOTION_MULTIPLIER[self.mode] * 2.0:
            reason = "high_motion"
        elif now - self._last_inference_at >= 1.0 / self.min_inference_fps:
            reason = "minimum_rate"
        elif self._frame_index - self._last_inference_frame >= target_interval:
            reason = "cadence_due"

        if reason is not None:
            self._last_inference_at = now
            self._last_inference_frame = self._frame_index
            return ScheduleDecision(True, reason, motion_score, target_interval)

        if all(getattr(track, "is_stationary", False) for track in tracks):
            reason = "stable_scene"
        else:
            reason = "tracked_prediction"
        return ScheduleDecision(False, reason, motion_score, target_interval)
