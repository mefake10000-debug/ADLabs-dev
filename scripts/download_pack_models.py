"""Download segregated *next-integrate* pack weights into ./models/pack/.

These are NOT production-wired. Production stack remains scripts/download_models.py
→ ./models/*.pt and ./models/onnx/.

Run:

    python scripts/download_pack_models.py

Safe to re-run; existing large-enough files are skipped.
"""
from __future__ import annotations

import os
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACK = os.path.join(ROOT, "models", "pack")

# (relpath under pack/, url, min_bytes)
PACK_MODELS = [
    (
        "01-detection/yolo26n/yolo26n.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt",
        4_000_000,
    ),
    (
        "03-reid/osnet-x0_25/osnet_x0_25_msmt17.pt",
        "https://huggingface.co/paulosantiago/osnet_x0_25_msmt17/resolve/main/osnet_x0_25_msmt17.pt",
        2_000_000,
    ),
    (
        "03-reid/osnet-x0_5/osnet_x0_5_msmt17.pth",
        "https://huggingface.co/kaiyangzhou/osnet/resolve/main/osnet_x0_5_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth",
        8_000_000,
    ),
    (
        "05-seg/yolo26m-seg/yolo26m-seg.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26m-seg.pt",
        40_000_000,
    ),
    (
        "07-openvocab/yolov8s-worldv2.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s-worldv2.pt",
        20_000_000,
    ),
]


def _download(url: str, dest: str, label: str) -> int:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    print(f"  downloading {label} ...", flush=True)
    with urllib.request.urlopen(url, timeout=180) as resp, open(tmp, "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(tmp, dest)
    return os.path.getsize(dest)


def main() -> int:
    os.makedirs(PACK, exist_ok=True)
    failures: list[str] = []
    print("Pack models (segregated / not production-wired):")
    for rel, url, min_bytes in PACK_MODELS:
        dest = os.path.join(PACK, rel)
        if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
            print(f"  {rel}: present ({os.path.getsize(dest) / 1e6:.1f}MB)")
            continue
        try:
            size = _download(url, dest, rel)
            print(f"  {rel}: downloaded ({size / 1e6:.1f}MB)")
        except Exception as e:
            print(f"  {rel}: FAILED ({e})")
            failures.append(rel)
    if failures:
        print(f"\nFAILED: {', '.join(failures)}")
        return 1
    print("\nPack models present under models/pack/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
