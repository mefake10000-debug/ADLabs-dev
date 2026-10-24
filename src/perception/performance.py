"""Live-demo performance presets (fast | balanced | detect | quality).

Docker on Mac ARM runs PyTorch CPU-only. Enabling pose / YuNet / YOLO-World+CLIP
on every stream collapses infer FPS to ~0.3–1. Fast keeps max display FPS;
balanced is the lighter nano letterbox; **detect** (demo default) is
quality-leaning Ultralytics (yolo26s, imgsz 640, infer every 2 frames) so
people in frame are not missed. Quality restores the enrichment tier.
RF-DETR is never a default — only ``DETECTOR_BACKEND=rfdetr``.

Env (wins over yaml mode):
  EDGE_PERF_MODE=fast|balanced|detect|quality
  EDGE_MAX_CAMERAS=<int>
  EDGESIGHT_DETECT_MODEL=<path>   # optional YOLO weight override
  DETECTOR_BACKEND=yolo26|rfdetr  # Ultralytics unless rfdetr is set explicitly
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

_VALID_MODES = ("fast", "balanced", "detect", "quality")

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

# Lighter nano letterbox. Opt-in when detect (yolo26s @ 640) is too slow.
BALANCED_PRESET: Dict[str, Any] = {
    "mode": "balanced",
    "model_name": "models/yolo26n.pt",
    "imgsz": 416,
    "infer_every_n": 2,
    "display_every_n": 1,
    "enrichment": False,
    "reid": False,
    "detector_backend": BACKEND_YOLO26,
}

# Demo default: quality-leaning people recall without the enrichment tier.
# yolo26s @ 640, still skip every other frame so Docker CPU can draw feet.
# Person conf stays in 0.20–0.25; store objects use a higher bar.
DETECT_PRESET: Dict[str, Any] = {
    "mode": "detect",
    "model_name": "models/yolo26s.pt",
    "imgsz": 640,
    "infer_every_n": 2,
    "display_every_n": 1,
    "enrichment": False,
    "reid": False,
    "detector_backend": BACKEND_YOLO26,
    "person_conf": 0.22,
    "object_conf": 0.45,
    "track_thresh": 0.25,
}

QUALITY_PRESET: Dict[str, Any] = {
    "mode": "quality",
    "model_name": "models/yolo26s.pt",  # Ultralytics; RF-DETR only if explicitly selected
    "imgsz": 640,
    "infer_every_n": 1,
    "display_every_n": 2,
    "enrichment": True,
    "reid": False,  # still opt-in via models.reid.enabled
    "detector_backend": BACKEND_YOLO26,
}

_PRESETS = {
    "fast": FAST_PRESET,
    "balanced": BALANCED_PRESET,
    "detect": DETECT_PRESET,
    "quality": QUALITY_PRESET,
}

_DETECT_WEIGHT_FALLBACKS = (
    "models/yolo26s.pt",
    "models/pack/01-detection/yolo26s/yolo26s.pt",
    "models/yolo26n.pt",
)


def resolve_perf_mode(pipeline_cfg: Dict[str, Any]) -> str:
    env = (os.environ.get("EDGE_PERF_MODE") or "").strip().lower()
    if env in _VALID_MODES:
        return env
    cfg = pipeline_cfg.get("performance") or {}
    mode = str(cfg.get("mode", "detect") or "detect").strip().lower()
    return mode if mode in _VALID_MODES else "detect"


def rfdetr_audit_enabled(env: Optional[Dict[str, str]] = None) -> bool:
    """The standalone RF-DETR audit is off unless explicitly requested.

    It runs a second detector process and is not part of visitor counts; leaving it
    on beside the live edge steals CPU from the people/tracking pipeline.
    """
    source = env if env is not None else os.environ
    return str(source.get("EDGE_RUN_RFDETR_AUDIT", "0")).strip().lower() in ("1", "true", "yes", "on")


def _first_existing_weight(*candidates: str) -> str:
    """Return the first weight file that exists, else the preferred name."""
    preferred = ""
    for candidate in candidates:
        path = (candidate or "").strip()
        if not path:
            continue
        if not preferred:
            preferred = path
        if os.path.isfile(path) and os.path.getsize(path) > 1000:
            return path
    return preferred


def resolve_performance(pipeline_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Merge yaml + env into concrete knobs used by EdgePipeline.

    Numeric yaml knobs describe ``performance.mode``. They apply only when that
    mode is the one we resolved, so ``EDGE_PERF_MODE=fast`` does not inherit
    detect's ``imgsz=640``.
    """
    mode = resolve_perf_mode(pipeline_cfg)
    preset = dict(_PRESETS[mode])
    perf_cfg = pipeline_cfg.get("performance") or {}
    p_cfg = pipeline_cfg.get("perception") or {}
    yaml_mode = str(perf_cfg.get("mode") or "").strip().lower()
    env_mode = (os.environ.get("EDGE_PERF_MODE") or "").strip().lower()
    same_mode = (not env_mode) or yaml_mode == mode or yaml_mode not in _VALID_MODES

    if same_mode:
        for key, cast in (("imgsz", int), ("infer_every_n", int), ("display_every_n", int)):
            if key not in perf_cfg and key not in p_cfg:
                continue
            raw = perf_cfg.get(key, p_cfg.get(key))
            try:
                preset[key] = max(1, cast(raw))
            except (TypeError, ValueError):
                pass

    backend = resolve_detector_backend(pipeline_cfg, perf_mode=mode)
    preset["detector_backend"] = backend
    variant = resolve_rfdetr_variant(pipeline_cfg)
    preset["rfdetr_variant"] = variant
    preset["rfdetr_weights"] = resolve_rfdetr_weights(variant, pipeline_cfg)

    # Detector weight: env > mode preset. Detect prefers yolo26s on disk, else nano
    # at the same imgsz (recall via letterbox when the small weight is absent).
    env_model = (os.environ.get("EDGESIGHT_DETECT_MODEL") or "").strip()
    if env_model:
        preset["model_name"] = env_model
    elif mode == "detect":
        preferred = _PRESETS["detect"]["model_name"]
        if same_mode and "yolo26s" in str(p_cfg.get("model_name") or ""):
            preferred = str(p_cfg.get("model_name"))
        preset["model_name"] = _first_existing_weight(preferred, *_DETECT_WEIGHT_FALLBACKS)
    elif mode == "quality" and same_mode and p_cfg.get("model_name"):
        preset["model_name"] = p_cfg["model_name"]
    elif mode in ("fast", "balanced") and same_mode:
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

    if mode == "detect":
        raw_person = preset.get("person_conf", 0.22)
        if same_mode and p_cfg.get("person_confidence") is not None:
            raw_person = p_cfg.get("person_confidence")
        try:
            person_conf = float(raw_person)
        except (TypeError, ValueError):
            person_conf = 0.22
        # Demo person bar stays inside 0.20–0.25 (yaml 0.50 must not hide people).
        preset["person_conf"] = min(0.25, max(0.20, person_conf))
        raw_object = preset.get("object_conf", 0.45)
        if same_mode and p_cfg.get("object_confidence") is not None:
            raw_object = p_cfg.get("object_confidence")
        try:
            object_conf = float(raw_object)
        except (TypeError, ValueError):
            object_conf = 0.45
        preset["object_conf"] = max(preset["person_conf"] + 0.10, object_conf)
        raw_track = preset.get("track_thresh", 0.25)
        try:
            track_thresh = float(raw_track)
        except (TypeError, ValueError):
            track_thresh = 0.25
        preset["track_thresh"] = min(0.30, max(preset["person_conf"], track_thresh))
    else:
        preset.setdefault("person_conf", None)
        preset.setdefault("object_conf", 0.45)
        preset.setdefault("track_thresh", None)

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
