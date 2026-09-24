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
    temporal confirmation, stationary tagging, and velocity-predicted
    re-matching for brief occlusions.

    Two-stage (ByteTrack-style) confidence association: PersonDetector is configured with a
    low confidence floor (see configs/pipeline.yaml perception.confidence_threshold), so it
    returns weaker detections too -- typically partially-occluded people, exactly the case
    that was previously being dropped outright. track_thresh is the bar for STARTING a new
    track; detections below it can only extend a track that already exists, never create one.
    This recovers occluded people without letting low-confidence noise spawn new identities."""

    def __init__(
        self,
        max_age: int = 45,          # CHANGED: was 15 (~1s) -> 45 (~3s at 15fps)
        iou_threshold: float = 0.35,
        min_hits: int = 4,
        stationary_policy: str = "tag",   # "tag": return stationary tracks with is_stationary=True
                                           # set (callers like Tripwire already ignore the flag
                                           # themselves; zones/queues now see and count these
                                           # people, which is what queueing customers are).
                                           # "suppress": old behaviour, drop them from the
                                           # returned list entirely (e.g. for known cardboard-
                                           # cutout/mannequin environments).
        track_thresh: float = 0.5
    ):
        if stationary_policy not in ("tag", "suppress"):
            raise ValueError("stationary_policy must be 'tag' or 'suppress'")
        self.max_age = max_age
        self.iou_threshold = iou_threshold
        self.min_hits = min_hits
        self.stationary_policy = stationary_policy
        self.track_thresh = track_thresh
        self.tracks: List[Track] = []
        self._next_id = 1

    def update(self, detections: List[Dict[str, Any]], timestamp: float) -> List[Track]:
        high_dets = [d for d in detections if d["confidence"] >= self.track_thresh]
        low_dets = [d for d in detections if d["confidence"] < self.track_thresh]

        if len(self.tracks) == 0:
            for det in high_dets:  # low-confidence detections never start a track on their own
                new_track = Track(self._next_id, det["bbox"], det["confidence"], timestamp)
                self._next_id += 1
                self.tracks.append(new_track)
            return self._active_list()

        # Stage set A: every track against the high-confidence detections (the existing
        # 3-stage IoU -> distance -> velocity-predicted matcher).
        track_indices = list(range(len(self.tracks)))
        matched_tracks, matched_dets, unmatched_high_dets, unmatched_tracks = self._match(
            track_indices, high_dets, timestamp
        )
        for t_idx, d_idx in zip(matched_tracks, matched_dets):
            det = high_dets[d_idx]
            self.tracks[t_idx].update(det["bbox"], det["confidence"], timestamp)

        # Stage set B: tracks STILL unmatched try the low-confidence detections. This is the
        # ByteTrack recovery step -- it can only extend a track that survived stage A, never
        # create a new one, so noisy/weak boxes can't spawn spurious identities.
        if low_dets and unmatched_tracks:
            matched_tracks2, matched_dets2, _, unmatched_tracks = self._match(
                unmatched_tracks, low_dets, timestamp
            )
            for t_idx, d_idx in zip(matched_tracks2, matched_dets2):
                det = low_dets[d_idx]
                self.tracks[t_idx].update(det["bbox"], det["confidence"], timestamp)

        for t_idx in unmatched_tracks:
            self.tracks[t_idx].mark_missed(max_age=self.max_age)

        for d_idx in unmatched_high_dets:
            det = high_dets[d_idx]
            new_track = Track(self._next_id, det["bbox"], det["confidence"], timestamp)
            self._next_id += 1
            self.tracks.append(new_track)

        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        return self._active_list()

    def _active_list(self) -> List[Track]:
        active_list = []
        for t in self.tracks:
            if t.state != "active":
                continue
            if t.time_since_update > 1:
                continue
            if t.hits < self.min_hits:
                continue
            if self.stationary_policy == "suppress" and t.is_stationary:
                continue
            active_list.append(t)
        return active_list

    def _match(self, track_indices: List[int], detections: List[Dict[str, Any]], timestamp: float):
        """3-stage greedy matcher (IoU -> last-position distance -> velocity-predicted
        distance) between the given subset of self.tracks (by index) and detections.
        Returns (matched_track_idx, matched_det_idx, unmatched_det_idx, unmatched_track_idx)."""
        num_dets = len(detections)
        if num_dets == 0 or not track_indices:
            return [], [], list(range(num_dets)), list(track_indices)

        iou_matrix = {t: [self._calculate_iou(self.tracks[t].bbox, det["bbox"]) for det in detections] for t in track_indices}

        matched_tracks, matched_dets = [], []
        unmatched_tracks = list(track_indices)
        unmatched_dets = list(range(num_dets))

        # Stage 1: IoU
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

        # Stage 2: distance from LAST KNOWN position (catches small/recent jitter)
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

        # Stage 3: velocity-PREDICTED position distance (see predicted_foot_point)
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
