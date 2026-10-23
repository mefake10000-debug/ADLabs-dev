"""Declarative EdgeSight model-stack catalog (LIVE|PACKED|PARTIAL|GATED|FUTURE|SKIP).

Honest statuses for health / dashboard. Does not invent LIVE demographics.
See docs/model-stack-policy.md.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def demographics_env_enabled() -> bool:
    """DPIA gate: raw age/gender path stays off unless ENABLE_DEMOGRAPHICS=1."""
    return os.environ.get("ENABLE_DEMOGRAPHICS", "0").strip().lower() in ("1", "true", "yes", "on")


def dpia_gate_ok() -> bool:
    """Optional second latch once DPIA + k≥10 rollup is wired (default false)."""
    return os.environ.get("DEMOGRAPHICS_DPIA_OK", "0").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class StackEntry:
    key: str
    name: str
    role: str
    license: str
    status: str  # LIVE | PACKED | PARTIAL | GATED | FUTURE | SKIP
    path_hint: str = ""
    env_flag: Optional[str] = None
    notes: str = ""
    on_disk: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
            license="AGPL-3.0",
            status="LIVE",
            path_hint="models/yolo26n.pt",
            notes="Jan 2026 edge-optimized; ~38.9 ms CPU-ONNX. Keep this pass — no detector swap.",
        ),
        StackEntry(
            key="yoloe",
            name="YOLOE open-vocab",
            role="Shelf / product categories",
            license="AGPL-3.0",
            status="LIVE",
            path_hint="models/pack/06-shelf/yoloe-v8s-seg-pf.pt",
            notes="Pilot OK under AGPL; commercial needs Enterprise or Apache swap.",
        ),
        StackEntry(
            key="osnet_reid",
            name="OSNet ReID",
            role="Session-scoped soft ReID",
            license="MIT",
            status="LIVE",
            path_hint="models/pack/03-reid/",
            env_flag="models.reid.enabled + EDGE_PERF_MODE=quality",
            notes="MIT code+weights. No multi-day identity gallery.",
        ),
        StackEntry(
            key="clip_vit_b32",
            name="CLIP ViT-B/32",
            role="Zero-shot text / shelf interest",
            license="MIT",
            status="LIVE",
            path_hint="weights/clip/ViT-B-32.pt",
        ),
        StackEntry(
            key="rtmpose",
            name="RTMPose-t/s/m ONNX (rtmlib)",
            role="Pose fall-candidate tier",
            license="Apache-2.0",
            status="PACKED",
            path_hint="models/pack/07-pose/",
            notes="Phase-2 dry-run default. PARTIAL when ONNX on disk + slow-tier wire.",
        ),
        StackEntry(
            key="shelf_gap_geometry",
            name="Shelf gap / OSA geometry",
            role="Gap alerts from existing boxes",
            license="N/A (no new weights)",
            status="PARTIAL",
            path_hint="src/analytics/shelf_gap_geometry.py",
            notes="License-free recipe; prefer over SKU-110K weights.",
        ),
        StackEntry(
            key="mivolo_v2",
            name="MiVOLO v2 age/gender",
            role="Demographics (body-only OK)",
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
            license="Apache-2.0",
            status="FUTURE",
            path_hint="models/pack/09-vlm/moondream2/",
            notes="Not every-frame. On-prem OK. Config stub only in phase-2 script.",
        ),
        StackEntry(
            key="p2pnet",
            name="P2PNet crowd density",
            role="Crush-density edge cases",
            license="Tencent academic-research-only",
            status="SKIP",
            path_hint="models/pack/10-crowd/P2PNet-STUB.txt",
            notes="Prefer YOLO max_det raise. Do not vendor commercially.",
        ),
        StackEntry(
            key="sku110k",
            name="SKU-110K shelf weights",
            role="Closed-set shelf detect",
            license="Non-commercial",
            status="SKIP",
            notes="Use geometry OSA or Roboflow CC BY 4.0 gap datasets.",
        ),
        StackEntry(
            key="locateanything_3b",
            name="LocateAnything-3B",
            role="Open-vocab grounding VLM",
            license="NVIDIA non-commercial",
            status="FUTURE",
            notes="Do not download. Stay FUTURE.",
        ),
        StackEntry(
            key="apache_detector_swap",
            name="RF-DETR / D-FINE / LW-DETR",
            role="Phase-2 AGPL→Apache detector option",
            license="Apache-2.0",
            status="FUTURE",
            notes=(
                "Bench vs Docker 4.7–6.4 s/frame baseline + ~7 fps native MPS YOLO26n. "
                "Do not switch detectors in this pass."
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
            if on and e.status == "PACKED":
                e.status = "PARTIAL"
                e.notes = "ONNX present — wire slow-tier SAFETY_FALL_CANDIDATE_POSE (candidate-only)."
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

    return {
        "policy": "docs/model-stack-policy.md",
        "env": {
            "ENABLE_DEMOGRAPHICS": os.environ.get("ENABLE_DEMOGRAPHICS", "0"),
            "DEMOGRAPHICS_DPIA_OK": os.environ.get("DEMOGRAPHICS_DPIA_OK", "0"),
            "demographics_runtime_allowed": demo_on,
            "EDGE_PERF_MODE": os.environ.get("EDGE_PERF_MODE", "fast"),
        },
        "models": [e.to_dict() for e in entries],
        "phase2": {
            "script": "scripts/download_pack_models_phase2.py",
            "default": "dry-run",
            "download_flag": "--download",
        },
    }
