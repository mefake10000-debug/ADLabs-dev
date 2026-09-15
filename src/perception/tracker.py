import time
from typing import List, Dict, Any, Tuple, Optional

class Track:
    def __init__(self, track_id: int, bbox: List[float], confidence: float, timestamp: float):
        self.track_id = track_id
        self.bbox = bbox
        self.confidence = confidence
        self.first_seen = timestamp
        self.last_seen = timestamp
        self.hits = 1
        self.time_since_update = 0
        self.state = "active"
        self.is_stationary = False
        self.total_displacement = 0.0

        foot = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
        self.initial_foot = foot
        self.history: List[Tuple[float, float, float]] = [(foot[0], foot[1], timestamp)]

        # --- NEW: velocity estimate, in pixels/second, along each axis ---
        self.velocity: Tuple[float, float] = (0.0, 0.0)

    @property
    def foot_point(self) -> Tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2.0, self.bbox[3])

    def _update_velocity(self):
        """Estimate current velocity from the last few history points.
        Using a short window (not just the last 2 points) smooths out
        per-frame detector jitter, which would otherwise make the
        velocity estimate noisy and unreliable."""
        window = self.history[-5:]  # last ~0.3s at 15fps
        if len(window) < 2:
            self.velocity = (0.0, 0.0)
            return
        (x0, y0, t0) = window[0]
        (x1, y1, t1) = window[-1]
        dt = t1 - t0
        if dt <= 0:
            return
        self.velocity = ((x1 - x0) / dt, (y1 - y0) / dt)

    def predicted_foot_point(self, timestamp: float) -> Tuple[float, float]:
        """Where do we expect this person to be NOW, given their last
        known position and velocity, even if they haven't been seen
        for a few frames? This is the key new capability - previously
        a missed track just sat at its last position forever."""
        vx, vy = self.velocity
        dt = timestamp - self.last_seen
        fx, fy = self.foot_point
        return (fx + vx * dt, fy + vy * dt)

    def update(self, bbox: List[float], confidence: float, timestamp: float):
        self.bbox = bbox
        self.confidence = confidence
        self.last_seen = timestamp
        self.hits += 1
        self.time_since_update = 0
        self.state = "active"  # FIX: being matched again means visible again -
                               # previously this never reset, so a track that
                               # went 'lost' stayed invisible forever even after
                               # being correctly re-matched

        foot = self.foot_point
        self.history.append((foot[0], foot[1], timestamp))
        if len(self.history) > 60:
            self.history.pop(0)

        self._update_velocity()

        dx = foot[0] - self.initial_foot[0]
        dy = foot[1] - self.initial_foot[1]
        self.total_displacement = (dx * dx + dy * dy) ** 0.5

        if self.hits >= 25 and self.total_displacement < 16.0:
            self.is_stationary = True
        elif self.total_displacement >= 22.0:
            self.is_stationary = False

    def mark_missed(self, max_age: int = 15):
        self.time_since_update += 1
        if self.time_since_update > max_age:
            self.state = "lost"

