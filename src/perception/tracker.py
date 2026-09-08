import time
from typing import List, Dict, Any, Tuple

class Track:
    def __init__(self, track_id: int, bbox: List[float], confidence: float, timestamp: float):
        self.track_id = track_id
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.first_seen = timestamp
        self.last_seen = timestamp
        self.hits = 1
        self.time_since_update = 0
        self.state = "active"
        self.is_stationary = False
        self.total_displacement = 0.0

        # Calculate foot position (bottom-center of bounding box)
        foot = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
        self.initial_foot = foot
        self.history: List[Tuple[float, float, float]] = [(foot[0], foot[1], timestamp)]

    @property
    def foot_point(self) -> Tuple[float, float]:
        """Returns the ground contact point (bottom-center) of the person."""
        return ((self.bbox[0] + self.bbox[2]) / 2.0, self.bbox[3])

    def update(self, bbox: List[float], confidence: float, timestamp: float):
        self.bbox = bbox
        self.confidence = confidence
        self.last_seen = timestamp
        self.hits += 1
        self.time_since_update = 0

        foot = self.foot_point
        self.history.append((foot[0], foot[1], timestamp))
        if len(self.history) > 60:  # Keep past 60 points (~4 seconds at 15 FPS)
            self.history.pop(0)

        # Track total net displacement from first observed position
        dx = foot[0] - self.initial_foot[0]
        dy = foot[1] - self.initial_foot[1]
        self.total_displacement = (dx * dx + dy * dy) ** 0.5

        # Suppress static fixtures (cardboard cutouts, mannequins, price stands)
        # If tracked for 25+ frames (~1.8s) with lifetime displacement < 16px
        if self.hits >= 25 and self.total_displacement < 16.0:
            self.is_stationary = True
        elif self.total_displacement >= 22.0:
            self.is_stationary = False

    def mark_missed(self):
        self.time_since_update += 1
        if self.time_since_update > 15:  # Max 15 frames lost (~1 second)
            self.state = "lost"

class SimpleByteTracker:
    """Lightweight IoU + Spatial distance multi-object tracker with temporal confirmation and stationary suppression."""

    def __init__(
        self,
        max_age: int = 15,
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
        # 1. Compute IoU cost matrix between existing tracks and new detections
        if len(self.tracks) == 0:
            for det in detections:
                new_track = Track(self._next_id, det["bbox"], det["confidence"], timestamp)
                self._next_id += 1
                self.tracks.append(new_track)
            return [t for t in self.tracks if t.state == "active" and t.hits >= self.min_hits]

        matched_tracks, matched_dets, unmatched_dets, unmatched_tracks = self._match(detections)

        # Update matched tracks
        for t_idx, d_idx in zip(matched_tracks, matched_dets):
            det = detections[d_idx]
            self.tracks[t_idx].update(det["bbox"], det["confidence"], timestamp)

        # Increment age on unmatched tracks
        for t_idx in unmatched_tracks:
            self.tracks[t_idx].mark_missed()

        # Create new tracks for unmatched detections
        for d_idx in unmatched_dets:
            det = detections[d_idx]
            new_track = Track(self._next_id, det["bbox"], det["confidence"], timestamp)
            self._next_id += 1
            self.tracks.append(new_track)

        # Remove dead tracks
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        # Return confirmed active tracks (filtering out tentative noise, stale missed boxes, and stationary cardboard fixtures)
        active_list = []
        for t in self.tracks:
            if t.state != "active":
                continue
            if t.time_since_update > 1:  # Suppress ghost bounding boxes from missed frames
                continue
            if t.hits < self.min_hits:
                continue
            if self.filter_stationary and t.is_stationary:
                continue
            active_list.append(t)
        return active_list

    def _match(self, detections: List[Dict[str, Any]]):
        num_tracks = len(self.tracks)
        num_dets = len(detections)

        if num_dets == 0:
            return [], [], [], list(range(num_tracks))

        iou_matrix = [[self._calculate_iou(track.bbox, det["bbox"]) for det in detections] for track in self.tracks]

        matched_tracks, matched_dets = [], []
        unmatched_tracks = list(range(num_tracks))
        unmatched_dets = list(range(num_dets))

        # Stage 1: Greedy matching for highest IoU
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

        # Stage 2: Spatial center-distance fallback matching for walking persons
        # When a person moves between frames or detector jitters slightly, IoU can drop,
        # but center/foot distance remains small (< 65px).
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

                    # Ensure scale is similar (height difference < 40%)
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
        iou = interArea / float(boxAArea + boxBArea - interArea)
        return float(iou)
