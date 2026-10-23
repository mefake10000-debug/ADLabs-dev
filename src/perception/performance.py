"""Live-demo performance presets (fast | balanced | quality).

Docker on Mac ARM runs PyTorch CPU-only. Enabling pose / YuNet / YOLO-World+CLIP
on every stream collapses infer FPS to ~0.3–1. Fast keeps max display FPS;
balanced (default for local demos) restores reliable person boxes; quality
restores the enrichment tier (+ RF-DETR by default).

Env (wins over yaml):
  EDGE_PERF_MODE=fast|balanced|quality
  EDGE_MAX_CAMERAS=<int>
  EDGESIGHT_DETECT_MODEL=<path>   # optional YOLO weight override
  DETECTOR_BACKEND=yolo26|rfdetr  # fast/balanced→yolo26; quality→rfdetr unless set
  RFDETR_VARIANT=nano|small
  RFDETR_WEIGHTS=<path|filename>
  OVERLAY_BOX_STYLE=foot|skeleton|nvidia|parallel|aabb  # default foot; nvidia optional
  ENABLE_RTMPOSE=1|0                             # ankle feet when ONNX on disk
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.perception.detector_backend import (
    BACKEND_RFDETR,
    BACKEND_YOLO26,
    resolve_detector_backend,
    resolve_rfdetr_variant,
    resolve_rfdetr_weights,
)

_VALID_MODES = ("fast", "balanced", "quality")

# Max display FPS on Docker CPU — smaller letterbox, skip more frames.
# Prefer EDGE_PERF_MODE=fast only when you accept missed people for speed.
FAST_PRESET: Dict[str, Any] = {
    "mode": "fast",
    "model_name": "models/yolo26n.pt",
    "imgsz": 320,
    "infer_every_n": 3,
    "display_every_n": 1,   # smooth MJPEG from last tracks between infer frames
    "enrichment": False,
    "reid": False,
    "detector_backend": BACKEND_YOLO26,
}

# Local demo default: denser tracks. 512 letterbox — 416 missed crowded shop
# people on entrance_sample checkpoints (about 38% of the hand count; 512 ~60%).
BALANCED_PRESET: Dict[str, Any] = {
    "mode": "balanced",
    "model_name": "models/yolo26n.pt",
    "imgsz": 512,
    "infer_every_n": 2,
    "display_every_n": 1,
    "enrichment": False,
    "reid": False,
    "detector_backend": BACKEND_YOLO26,
}

QUALITY_PRESET: Dict[str, Any] = {
    "mode": "quality",
    "model_name": "models/yolo26s.pt",  # used when DETECTOR_BACKEND=yolo26
    "imgsz": 640,
    "infer_every_n": 1,
    "display_every_n": 2,
    "enrichment": True,
    "reid": False,  # still opt-in via models.reid.enabled
    "detector_backend": BACKEND_RFDETR,  # Apache SOTA default for quality
}

_PRESETS = {
    "fast": FAST_PRESET,
    "balanced": BALANCED_PRESET,
    "quality": QUALITY_PRESET,
}


def resolve_perf_mode(pipeline_cfg: Dict[str, Any]) -> str:
    env = (os.environ.get("EDGE_PERF_MODE") or "").strip().lower()
    if env in _VALID_MODES:
        return env
    cfg = pipeline_cfg.get("performance") or {}
    mode = str(cfg.get("mode", "balanced") or "balanced").strip().lower()
    return mode if mode in _VALID_MODES else "balanced"


def resolve_performance(pipeline_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Merge yaml + env into concrete knobs used by EdgePipeline."""
    mode = resolve_perf_mode(pipeline_cfg)
    preset = dict(_PRESETS[mode])
    perf_cfg = pipeline_cfg.get("performance") or {}
    p_cfg = pipeline_cfg.get("perception") or {}

    # Explicit numeric overrides from performance.* or perception.*
    for key, cast in (("imgsz", int), ("infer_every_n", int), ("display_every_n", int)):
        raw = perf_cfg.get(key, p_cfg.get(key, preset[key]))
        try:
            preset[key] = max(1, cast(raw))
        except (TypeError, ValueError):
            pass

    backend = resolve_detector_backend(pipeline_cfg, perf_mode=mode)
    preset["detector_backend"] = backend
    variant = resolve_rfdetr_variant(pipeline_cfg)
    preset["rfdetr_variant"] = variant
    preset["rfdetr_weights"] = resolve_rfdetr_weights(variant, pipeline_cfg)

    # Detector weight: env > perception.model_name when set in quality, else preset
    # (YOLO path only — RF-DETR uses rfdetr_weights / published bare filenames.)
    env_model = (os.environ.get("EDGESIGHT_DETECT_MODEL") or "").strip()
    if env_model:
        preset["model_name"] = env_model
    elif mode == "quality" and p_cfg.get("model_name"):
        # quality may keep an explicit heavier weight from yaml
        preset["model_name"] = p_cfg["model_name"]
    elif mode in ("fast", "balanced"):
        # Prefer nano even if yaml still says yolo26s (legacy checkouts)
        preset["model_name"] = (
            perf_cfg.get("model_name")
            or (
                p_cfg.get("model_name")
                if "yolo26n" in str(p_cfg.get("model_name", ""))
                or "yolo11n" in str(p_cfg.get("model_name", ""))
                else None
            )
            or _PRESETS[mode]["model_name"]
        )

    max_cams = os.environ.get("EDGE_MAX_CAMERAS")
    if max_cams is None or str(max_cams).strip() == "":
        max_cams = perf_cfg.get("max_cameras")
    try:
        preset["max_cameras"] = int(max_cams) if max_cams not in (None, "", "null") else None
    except (TypeError, ValueError):
        preset["max_cameras"] = None

    return preset


def limit_cameras(cameras: List[Dict[str, Any]], max_cameras: Optional[int]) -> List[Dict[str, Any]]:
    if not max_cameras or max_cameras < 1:
        return list(cameras)
    return list(cameras)[:max_cameras]