class SimpleByteTracker:
    """Lightweight IoU + Spatial distance multi-object tracker with
    temporal confirmation, stationary suppression, and velocity-predicted
    re-matching for brief occlusions."""

    def __init__(
        self,
        max_age: int = 45,          # CHANGED: was 15 (~1s) -> 45 (~3s at 15fps)
        iou_threshold: float = 0.35,
        min_hits: int = 4,
        filter_stationary: bool = True
    ):
        self.max_age = max_age
        self.iou_threshold = iou_threshold
        self.min_hits = min_hits
        self.filter_stationary = filter_stationary
        self.tracks: List[Track] = []
        self._next_id = 1

    def update(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Track]:
        if len(self.tracks) == 0:
            for det in detections:
                new_track = Track(self._next_id, det["bbox"], det["confidence"], timestamp)
                self._next_id += 1
                self.tracks.append(new_track)
            return [t for t in self.tracks if t.state == "active" and t.hits >= self.min_hits]

        matched_tracks, matched_dets, unmatched_dets, unmatched_tracks = self._match(detections, timestamp)

        for t_idx, d_idx in zip(matched_tracks, matched_dets):
            det = detections[d_idx]
            self.tracks[t_idx].update(det["bbox"], det["confidence"], timestamp)

        for t_idx in unmatched_tracks:
            self.tracks[t_idx].mark_missed(max_age=self.max_age)  # FIX: use the
                                                                    # same max_age
                                                                    # the tracker
                                                                    # was configured
                                                                    # with, instead
                                                                    # of a separate
                                                                    # hardcoded value

        for d_idx in unmatched_dets:
            det = detections[d_idx]
            new_track = Track(self._next_id, det["bbox"], det["confidence"], timestamp)
            self._next_id += 1
            self.tracks.append(new_track)

        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        active_list = []
        for t in self.tracks:
            if t.state != "active":
                continue
            if t.time_since_update > 1:
                continue
            if t.hits < self.min_hits:
                continue
            if self.filter_stationary and t.is_stationary:
                continue
            active_list.append(t)
        return active_list

    def _match(self, detections: List[Dict[str, Any]], timestamp: float):
        num_tracks = len(self.tracks)
        num_dets = len(detections)

        if num_dets == 0:
            return [], [], [], list(range(num_tracks))

        iou_matrix = [[self._calculate_iou(track.bbox, det["bbox"]) for det in detections] for track in self.tracks]

        matched_tracks, matched_dets = [], []
        unmatched_tracks = list(range(num_tracks))
        unmatched_dets = list(range(num_dets))

        # Stage 1: IoU (unchanged)
        while len(unmatched_tracks) > 0 and len(unmatched_dets) > 0:
            max_iou = 0.0
            best_t, best_d = -1, -1
            for t in unmatched_tracks:
                for d in unmatched_dets:
                    if iou_matrix[t][d] > max_iou:
                        max_iou = iou_matrix[t][d]
                        best_t, best_d = t, d
            if max_iou >= self.iou_threshold:
                matched_tracks.append(best_t)
                matched_dets.append(best_d)
                unmatched_tracks.remove(best_t)
                unmatched_dets.remove(best_d)
            else:
                break

        # Stage 2: distance from LAST KNOWN position (unchanged - catches
        # small/recent jitter)
        while len(unmatched_tracks) > 0 and len(unmatched_dets) > 0:
            min_dist = 65.0
            best_t, best_d = -1, -1
            for t in unmatched_tracks:
                t_box = self.tracks[t].bbox
                t_cx = (t_box[0] + t_box[2]) / 2.0
                t_cy = (t_box[1] + t_box[3]) / 2.0
                t_h = t_box[3] - t_box[1]
                for d in unmatched_dets:
                    d_box = detections[d]["bbox"]
                    d_cx = (d_box[0] + d_box[2]) / 2.0
                    d_cy = (d_box[1] + d_box[3]) / 2.0
                    d_h = d_box[3] - d_box[1]
                    if abs(t_h - d_h) / max(1.0, t_h) > 0.4:
                        continue
                    dist = ((t_cx - d_cx) ** 2 + (t_cy - d_cy) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        best_t, best_d = t, d
            if best_t != -1 and best_d != -1:
                matched_tracks.append(best_t)
                matched_dets.append(best_d)
                unmatched_tracks.remove(best_t)
                unmatched_dets.remove(best_d)
            else:
                break

        # --- NEW Stage 3: velocity-PREDICTED position distance ---
        # For tracks that have been missing for a while, their last
        # known position is stale - a person walking at 5px/frame who's
        # been gone 20 frames is now ~100px away from where stage 2
        # would look. This stage predicts where they SHOULD be now,
        # based on their velocity before they disappeared, and matches
        # against that predicted point instead.
        while len(unmatched_tracks) > 0 and len(unmatched_dets) > 0:
            min_dist = 80.0  # slightly more forgiving - prediction has some error
            best_t, best_d = -1, -1
            for t in unmatched_tracks:
                track = self.tracks[t]
                if track.time_since_update < 2:
                    continue  # already tried at their real last position in stage 2
                pred_x, pred_y = track.predicted_foot_point(timestamp)
                t_box = track.bbox
                t_h = t_box[3] - t_box[1]
                for d in unmatched_dets:
                    d_box = detections[d]["bbox"]
                    d_cx = (d_box[0] + d_box[2]) / 2.0
                    d_cy = d_box[3]
                    d_h = d_box[3] - d_box[1]
                    if abs(t_h - d_h) / max(1.0, t_h) > 0.4:
                        continue
                    dist = ((pred_x - d_cx) ** 2 + (pred_y - d_cy) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        best_t, best_d = t, d
            if best_t != -1 and best_d != -1:
                matched_tracks.append(best_t)
                matched_dets.append(best_d)
                unmatched_tracks.remove(best_t)
                unmatched_dets.remove(best_d)
            else:
                break

        return matched_tracks, matched_dets, unmatched_dets, unmatched_tracks

    @staticmethod
    def _calculate_iou(boxA: List[float], boxB: List[float]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        if interArea == 0:
            return 0.0
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        return float(interArea / float(boxAArea + boxBArea - interArea))
