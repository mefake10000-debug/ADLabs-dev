"""Session-scoped, overlap-zone ReID association for camera-to-camera deduplication.

This module intentionally refuses to fuse unless the operator has mapped the same
physical store zone in at least two cameras and supplied floor homographies for those
cameras. It does not persist person identifiers or embeddings. Timestamps are edge
receive-time monotonic stamps (same host clock), not camera-exposure timestamps.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


Point = Tuple[float, float]


def _vector(values: Any) -> Tuple[float, ...]:
    if hasattr(values, "tolist"):
        values = values.tolist()
    if len(values) and isinstance(values[0], (list, tuple)):
        values = values[0]
    return tuple(float(v) for v in values)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        return -1.0
    return dot / (left_norm * right_norm)


def project_homography(point: Sequence[float], matrix: Any) -> Optional[Point]:
    """Project one pixel point into the configured shared store-floor coordinates."""
    try:
        if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
            return None
        x, y = float(point[0]), float(point[1])
        m = [[float(v) for v in row] for row in matrix]
        denominator = m[2][0] * x + m[2][1] * y + m[2][2]
        if abs(denominator) < 1e-9:
            return None
        return (
            (m[0][0] * x + m[0][1] * y + m[0][2]) / denominator,
            (m[1][0] * x + m[1][1] * y + m[1][2]) / denominator,
        )
    except (TypeError, ValueError, IndexError):
        return None


@dataclass
class _Observation:
    camera_id: str
    track_id: int
    timestamp_mono: float
    embedding: Tuple[float, ...]
    store_zone_id: str
    floor_xy: Point
    global_id: str


class CrossCameraFusion:
    """Associate tracklets only inside explicitly shared, calibrated store zones."""

    def __init__(
        self,
        *,
        requested_enabled: bool,
        reid_active: bool,
        shared_zone_cameras: Mapping[str, Iterable[str]],
        camera_homographies: Mapping[str, Any],
        association_window_seconds: float = 1.5,
        cosine_threshold: float = 0.86,
        max_floor_distance_m: float = 2.5,
        gallery_ttl_seconds: float = 20.0,
    ):
        self.requested_enabled = bool(requested_enabled)
        self.reid_active = bool(reid_active)
        self.shared_zone_cameras = {}
        for zone_id, cameras in shared_zone_cameras.items():
            camera_set = {str(cam) for cam in cameras}
            if len(camera_set) >= 2:
                self.shared_zone_cameras[str(zone_id)] = camera_set
        self.camera_homographies = dict(camera_homographies)
        self.association_window_seconds = max(0.1, float(association_window_seconds))
        self.cosine_threshold = min(1.0, max(-1.0, float(cosine_threshold)))
        self.max_floor_distance_m = max(0.0, float(max_floor_distance_m))
        self.gallery_ttl_seconds = max(1.0, float(gallery_ttl_seconds))
        self._observations: List[_Observation] = []
        self._track_to_global: Dict[Tuple[str, int], str] = {}
        self._track_seen_at: Dict[Tuple[str, int], float] = {}
        self._next_global_id = 1
        self._cross_camera_matches = 0
        self._last_match_similarity: Optional[float] = None

        shared_cameras = set().union(*self.shared_zone_cameras.values()) if self.shared_zone_cameras else set()
        missing_homography = sorted(cam for cam in shared_cameras if not self._valid_homography(self.camera_homographies.get(cam)))
        if not self.requested_enabled:
            self.gate_reason = "fusion_disabled_by_config"
        elif not self.reid_active:
            self.gate_reason = "reid_model_inactive"
        elif not self.shared_zone_cameras:
            self.gate_reason = "shared_store_zone_not_mapped_in_two_cameras"
        elif missing_homography:
            self.gate_reason = "floor_homography_missing:" + ",".join(missing_homography)
        else:
            self.gate_reason = None

    @staticmethod
    def _valid_homography(matrix: Any) -> bool:
        try:
            if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
                return False
            m = [[float(value) for value in row] for row in matrix]
            values = [value for row in m for value in row]
            determinant = (
                m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
            )
            return all(math.isfinite(value) for value in values) and abs(determinant) > 1e-9
        except (TypeError, ValueError, IndexError):
            return False

    @property
    def enabled(self) -> bool:
        return self.gate_reason is None

    def observe(
        self,
        camera_id: str,
        track_id: int,
        embedding: Any,
        timestamp_mono: float,
        store_zone_ids: Iterable[str],
        floor_xy: Optional[Sequence[float]],
    ) -> Optional[str]:
        """Return an ephemeral global ID when gates pass; otherwise return None."""
        if not self.enabled or floor_xy is None:
            return None
        zones = set(store_zone_ids) & set(self.shared_zone_cameras)
        if not zones:
            return None
        camera_id = str(camera_id)
        track_id = int(track_id)
        timestamp_mono = float(timestamp_mono)
        key = (camera_id, track_id)
        vector = _vector(embedding)
        if not vector:
            return None
        point = (float(floor_xy[0]), float(floor_xy[1]))
        self.prune(timestamp_mono)

        existing_id = self._track_to_global.get(key)
        best: Optional[_Observation] = None
        best_similarity = -1.0
        for candidate in self._observations:
            if candidate.camera_id == camera_id or candidate.store_zone_id not in zones:
                continue
            dt = abs(timestamp_mono - candidate.timestamp_mono)
            if dt > self.association_window_seconds:
                continue
            # Do not merge two distinct tracklets from the same camera into one person.
            if any(
                obs.global_id == candidate.global_id
                and obs.camera_id == camera_id
                and obs.track_id != track_id
                and abs(timestamp_mono - obs.timestamp_mono) <= self.association_window_seconds
                for obs in self._observations
            ):
                continue
            floor_gap = math.dist(point, candidate.floor_xy)
            if floor_gap > self.max_floor_distance_m:
                continue
            similarity = cosine_similarity(vector, candidate.embedding)
            if similarity >= self.cosine_threshold and similarity > best_similarity:
                best, best_similarity = candidate, similarity

        if existing_id:
            global_id = existing_id
        elif best is not None:
            global_id = best.global_id
            self._track_to_global[key] = global_id
            self._cross_camera_matches += 1
            self._last_match_similarity = round(best_similarity, 4)
        else:
            global_id = f"g{self._next_global_id:08d}"
            self._next_global_id += 1
            self._track_to_global[key] = global_id

        self._track_seen_at[key] = timestamp_mono
        # Keep one fresh descriptor per local tracklet; no embedding reaches disk/API.
        self._observations = [obs for obs in self._observations if (obs.camera_id, obs.track_id) != key]
        zone_id = sorted(zones)[0]
        self._observations.append(_Observation(
            camera_id=camera_id,
            track_id=track_id,
            timestamp_mono=timestamp_mono,
            embedding=vector,
            store_zone_id=zone_id,
            floor_xy=point,
            global_id=global_id,
        ))
        return global_id

    def prune(self, now_mono: float) -> None:
        cutoff = float(now_mono) - self.gallery_ttl_seconds
        self._observations = [obs for obs in self._observations if obs.timestamp_mono >= cutoff]
        active_keys = {(obs.camera_id, obs.track_id) for obs in self._observations}
        self._track_to_global = {key: value for key, value in self._track_to_global.items() if key in active_keys}
        self._track_seen_at = {key: value for key, value in self._track_seen_at.items() if key in active_keys}

    def reset(self) -> None:
        """Forget the current session gallery (e.g. on sample-video pass boundary)."""
        self._observations.clear()
        self._track_to_global.clear()
        self._track_seen_at.clear()

    def global_id_for(self, camera_id: str, track_id: int) -> Optional[str]:
        """Internal-only lookup. Never serialize the returned ID to the API or disk."""
        return self._track_to_global.get((str(camera_id), int(track_id)))

    def snapshot(
        self,
        active_tracks: Mapping[str, Iterable[int]],
        active_store_zones: Optional[Mapping[str, Mapping[int, Iterable[str]]]] = None,
    ) -> Dict[str, Any]:
        active = {str(camera): tuple(int(tid) for tid in ids) for camera, ids in active_tracks.items()}
        active_store_zones = active_store_zones or {}
        shared_camera_ids = set().union(*self.shared_zone_cameras.values()) if self.shared_zone_cameras else set()
        calibration_summary = {
            "configured_shared_zones": sorted(self.shared_zone_cameras),
            "shared_zone_camera_count": len(shared_camera_ids),
            "homography_camera_count": sum(
                1 for cam in shared_camera_ids if self._valid_homography(self.camera_homographies.get(cam))
            ),
        }
        if not self.enabled:
            return {
                "enabled": False,
                "status": "GATED",
                "gate_reason": self.gate_reason,
                **calibration_summary,
                "time_basis": "edge_receive_monotonic",
                "deduplicated_active_count": None,
                "matched_active_tracks": 0,
                "unmatched_active_tracks": sum(len(ids) for ids in active.values()),
                "cross_camera_matches_session": self._cross_camera_matches,
                "last_match_similarity": self._last_match_similarity,
                "note": "Per-camera counts remain independent until overlapping zones, floor homographies, and active ReID are configured.",
            }

        identity_keys: Set[str] = set()
        zone_identity_keys: Dict[str, Set[str]] = {}
        matched = 0
        for camera_id, track_ids in active.items():
            for track_id in track_ids:
                global_id = self.global_id_for(camera_id, int(track_id))
                if global_id:
                    identity_keys.add(global_id)
                    matched += 1
                    local_identity = global_id
                else:
                    # Conservative fallback: keep unmatched tracks separate (no undercount).
                    local_identity = f"local:{camera_id}:{int(track_id)}"
                    identity_keys.add(local_identity)
                for zone_id in active_store_zones.get(camera_id, {}).get(track_id, ()):
                    if zone_id in self.shared_zone_cameras:
                        zone_identity_keys.setdefault(str(zone_id), set()).add(local_identity)
        total = sum(len(ids) for ids in active.values())
        return {
            "enabled": True,
            "status": "ACTIVE" if self._cross_camera_matches else "READY_NO_MATCHES_YET",
            "gate_reason": None,
            **calibration_summary,
            "time_basis": "edge_receive_monotonic",
            "deduplicated_active_count": len(identity_keys),
            "deduplicated_count_by_zone": {
                zone_id: len(identity_ids) for zone_id, identity_ids in zone_identity_keys.items()
            },
            "matched_active_tracks": matched,
            "unmatched_active_tracks": max(0, total - matched),
            "cross_camera_matches_session": self._cross_camera_matches,
            "last_match_similarity": self._last_match_similarity,
            "note": "Overlap-zone ReID union; unmatched local tracks remain separately counted. Session-only IDs are not serialized.",
        }
