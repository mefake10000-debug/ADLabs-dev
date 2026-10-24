"""Deterministic native live-edge profile for the local MPS + CPU model stack."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def build_live_profile(base_config: Dict[str, Any], shared_db_path: str) -> Dict[str, Any]:
    """Enable the verified one-camera model stack with bounded concurrent slow jobs.

    The current second sample camera is a test pattern, so this profile intentionally
    keeps one real camera active. It does not enable cross-camera fusion without
    calibrated shared zones/homographies.
    """
    profile = deepcopy(base_config or {})
    performance = profile.setdefault("performance", {})
    performance.update({
        "mode": "quality",
        "imgsz": 640,
        "infer_every_n": 1,
        "display_every_n": 1,
        "max_cameras": 1,
    })
    perception = profile.setdefault("perception", {})
    perception.update({
        "model_name": "models/yolo26s.pt",
        "imgsz": 640,
        "infer_every_n": 1,
        "display_every_n": 1,
    })
    profile.setdefault("storage", {})["db_path"] = str(shared_db_path)
    models = profile.setdefault("models", {})
    models["enabled"] = True
    models["enrichment_threads"] = 1
    slow = models.setdefault("slow_tier", {})
    slow.update({
        "interval_frames": 16,
        "parallel_model_workers": 3,
        "max_faces_per_tick": 1,
        "max_products_per_tick": 4,
    })
    for name in ("face", "demographics", "head_pose", "products", "reid"):
        models.setdefault(name, {})["enabled"] = True
    # Foot-specific RTMPose is the active pose path. The separately loaded
    # YOLO pose checkpoint did not feed a distinct current KPI and duplicated
    # keypoint inference work.
    models.setdefault("pose", {})["enabled"] = False
    products = models.setdefault("products", {})
    products["backend"] = "yoloe"
    models["reid"]["interval_frames"] = 16
    models["reid"]["max_crops_per_tick"] = 1
    # Leave cross-camera identity off until real overlap calibration has passed review.
    fusion = profile.setdefault("cross_camera_fusion", {})
    fusion["enabled"] = False
    return profile
