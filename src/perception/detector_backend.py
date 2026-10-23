"""Detector backend selection (YOLO26 fast path vs RF-DETR SOTA/alternate).

Env (wins over yaml):
  DETECTOR_BACKEND=yolo26|rfdetr
  RFDETR_VARIANT=nano|small          # Apache-2.0 sizes only (not XL/2XL PML)
  RFDETR_WEIGHTS=<path|filename>     # optional; bare name uses RF_HOME cache
  RF_HOME / ROBOFLOW_HOME            # rfdetr weight cache (upstream)

Defaults:
  EDGE_PERF_MODE=fast     → yolo26 (YOLO26n)
  EDGE_PERF_MODE=quality  → rfdetr (SOTA Apache path) unless DETECTOR_BACKEND set
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

BACKEND_YOLO26 = "yolo26"
BACKEND_RFDETR = "rfdetr"
_VALID_BACKENDS = (BACKEND_YOLO26, BACKEND_RFDETR)
_VALID_VARIANTS = ("nano", "small")

# Upstream published weight filenames (Apache-2.0 COCO checkpoints).
RFDETR_WEIGHT_IDS = {
    "nano": "rf-detr-nano.pth",
    "small": "rf-detr-small.pth",
}

RFDETR_GCS_URLS = {
    "nano": "https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth",
    "small": "https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth",
}

# Fixed native resolutions (RF-DETR letterbox is model-owned; imgsz is informational).
RFDETR_RESOLUTIONS = {
    "nano": 384,
    "small": 512,
}


def resolve_detector_backend(
    pipeline_cfg: Optional[Dict[str, Any]] = None,
    perf_mode: Optional[str] = None,
) -> str:
    """Pick yolo26 (fast default) or rfdetr (quality/SOTA default)."""
    env = (os.environ.get("DETECTOR_BACKEND") or "").strip().lower()
    if env in _VALID_BACKENDS:
        return env

    cfg = (pipeline_cfg or {}).get("perception") or {}
    raw = str(cfg.get("detector_backend") or "").strip().lower()
    if raw in _VALID_BACKENDS:
        return raw

    mode = (perf_mode or "").strip().lower()
    if not mode:
        mode = (os.environ.get("EDGE_PERF_MODE") or "").strip().lower()
    if mode == "quality":
        return BACKEND_RFDETR
    return BACKEND_YOLO26


def resolve_rfdetr_variant(pipeline_cfg: Optional[Dict[str, Any]] = None) -> str:
    env = (os.environ.get("RFDETR_VARIANT") or "").strip().lower()
    if env in _VALID_VARIANTS:
        return env
    cfg = (pipeline_cfg or {}).get("perception") or {}
    raw = str(cfg.get("rfdetr_variant") or "").strip().lower()
    if raw in _VALID_VARIANTS:
        return raw
    # Prefer nano first (disk + latency); quality can opt into small via env.
    return "nano"


def resolve_rfdetr_weights(
    variant: str,
    pipeline_cfg: Optional[Dict[str, Any]] = None,
) -> str:
    """Return path or published bare filename for RFDETR*.pretrain_weights."""
    env = (os.environ.get("RFDETR_WEIGHTS") or "").strip()
    if env:
        return env
    cfg = (pipeline_cfg or {}).get("perception") or {}
    raw = str(cfg.get("rfdetr_weights") or "").strip()
    if raw:
        return raw

    # Prefer pack path when present (download script / mount).
    pack_rel = f"models/pack/01-detection/rfdetr/{RFDETR_WEIGHT_IDS[variant]}"
    if os.path.isfile(pack_rel) and os.path.getsize(pack_rel) > 1000:
        return pack_rel

    # Bare published name → rfdetr downloads into RF_HOME (~/.roboflow/models).
    return RFDETR_WEIGHT_IDS.get(variant, RFDETR_WEIGHT_IDS["nano"])


def backend_label(backend: str, variant: Optional[str] = None) -> str:
    if backend == BACKEND_RFDETR:
        v = variant or resolve_rfdetr_variant()
        return f"rfdetr-{v}"
    return "yolo26"


def rfdetr_runtime_probe() -> Tuple[bool, str]:
    """Return (import_ok, detail) without loading weights."""
    try:
        import rfdetr  # noqa: F401
        from rfdetr import RFDETRNano, RFDETRSmall  # noqa: F401
        return True, f"rfdetr={getattr(rfdetr, '__version__', 'unknown')}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"
