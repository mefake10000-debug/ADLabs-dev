"""Declarative EdgeSight model-stack catalog (LIVE|PACKED|PARTIAL|GATED|FUTURE|SKIP|OFF).

Honest statuses for health / dashboard. Does not invent LIVE demographics.
See docs/model-stack-policy.md.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.perception.detector_backend import (
    BACKEND_RFDETR,
    RFDETR_WEIGHT_IDS,
    resolve_detector_backend,
    resolve_rfdetr_variant,
    rfdetr_runtime_probe,
)


def demographics_env_enabled() -> bool:
    """DPIA gate: raw age/gender path stays off unless ENABLE_DEMOGRAPHICS=1."""
    return os.environ.get("ENABLE_DEMOGRAPHICS", "0").strip().lower() in ("1", "true", "yes", "on")


def dpia_gate_ok() -> bool:
    """Optional second latch once DPIA + k≥10 rollup is wired (default false)."""
    return os.environ.get("DEMOGRAPHICS_DPIA_OK", "0").strip().lower() in ("1", "true", "yes", "on")


def run_state_for(status: str) -> str:
    """Operator-facing strip status: ON | OFF | WAITING (never invent LIVE demos)."""
    s = (status or "").upper()
    if s == "LIVE":
        return "ON"
    if s in ("PACKED", "PARTIAL"):
        return "WAITING"
    return "OFF"


@dataclass
class StackEntry:
    key: str
    name: str
    role: str
    license: str
    status: str  # LIVE | PACKED | PARTIAL | GATED | FUTURE | SKIP | OFF
    path_hint: str = ""
    env_flag: Optional[str] = None
    notes: str = ""
    on_disk: Optional[bool] = None
    # Operator Models strip (plain English; no AGPL/path spam on primary UI)
    job: str = ""
    feeds_kpi: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["run_state"] = run_state_for(self.status)
        d["job"] = self.job or self.role
        return d


def _exists(base: Path, rel: str) -> bool:
    if not rel:
        return False
    p = Path(rel) if os.path.isabs(rel) else base / rel
    try:
        return p.is_file() and p.stat().st_size > 100
    except OSError:
        return False


def _any_exists(base: Path, *rels: str) -> bool:
    return any(_exists(base, r) for r in rels if r)


def build_model_stack(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """Catalog + disk probes for GET /api/v1/models/stack."""
    base = Path(base_dir or os.getcwd())
    demo_on = demographics_env_enabled() and dpia_gate_ok()

    entries: List[StackEntry] = [
        StackEntry(
            key="yolo26n",
            name="YOLO26n detector",
            role="Person detect (fast / edge)",
            job="Finds people in the camera frame",
            feeds_kpi="Present · In/Out (with entrance line)",
            license="AGPL-3.0",
            status="LIVE",
            path_hint="models/yolo26n.pt",
            env_flag="DETECTOR_BACKEND=yolo26 (Ultralytics default, all perf modes)",
            notes="Jan 2026 edge-optimized; ~38.9 ms CPU-ONNX. Default person detector.",
        ),
        StackEntry(
            key="yoloe",
            name="YOLOE open-vocab",
            role="Shelf / product categories",
            job="Names product categories on shelves",
            feeds_kpi="Shelf / display interest",
            license="AGPL-3.0",
            status="LIVE",
            path_hint="models/pack/06-shelf/yoloe-v8s-seg-pf.pt",
            notes="Pilot OK under AGPL; commercial needs Enterprise or Apache swap.",
        ),
        StackEntry(
            key="osnet_reid",
            name="OSNet ReID",
            role="Session-scoped soft ReID",
            job="Keeps the same person ID within a short visit",
            feeds_kpi="Path / journey (same visit)",
            license="MIT",
            status="LIVE",
            path_hint="models/pack/03-reid/",
            env_flag="models.reid.enabled + EDGE_PERF_MODE=quality",
            notes="MIT code+weights. No multi-day identity gallery.",
        ),
        StackEntry(
            key="clip_vit_b32",
            name="CLIP ViT-B/32",
            job="Matches on-screen objects to text labels",
            feeds_kpi="Shelf category tags",
            role="Zero-shot text / shelf interest",
            license="MIT",
            status="LIVE",
            path_hint="weights/clip/ViT-B-32.pt",
        ),
        StackEntry(
            key="rtmpose",
            name="RTMPose-t/s ONNX (rtmlib)",
            role="Ankle / foot pose + fall-candidate",
            job="Red foot mark, skeleton, tripwire/dwell ground point",
            feeds_kpi="Footfall · dwell · safety cautions",
            license="Apache-2.0",
            status="PACKED",
            path_hint="models/pack/07-pose/",
            notes="LIVE when ONNX on disk and RTMPoseFootEstimator active.",
        ),
        StackEntry(
            key="shelf_gap_geometry",
            name="Shelf gap / OSA geometry",
            role="Gap alerts from existing boxes",
            job="Spots empty shelf gaps from boxes already drawn",
            feeds_kpi="Shelf gap alerts",
            license="N/A (no new weights)",
            status="PARTIAL",
            path_hint="src/analytics/shelf_gap_geometry.py",
            notes="License-free recipe; prefer over SKU-110K weights.",
        ),
        StackEntry(
            key="mivolo_v2",
            name="MiVOLO v2 age/gender",
            role="Demographics (body-only OK)",
            job="Age/gender groups only after privacy gate",
            feeds_kpi="Age & groups (when enabled)",
            license="Apache-2.0",
            status="GATED" if not demo_on else "PACKED",
            path_hint="models/pack/08-demographics/mivolo_v2/",
            env_flag="ENABLE_DEMOGRAPHICS=0 (default) + DEMOGRAPHICS_DPIA_OK + k≥10",
            notes="UI must never show raw age/gender as LIVE without aggregation gate.",
        ),
        StackEntry(
            key="moondream",
            name="Moondream lean VLM",
            role="Nightly shelf-photo QA",
            job="Nightly photo check of shelf look",
            feeds_kpi="Shelf QA (nightly)",
            license="Apache-2.0",
            status="FUTURE",
            path_hint="models/pack/09-vlm/moondream2/",
            notes="Not every-frame. On-prem OK. Config stub only in phase-2 script.",
        ),
        StackEntry(
            key="p2pnet",
            name="P2PNet crowd density",
            role="Crush-density edge cases",
            job="Crowd density (research only — skipped)",
            feeds_kpi="—",
            license="Tencent academic-research-only",
            status="SKIP",
            path_hint="models/pack/10-crowd/P2PNet-STUB.txt",
            notes="Prefer YOLO max_det raise. Do not vendor commercially.",
        ),
        StackEntry(
            key="sku110k",
            name="SKU-110K shelf weights",
            role="Closed-set shelf detect",
            job="Closed-set SKU detect (skipped — non-commercial)",
            feeds_kpi="—",
            license="Non-commercial",
            status="SKIP",
            notes="Use geometry OSA or Roboflow CC BY 4.0 gap datasets.",
        ),
        StackEntry(
            key="locateanything_3b",
            name="LocateAnything-3B",
            role="Open-vocab grounding VLM",
            job="Grounding VLM (not installed)",
            feeds_kpi="—",
            license="NVIDIA non-commercial",
            status="FUTURE",
            notes="Do not download. Stay FUTURE.",
        ),
        StackEntry(
            key="rfdetr",
            name="RF-DETR-N/S (Roboflow)",
            role="Person detect (SOTA / Apache alternate)",
            job="Finds people (alternate detector)",
            feeds_kpi="Present · In/Out (with entrance line)",
            license="Apache-2.0",
            status="PACKED",
            path_hint="models/pack/01-detection/rfdetr/",
            env_flag="DETECTOR_BACKEND=rfdetr · RFDETR_VARIANT=nano|small",
            notes=(
                "Roboflow SOTA real-time DETR. Package `rfdetr` (PyPI). "
                "Weights rf-detr-nano.pth / rf-detr-small.pth. "
                "LIVE when selected+loaded; PACKED when available but not selected; OFF if missing."
            ),
        ),
    ]

    # Disk probes + status refinement
    for e in entries:
        if e.key == "yolo26n":
            e.on_disk = _any_exists(base, "models/yolo26n.pt")
        elif e.key == "yoloe":
            e.on_disk = _any_exists(
                base,
                "models/pack/06-shelf/yoloe-v8s-seg-pf.pt",
                "models/yolov8s-worldv2.pt",
            )
        elif e.key == "osnet_reid":
            reid_dir = base / "models/pack/03-reid"
            e.on_disk = _any_exists(base, "models/pack/03-reid/osnet_x0_25_msmt17.onnx")
            if not e.on_disk and reid_dir.is_dir():
                e.on_disk = any(reid_dir.glob("osnet*.pth"))
        elif e.key == "clip_vit_b32":
            e.on_disk = _any_exists(
                base,
                "weights/clip/ViT-B-32.pt",
                "models/pack/05-open-vocab/clip-vit-base-patch32/pytorch_model.bin",
            )
        elif e.key == "rtmpose":
            pose_dir = base / "models/pack/07-pose"
            on = pose_dir.is_dir() and any(pose_dir.glob("*.onnx"))
            e.on_disk = on
            # Runtime latch from edge process (main sets after successful load).
            runtime = os.environ.get("RTMPOSE_RUNTIME_LOADED", "").strip().lower() in (
                "1", "true", "yes", "on",
            )
            enable = (os.environ.get("ENABLE_RTMPOSE") or "1").strip().lower() not in (
                "0", "false", "off", "no",
            )
            if on and runtime and enable:
                e.status = "LIVE"
                e.notes = (
                    "ON — ankle feet feed overlay/tripwire/dwell. "
                    "Fall-candidate remains caution-only."
                )
            elif on and enable:
                e.status = "PARTIAL"
                e.notes = (
                    "ONNX on disk — waiting for edge RTMPoseFootEstimator "
                    "(ENABLE_RTMPOSE=1). Overlay foot falls back to bbox bottom-center until then."
                )
            elif on:
                e.status = "PACKED"
                e.notes = "ONNX present but ENABLE_RTMPOSE=0."
        elif e.key == "mivolo_v2":
            e.on_disk = _any_exists(
                base,
                "models/pack/08-demographics/mivolo_v2/model.safetensors",
            )
            if not demo_on:
                e.status = "GATED"
        elif e.key == "moondream":
            e.on_disk = _any_exists(base, "models/pack/09-vlm/moondream2/config.json")
        elif e.key == "shelf_gap_geometry":
            e.on_disk = (base / "src/analytics/shelf_gap_geometry.py").is_file()
        elif e.key == "rfdetr":
            variant = resolve_rfdetr_variant()
            weight_name = RFDETR_WEIGHT_IDS.get(variant, RFDETR_WEIGHT_IDS["nano"])
            pack_path = base / "models/pack/01-detection/rfdetr" / weight_name
            rf_home = Path(
                os.path.expanduser(
                    os.environ.get("RF_HOME")
                    or os.environ.get("ROBOFLOW_HOME")
                    or "~/.roboflow/models"
                )
            )
            cache_path = rf_home / weight_name
            stub = base / "models/pack/01-detection/rfdetr/RFDETR-PACKED.txt"
            e.on_disk = _exists(base, str(pack_path)) or (
                cache_path.is_file() and cache_path.stat().st_size > 1000
            )
            import_ok, import_detail = rfdetr_runtime_probe()
            selected = resolve_detector_backend() == BACKEND_RFDETR
            runtime_loaded = os.environ.get("RFDETR_RUNTIME_LOADED", "").strip() in (
                "1", "true", "yes", "on",
            )
            if selected and (runtime_loaded or (import_ok and e.on_disk)):
                e.status = "LIVE"
                e.notes = (
                    f"Selected DETECTOR_BACKEND=rfdetr ({variant}). "
                    f"{import_detail}. xyxy → ByteTrack; overlays unchanged."
                )
            elif selected and import_ok and not e.on_disk:
                e.status = "PACKED"
                e.notes = (
                    f"Selected but weights not on disk yet — "
                    f"`pip install rfdetr` then instantiate (auto-fetch) or "
                    f"`--download --only rfdetr-{variant}`. {import_detail}"
                )
            elif e.on_disk or stub.is_file() or import_ok:
                e.status = "PACKED"
                e.notes = (
                    f"Available (variant={variant}); not selected. "
                    f"Set DETECTOR_BACKEND=rfdetr to go LIVE (opt-in; Ultralytics is default). "
                    f"{import_detail}"
                )
            else:
                e.status = "OFF"
                e.notes = (
                    "Package/weights missing. "
                    "`pip install 'rfdetr>=1.3,<2'` + phase2 download stub. "
                    f"{import_detail}"
                )
            e.path_hint = str(pack_path.relative_to(base)) if pack_path.exists() else (
                f"models/pack/01-detection/rfdetr/{weight_name}"
            )

    # Honest detector LIVE only for the selected backend.
    # Do not flip YOLO to OFF on a failed path probe — Ultralytics may load from cache
    # while still producing live boxes (site strip also reconciles with live.models).
    backend = resolve_detector_backend()
    for e in entries:
        if e.key == "yolo26n" and backend == BACKEND_RFDETR:
            e.status = "PACKED"
            e.notes = (
                "Fast-path YOLO26n kept as selectable alternate "
                "(DETECTOR_BACKEND=yolo26). RF-DETR currently selected."
            )
        elif e.key in ("osnet_reid", "clip_vit_b32") and e.status == "LIVE":
            perf = os.environ.get("EDGE_PERF_MODE", "balanced").strip().lower()
            if e.on_disk is False:
                e.status = "PACKED"
                e.notes = (e.notes or "") + " Weights not on probed path — waiting."
            elif perf in ("fast", "balanced"):
                e.status = "PACKED"
                e.notes = (e.notes or "") + " Waiting: set EDGE_PERF_MODE=quality to run."
        elif e.key == "yoloe" and e.status == "LIVE" and e.on_disk is False:
            e.status = "PACKED"
            e.notes = (e.notes or "") + " Weights not on probed path — waiting."

    return {
        "policy": "docs/model-stack-policy.md",
        "env": {
            "ENABLE_DEMOGRAPHICS": os.environ.get("ENABLE_DEMOGRAPHICS", "0"),
            "DEMOGRAPHICS_DPIA_OK": os.environ.get("DEMOGRAPHICS_DPIA_OK", "0"),
            "demographics_runtime_allowed": demo_on,
            "EDGE_PERF_MODE": os.environ.get("EDGE_PERF_MODE", "balanced"),
            "DETECTOR_BACKEND": resolve_detector_backend(),
            "RFDETR_VARIANT": resolve_rfdetr_variant(),
            "RFDETR_RUNTIME_LOADED": os.environ.get("RFDETR_RUNTIME_LOADED", "0"),
        },
        "models": [e.to_dict() for e in entries],
        "phase2": {
            "script": "scripts/download_pack_models_phase2.py",
            "default": "dry-run",
            "download_flag": "--download",
        },
    }
