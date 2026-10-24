#!/usr/bin/env python3
"""Launch one native live edge with a bounded, concurrent model profile.

Uses the machine-local model paths/camera calibration, but shares the edge storage
directory with the host API so the live panel, frames, and telemetry agree.
"""
from __future__ import annotations

import os
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "MiVOLO"))

import yaml

from src.perception.live_runtime import build_live_profile


def main() -> None:
    base_config = os.environ.get("EDGE_BASE_PIPELINE_CONFIG", "local-runtime/pipeline.native.yaml")
    try:
        with open(base_config, "r", encoding="utf-8") as stream:
            pipeline = yaml.safe_load(stream) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"Cannot load local model profile {base_config}: {exc}")

    shared_db = (
        os.environ.get("EDGE_SHARED_DB_PATH")
        or os.environ.get("SERVER_DB_PATH")
        or str(Path.home() / "Desktop/ad-labs-project/repos/ADLabs-dev/data/storage/edgesight.db")
    )
    profile = build_live_profile(pipeline, shared_db_path=shared_db)
    cameras_config = os.environ.get("CAMERAS_CONFIG", "local-runtime/cameras.yaml")

    with tempfile.TemporaryDirectory(prefix="edgesight-live-") as tmpdir:
        pipeline_path = Path(tmpdir) / "pipeline.live.yaml"
        pipeline_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
        os.environ.update({
            "PYTHONUNBUFFERED": "1",
            "PIPELINE_CONFIG": str(pipeline_path),
            "CAMERAS_CONFIG": str((ROOT / cameras_config).resolve()),
            "EDGE_PERF_MODE": "quality",
            "EDGE_ENRICHMENT": "1",
            # Only the entrance sample has real people; checkout_sample is a color-bar test pattern.
            "EDGE_MAX_CAMERAS": "1",
            "EDGESIGHT_DETECT_MODEL": "models/yolo26s.pt",
            "OVERLAY_BOX_STYLE": "aabb",
            "OVERLAY_SHOW_STORE_OBJECTS": "0",
            "ENABLE_RTMPOSE": "1",
            "RTMPOSE_VARIANT": "t",
            "RTMPOSE_EVERY_N": "4",
            "ENABLE_DEMOGRAPHICS": "1",
            "EDGE_RUN_RFDETR_AUDIT": "0",
            "YOLO_AUTOINSTALL": "false",
            "TELEMETRY_LOCAL_ENDPOINT": "http://127.0.0.1:8000/api/v1/telemetry",
            "TELEMETRY_CLOUD_ENDPOINT": "http://127.0.0.1:8000/api/v1/telemetry",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        })

        try:
            import cv2
            import ultralytics.utils.torch_utils as torch_utils

            torch_utils.NUM_THREADS = 2
            cv2.setNumThreads(1)
        except ImportError:
            pass

        print(
            "Native live profile: YOLO26s/MPS + parallel slow-model workers; "
            "AABB boxes; 1 real-person camera; shared host API storage.",
            flush=True,
        )
        runpy.run_module("src.main", run_name="__main__")


if __name__ == "__main__":
    main()
