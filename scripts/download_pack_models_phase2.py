#!/usr/bin/env python3
"""
EdgeSight phase-2 model stubs (license-clean pulls).

DEFAULT = dry-run. Prints planned URLs, licenses, sizes, and disk check.
Only fetches when --download is set AND free disk ≥ --min-free-gb AND URL HEAD OK.

Pulls (when enabled):
  - RF-DETR Nano/Small COCO checkpoints (Apache-2.0) → models/pack/01-detection/rfdetr/
  - RTMPose-t/s/m ONNX SDK zips (rtmlib / Tau-J HF + OpenMMLab mirror) → models/pack/07-pose/
  - MiVOLO v2 (Apache-2.0) → models/pack/08-demographics/  [GATED — ENABLE_DEMOGRAPHICS]
  - Moondream2 config stub only by default (full weights huge; nightly shelf QA)
  - P2PNet: STUB ONLY — academic-research license → SKIP commercial download

Never downloads:
  - SKU-110K shelf weights (non-commercial)
  - LocateAnything-3B (NVIDIA non-commercial)
  - RF-DETR XL/2XL (PML 1.0 Plus — not Apache)

Std-lib + optional certifi. Mirror of phase-1 pack loader patterns.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import ssl
import sys
import urllib.request
import warnings
import zipfile
from pathlib import Path

UA = {"User-Agent": "ADLabs-EdgeSight-model-pack-phase2/1.0"}
CHUNK = 1 << 18
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DEST = _REPO_ROOT / "models" / "pack"
HF = "https://huggingface.co"
OMM = "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk"

_OPENER: urllib.request.OpenerDirector | None = None


def _opener() -> urllib.request.OpenerDirector:
    global _OPENER
    if _OPENER is not None:
        return _OPENER
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        _OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        return _OPENER
    except Exception:
        pass
    try:
        urllib.request.urlopen("https://huggingface.co/robots.txt", timeout=20)
        _OPENER = urllib.request.build_opener()
        return _OPENER
    except Exception:
        pass
    ctx = ssl.create_default_context(check_hostname=False, verify_mode=ssl.CERT_NONE)
    warnings.warn("INSECURE-TLS-FALLBACK for phase2 probe; prefer `pip install certifi`.")
    _OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    return _OPENER


# status: PACKED candidate | GATED | FUTURE | SKIP
ITEMS = [
    dict(
        id="rfdetr-nano",
        key="rf-detr-nano.pth",
        folder="01-detection/rfdetr",
        size=350_000_000,  # ~349 MB published nano COCO checkpoint (GCS Content-Length)
        sources=[
            "https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth",
        ],
        license="Apache-2.0 (Roboflow RF-DETR; code+COCO weights)",
        status="PACKED",
        purpose=(
            "RF-DETR-N — Roboflow SOTA real-time DETR (48.4 COCO AP50:95 @ 2.3 ms T4 TRT). "
            "Selectable via DETECTOR_BACKEND=rfdetr RFDETR_VARIANT=nano. Prefer nano first."
        ),
    ),
    dict(
        id="rfdetr-small",
        key="rf-detr-small.pth",
        folder="01-detection/rfdetr",
        size=370_000_000,  # ~368 MB published small COCO checkpoint (GCS Content-Length)
        sources=[
            "https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth",
        ],
        license="Apache-2.0 (Roboflow RF-DETR; code+COCO weights)",
        status="PACKED",
        purpose=(
            "RF-DETR-S — 53.0 COCO AP50:95 @ 3.5 ms T4. "
            "DETECTOR_BACKEND=rfdetr RFDETR_VARIANT=small."
        ),
    ),
    dict(
        id="rfdetr-readme",
        key="RFDETR-PACKED.txt",
        folder="01-detection/rfdetr",
        size=0,
        sources=[],
        license="Apache-2.0",
        status="PACKED",
        purpose="Stub marker so stack API can report PACKED before weights land.",
        skip=True,
        stub_text=(
            "RF-DETR (Roboflow) — Apache-2.0 SOTA object detector for EdgeSight.\n"
            "Package: pip install 'rfdetr>=1.3,<2'  (Python>=3.10)\n"
            "Weights: rf-detr-nano.pth / rf-detr-small.pth\n"
            "  GCS nano:  https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth\n"
            "  GCS small: https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth\n"
            "Env: DETECTOR_BACKEND=rfdetr RFDETR_VARIANT=nano|small\n"
            "    EDGE_PERF_MODE=quality defaults to rfdetr; fast keeps yolo26n.\n"
            "Do NOT fetch XL/2XL (PML 1.0 Plus).\n"
            "See docs/rfdetr-integration.md\n"
        ),
    ),
    dict(
        id="rtmpose-t",
        key="rtmpose-t_simcc-body7_pt-body7_420e-256x192-026a1439_20230504.zip",
        folder="07-pose",
        size=12547710,
        sources=[
            f"{HF}/Tau-J/RTMPose/resolve/main/rtmposev1/onnx_sdk/"
            "rtmpose-t_simcc-body7_pt-body7_420e-256x192-026a1439_20230504.zip",
            f"{OMM}/rtmpose-t_simcc-body7_pt-body7_420e-256x192-026a1439_20230504.zip",
        ],
        license="Apache-2.0 (Tau-J/RTMPose HF card)",
        status="PACKED",
        purpose="RTMPose-t body7 256x192 ONNX SDK zip for rtmlib — fall-candidate pose tier.",
        unpack_onnx=True,
    ),
    dict(
        id="rtmpose-s",
        key="rtmpose-s_simcc-body7_pt-body7_420e-256x192-acd4a1ef_20230504.zip",
        folder="07-pose",
        size=20496303,
        sources=[
            f"{HF}/Tau-J/RTMPose/resolve/main/rtmposev1/onnx_sdk/"
            "rtmpose-s_simcc-body7_pt-body7_420e-256x192-acd4a1ef_20230504.zip",
            f"{OMM}/rtmpose-s_simcc-body7_pt-body7_420e-256x192-acd4a1ef_20230504.zip",
        ],
        license="Apache-2.0 (Tau-J/RTMPose HF card)",
        status="PACKED",
        purpose="RTMPose-s body7 — mid accuracy pose tier.",
        unpack_onnx=True,
    ),
    dict(
        id="rtmpose-m",
        key="rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.zip",
        folder="07-pose",
        size=50799818,
        sources=[
            f"{HF}/Tau-J/RTMPose/resolve/main/rtmposev1/onnx_sdk/"
            "rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.zip",
            f"{OMM}/rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.zip",
        ],
        license="Apache-2.0 (Tau-J/RTMPose HF card)",
        status="PACKED",
        purpose="RTMPose-m body7 — accuracy tier for offline pose / fall candidates.",
        unpack_onnx=True,
    ),
    dict(
        id="mivolo-v2",
        key="model.safetensors",
        folder="08-demographics/mivolo_v2",
        size=115078528,
        sources=[f"{HF}/iitolstykh/mivolo_v2/resolve/main/model.safetensors"],
        license="Apache-2.0",
        status="GATED",
        purpose="MiVOLO v2 age/gender (body-only OK). ENABLE_DEMOGRAPHICS=1 + DPIA + k≥10 only.",
        gated=True,
    ),
    dict(
        id="mivolo-v2-config",
        key="config.json",
        folder="08-demographics/mivolo_v2",
        size=924,
        sources=[f"{HF}/iitolstykh/mivolo_v2/resolve/main/config.json"],
        license="Apache-2.0",
        status="GATED",
        purpose="MiVOLO v2 config companion.",
        gated=True,
    ),
    dict(
        id="moondream2-config",
        key="config.json",
        folder="09-vlm/moondream2",
        size=277,
        sources=[f"{HF}/vikhyatk/moondream2/resolve/main/config.json"],
        license="Apache-2.0 (model card)",
        status="FUTURE",
        purpose="Moondream2 config stub — nightly shelf-photo QA only; full weights opt-in.",
    ),
    # ---- stubs that must never auto-download ----
    dict(
        id="p2pnet",
        key="P2PNet-STUB.txt",
        folder="10-crowd",
        size=0,
        sources=[],
        license="Tencent academic-research-only (LICENSE §1)",
        status="SKIP",
        purpose="Crush-density research stub. Prefer YOLO max_det raise. Do NOT vendor for commercial.",
        skip=True,
        stub_text=(
            "P2PNet — SKIP for commercial EdgeSight.\n"
            "Upstream LICENSE restricts use to academic research.\n"
            "Upstream: https://github.com/TencentYoutuResearch/CrowdCounting-P2PNet\n"
            "Prefer raising detector max_det before any crowd-count model.\n"
        ),
    ),
    dict(
        id="sku110k",
        key="SKU110K-SKIP.txt",
        folder="06-shelf",
        size=0,
        sources=[],
        license="SKU-110K non-commercial",
        status="SKIP",
        purpose="Do not download SKU-110K weights. Use geometry OSA or Roboflow CC BY 4.0 gap data.",
        skip=True,
        stub_text=(
            "SKU-110K shelf weights — SKIP (non-commercial).\n"
            "Prefer shelf_gap_geometry from existing boxes, or Roboflow Universe CC BY 4.0 gap datasets.\n"
        ),
    ),
    dict(
        id="locateanything-3b",
        key="LocateAnything-3B-FUTURE.txt",
        folder="11-locateanything",
        size=0,
        sources=[],
        license="NVIDIA non-commercial",
        status="FUTURE",
        purpose="Already researched — do NOT download. Stay FUTURE.",
        skip=True,
        stub_text=(
            "LocateAnything-3B — FUTURE / do not download (NVIDIA non-commercial).\n"
            "See docs/locateanything-3b-integration.md and docs/model-stack-policy.md.\n"
        ),
    ),
]


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def free_bytes(path: Path) -> int:
    usage = shutil.disk_usage(str(path if path.exists() else path.parent))
    return int(usage.free)


def head_ok(url: str) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with _opener().open(req, timeout=30) as resp:
            cl = resp.getheader("Content-Length") or "?"
            return True, f"HTTP {resp.status} len={cl}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def download(url: str, dest: Path, min_size: int) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers=UA)
    with _opener().open(req, timeout=300) as resp, open(tmp, "wb") as fo:
        head = b""
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            head = (head + chunk)[:64]
            if head.startswith(b"version https://git-lfs"):
                raise ValueError("git-lfs pointer, not weights")
            fo.write(chunk)
    if tmp.stat().st_size < min_size:
        raise ValueError(f"truncated: {tmp.stat().st_size} < {min_size}")
    os.replace(tmp, dest)


def unpack_onnx_zip(zip_path: Path, folder: Path) -> list[Path]:
    out: list[Path] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.lower().endswith(".onnx"):
                target = folder / Path(name).name
                if not target.exists():
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                out.append(target)
    return out


def write_stub(dest: Path, text: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_text(text)


def write_gitignore(root: Path) -> None:
    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text(
            "# never commit model binaries\n"
            "**/*.pt\n**/*.pth\n**/*.onnx\n**/*.zip\n**/*.safetensors\n**/*.part\n"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase-2 model stubs (dry-run default).")
    ap.add_argument("--dest", default=str(_DEFAULT_DEST), help="pack root")
    ap.add_argument("--download", action="store_true",
                    help="actually fetch (default is dry-run)")
    ap.add_argument("--min-free-gb", type=float, default=8.0,
                    help="refuse --download if free disk below this (default 8)")
    ap.add_argument("--only", nargs="*", help="limit to these item ids")
    ap.add_argument("--include-gated", action="store_true",
                    help="allow MiVOLO download (still GATED at runtime)")
    ap.add_argument("--include-future-vlm-full", action="store_true",
                    help="reserved: full Moondream weights (not wired; refuse for now)")
    args = ap.parse_args()

    root = Path(args.dest).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    write_gitignore(root)

    free = free_bytes(root)
    print(f"pack root: {root}")
    print(f"free disk: {human(free)}  (min for --download: {args.min_free_gb} GB)")
    print(f"mode: {'DOWNLOAD' if args.download else 'DRY-RUN (default)'}\n")

    if args.include_future_vlm_full:
        print("REFUSE: full Moondream weights not auto-fetched this pass "
              "(nightly shelf QA only; use HF manually after review).")
        return 2

    todo = []
    for it in ITEMS:
        if args.only and it["id"] not in args.only:
            continue
        todo.append(it)

    ok = True
    for it in todo:
        dest = root / it["folder"] / it["key"]
        print(f"--- {it['id']}  status={it['status']}  license={it['license']}")
        print(f"    {it['purpose']}")
        if it.get("skip"):
            write_stub(dest, it.get("stub_text") or f"{it['id']} skipped\n")
            print(f"    [STUB] wrote {dest.relative_to(root)}")
            continue

        if it.get("gated") and not args.include_gated and args.download:
            print("    [SKIP-GATED] pass --include-gated to fetch MiVOLO (runtime still gated)")
            continue

        for url in it.get("sources") or []:
            good, note = head_ok(url)
            print(f"    HEAD {'OK' if good else 'FAIL'}  {note}  ← {url}")
            if not good:
                ok = False

        if not args.download:
            print(f"    [DRY-RUN] would write → {dest.relative_to(root)} (~{human(it['size'])})")
            continue

        if free < args.min_free_gb * (1 << 30):
            print(f"    [ABORT] free disk {human(free)} < {args.min_free_gb} GB")
            return 1

        if dest.exists() and dest.stat().st_size >= it["size"]:
            print(f"    [PRESENT] {dest.relative_to(root)}")
        else:
            last = ""
            fetched = False
            dest.parent.mkdir(parents=True, exist_ok=True)
            for url in it["sources"]:
                try:
                    download(url, dest, max(1, int(it["size"] * 0.9)))
                    print(f"    [DOWNLOADED] {dest.relative_to(root)} ← {url}")
                    fetched = True
                    break
                except Exception as e:  # noqa: BLE001
                    last = str(e)
                    dest.with_suffix(dest.suffix + ".part").unlink(missing_ok=True)
            if not fetched:
                ok = False
                print(f"    [FAILED] {last}")
                continue

        if it.get("unpack_onnx") and dest.suffix == ".zip" and dest.exists():
            extracted = unpack_onnx_zip(dest, dest.parent)
            for p in extracted:
                print(f"    [UNPACK] {p.relative_to(root)}")

    print("\n==== PHASE2 SUMMARY ====")
    print("SKU-110K: SKIP  |  LocateAnything-3B: FUTURE (no download)  |  P2PNet: SKIP commercial")
    print("MiVOLO: GATED (ENABLE_DEMOGRAPHICS=0 default)  |  Moondream: FUTURE nightly stub")
    print("RF-DETR one-command (optional, ~350MB, disk-gated):")
    print("  python3 scripts/download_pack_models_phase2.py --download --only rfdetr-nano --min-free-gb 1")
    print("See docs/model-stack-policy.md · docs/rfdetr-integration.md")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
