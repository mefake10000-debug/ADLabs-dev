"""Run pose refinement off the live person-detection loop."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, List, Optional, Sequence, Tuple


class AsyncPoseRefiner:
    """Schedule one RTMPose pass at a time and apply results to live track IDs."""

    def __init__(self, estimator: Any):
        self.estimator = estimator
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rtmpose")
        self._future: Optional[Future] = None
        self._track_ids: List[int] = []
        self._tick = 0

    def update(self, tracks: Sequence[Any], frame: Any, every_n: int = 8) -> None:
        self._tick += 1
        self._apply_ready(tracks)
        if self._future is not None or not tracks or self._tick % max(1, int(every_n)):
            return

        frame_copy = frame.copy() if hasattr(frame, "copy") else frame
        selected = list(tracks)
        boxes = [list(track.bbox) for track in selected]
        self._track_ids = [int(track.track_id) for track in selected]
        self._future = self._executor.submit(self.estimator.estimate_on_bboxes, frame_copy, boxes)

    def _apply_ready(self, tracks: Sequence[Any]) -> None:
        future = self._future
        if future is None or not future.done():
            return
        self._future = None
        try:
            poses = future.result()
        except Exception:
            self._track_ids = []
            return

        live_tracks = {int(track.track_id): track for track in tracks}
        for track_id, pose in zip(self._track_ids, poses or []):
            track = live_tracks.get(track_id)
            foot = (pose or {}).get("foot_point")
            if track is None or not foot:
                continue
            track.set_pose(
                foot=(float(foot[0]), float(foot[1])),
                keypoints=pose.get("keypoints"),
                keypoints_xy=pose.get("keypoints_xy"),
            )
        self._track_ids = []

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
