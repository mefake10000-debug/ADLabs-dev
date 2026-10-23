import time
from typing import List, Dict, Any, Tuple, Optional


def tracker_params_for_infer_gap(
    infer_every_n: int = 1,
    *,
    track_buffer: int = 45,
    match_thresh: float = 0.45,
    min_hits: int = 4,
    track_thresh: float = 0.5,
) -> Dict[str, Any]:
    """Scale ByteTrack association for skipped detect frames.

    ``infer_every_n`` > 1 means consecutive tracker updates are N decoded frames
    apart. People move farther, IoU drops, and a tight distance gate mints new
    IDs — which breaks dwell continuity and tripwire crossings. Buffer stays in
    *update ticks* (not wall frames); distance gates grow with the gap.
    """
    n = max(1, int(infer_every_n or 1))
    gap = n - 1
    return {
        "max_age": max(int(track_buffer), int(round(track_buffer * (1.0 + 0.35 * gap)))),
        "iou_threshold": max(0.25, float(match_thresh) - 0.05 * gap),
        "min_hits": max(2, int(min_hits) - gap),
        "track_thresh": float(track_thresh),
        "dist_gate": 65.0 * (1.0 + 0.55 * gap),
        "pred_dist_gate": 80.0 * (1.0 + 0.55 * gap),
        "infer_every_n": n,
    }


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
        # Zone / queue dwell while currently inside (seconds). Updated by analytics.
        self.dwell_s: float = 0.0
        self.zone_id: Optional[str] = None
        # Pose-refined ground contact (RTMPose ankles). None → bbox bottom-center.
        self.pose_foot: Optional[Tuple[float, float]] = None
        self.keypoints: Optional[Dict[str, List[float]]] = None
        self.keypoints_xy: Optional[List[List[float]]] = None

        foot = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
        self.initial_foot = foot
        self.history: List[Tuple[float, float, float]] = [(foot[0], foot[1], timestamp)]

        # velocity estimate, pixels/second, along each axis
        self.velocity: Tuple[float, float] = (0.0, 0.0)

    @property
    def foot_point(self) -> Tuple[float, float]:
        """Primary ground contact for tripwire / dwell / red foot overlay.

        Prefer RTMPose ankle midpoint when set; otherwise AABB bottom-center.
        """
        if self.pose_foot is not None:
            return (float(self.pose_foot[0]), float(self.pose_foot[1]))
        return ((self.bbox[0] + self.bbox[2]) / 2.0, self.bbox[3])

    @property
    def ground_point(self) -> Tuple[float, float]:
        """Alias for foot_point (tripwire / zone / overlay contract)."""
        return self.foot_point

    def set_pose(
        self,
        foot: Optional[Tuple[float, float]] = None,
        keypoints: Optional[Dict[str, List[float]]] = None,
        keypoints_xy: Optional[List[List[float]]] = None,
    ) -> None:
        if foot is not None:
            self.pose_foot = (float(foot[0]), float(foot[1]))
        if keypoints is not None:
            self.keypoints = keypoints
        if keypoints_xy is not None:
            self.keypoints_xy = keypoints_xy

    def to_live_dict(self) -> Dict[str, Any]:
        gx, gy = self.ground_point
        return {
            "id": int(self.track_id),
            "track_id": int(self.track_id),
            "first_seen": float(self.first_seen),
            "last_seen": float(self.last_seen),
            "dwell_s": round(float(self.dwell_s or 0.0), 2),
            "foot": [round(float(gx), 1), round(float(gy), 1)],
            "ground_point": [round(float(gx), 1), round(float(gy), 1)],
            "bbox": [round(float(v), 1) for v in self.bbox],
            "confidence": round(float(self.confidence), 3),
            "zone_id": self.zone_id,
            "is_stationary": bool(self.is_stationary),
            "stationary": bool(self.is_stationary),
        }

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

        # Keep pose_foot across bbox updates; drop if ankles drift far from bbox.
        if self.pose_foot is not None:
            cx = (bbox[0] + bbox[2]) * 0.5
            bottom = bbox[3]
            fx, fy = self.pose_foot
            if abs(fx - cx) > max(40.0, 0.6 * (bbox[2] - bbox[0])) or abs(fy - bottom) > max(
                60.0, 0.35 * (bbox[3] - bbox[1])
            ):
                self.pose_foot = None
                self.keypoints = None
                self.keypoints_xy = None

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
        track_thresh: float = 0.5,
        dist_gate: float = 65.0,
        pred_dist_gate: float = 80.0,
        infer_every_n: int = 1,
    ):
        if stationary_policy not in ("tag", "suppress"):
            raise ValueError("stationary_policy must be 'tag' or 'suppress'")
        self.max_age = max_age
        self.iou_threshold = iou_threshold
        self.min_hits = min_hits
        self.stationary_policy = stationary_policy
        self.track_thresh = track_thresh
        self.dist_gate = float(dist_gate)
        self.pred_dist_gate = float(pred_dist_gate)
        self.infer_every_n = max(1, int(infer_every_n or 1))
        self.tracks: List[Track] = []
        self._next_id = 1

    def reset(self):
        """Clear identities (sample-video loop / session boundary)."""
        self.tracks = []
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

    def _active_list(self, min_hits: Optional[int] = None) -> List[Track]:
        need = self.min_hits if min_hits is None else int(min_hits)
        active_list = []
        for t in self.tracks:
            if t.state != "active":
                continue
            if t.time_since_update > 1:
                continue
            if t.hits < need:
                continue
            if self.stationary_policy == "suppress" and t.is_stationary:
                continue
            active_list.append(t)
        return active_list

    def early_tracks(self) -> List[Track]:
        """Tracks visible this update with ≥2 hits (enough history for tripwire).

        Confirmed ``min_hits`` filtering hides people during temporal confirmation.
        Tripwire must still see their ground-point trail or entrance crossings are
        lost forever (segment already same-side of the line when the ID appears).
        """
        return self._active_list(min_hits=2)

    def _match(self, track_indices: List[int], detections: List[Dict[str, Any]], timestamp: float):
        """3-stage greedy matcher (IoU -> last foot distance -> velocity-predicted
        foot distance) between the given subset of self.tracks (by index) and detections.
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

        # Stage 2: distance from LAST KNOWN ground point (not box center — keeps
        # association coherent with tripwire / zone / overlay foot dots).
        while len(unmatched_tracks) > 0 and len(unmatched_dets) > 0:
            min_dist = self.dist_gate
            best_t, best_d = -1, -1
            for t in unmatched_tracks:
                track = self.tracks[t]
                t_fx, t_fy = track.foot_point
                t_box = track.bbox
                t_h = t_box[3] - t_box[1]
                for d in unmatched_dets:
                    d_box = detections[d]["bbox"]
                    d_fx = (d_box[0] + d_box[2]) / 2.0
                    d_fy = d_box[3]
                    d_h = d_box[3] - d_box[1]
                    if abs(t_h - d_h) / max(1.0, t_h) > 0.4:
                        continue
                    dist = ((t_fx - d_fx) ** 2 + (t_fy - d_fy) ** 2) ** 0.5
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

        # Stage 3: velocity-PREDICTED ground point distance
        while len(unmatched_tracks) > 0 and len(unmatched_dets) > 0:
            min_dist = self.pred_dist_gate
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
