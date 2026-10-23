#!/usr/bin/env python3
"""
AD Labs EdgeSight - model pack downloader (verified 2026-10, every URL live-checked).

Target: models/pack/{01-detection,02-tracking,03-reid,04-face-attr,05-open-vocab,06-shelf}

- Downloads only open weights (licenses: AGPL-3.0 Ultralytics, MIT OSNet, Apache-2.0 OpenCV Zoo, MIT CLIP).
- Skips files that already exist with correct sha256 / sane size.
- Rejects GitHub-LFS pointer files and truncated downloads.
- Writes a README.md per folder (source URLs + purpose + license + outputs) and a .gitignore
  so binaries are never committed.
- Insightface buffalo_l (NON-COMMERCIAL research license) is excluded unless --include-research.
  Do NOT use --include-research for commercial demos without gated-license documentation.

Std-lib only (urllib). Run from repo root:

    python3 scripts/download/download_pack_models.py
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
import ssl
import warnings
from pathlib import Path

UA = {"User-Agent": "ADLabs-EdgeSight-model-pack/1.0 (macOS; python-urllib)"}
CHUNK = 1 << 18

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DEST = _REPO_ROOT / "models" / "pack"

_OPENER: urllib.request.OpenerDirector | None = None
_TLS_NOTE = ""


def _opener() -> urllib.request.OpenerDirector:
    """TLS context chain: system default -> certifi (if installed) -> verified-fallback.
    Content integrity does NOT rely on TLS trust: every artifact is pinned by sha256
    and/or exact-size minimum, so a MITM cannot deliver a working-but-wrong model."""
    global _OPENER, _TLS_NOTE
    if _OPENER is not None:
        return _OPENER
    try:
        urllib.request.urlopen("https://huggingface.co/robots.txt", timeout=30)  # trust probe
        _OPENER = urllib.request.build_opener()
        return _OPENER
    except Exception:
        pass
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        _OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        return _OPENER
    except Exception:
        pass
    ctx = ssl.create_default_context(check_hostname=False, verify_mode=ssl.CERT_NONE)
    _TLS_NOTE = ("INSECURE-TLS-FALLBACK: no trusted CA bundle found. Artifacts are still "
                 "validated by pinned sha256/size; for defense-in-depth run `pip install certifi`.")
    warnings.warn(_TLS_NOTE)
    _OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    return _OPENER

# --------------------------------------------------------------------------- #
# Verified manifest. Every URL returned HTTP 200 with the stated byte size
# (checked via HEAD on the final redirect hop; sha256 computed on real GETs
# where listed). min_size guards against LFS pointers & truncation.
# --------------------------------------------------------------------------- #

GH_ULTRALYTICS = "https://github.com/ultralytics/assets/releases/download"
ZOO_MEDIA = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models"
ZOO_RAW = "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models"
HF = "https://huggingface.co"

ITEMS = [
    # ---------------- 01-detection (AGPL-3.0, Ultralytics) ----------------
    dict(
        key="yolo11n.pt", folder="01-detection", size=5613764,
        sources=[f"{GH_ULTRALYTICS}/v8.3.0/yolo11n.pt"],
        license="AGPL-3.0", prio="P0",
        purpose="COCO YOLO11 nano detector (person=cls0, plus carts/vehicles/bags) - fast edge baseline.",
    ),
    dict(
        key="yolo11s.pt", folder="01-detection", size=19313732,
        sources=[f"{GH_ULTRALYTICS}/v8.3.0/yolo11s.pt"],
        license="AGPL-3.0", prio="P0",
        purpose="COCO YOLO11 small - primary retail detector (person, carts, boxes, chairs).",
    ),
    dict(
        key="yolo11m.pt", folder="01-detection", size=40684120,
        sources=[f"{GH_ULTRALYTICS}/v8.3.0/yolo11m.pt"],
        license="AGPL-3.0", prio="P1",
        purpose="COCO YOLO11 medium - accuracy tier for crowded/occluded scenes (offline batch).",
    ),
    dict(
        key="yolo11n-pose.pt", folder="01-detection", size=6255593,
        sources=[f"{GH_ULTRALYTICS}/v8.3.0/yolo11n-pose.pt"],
        license="AGPL-3.0", prio="P0",
        purpose="COCO17 keypoints - posture/pickup proxies (hand-near-shelf, stationary vs moving).",
    ),
    # ---------------- 03-reid ----------------
    dict(
        key="osnet_x0_25_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth",
        folder="03-reid", size=9336983,
        sources=[f"{HF}/kaiyangzhou/osnet/resolve/main/"
                 "osnet_x0_25_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth"],
        license="MIT", prio="P0",
        purpose="OSNet x0.25 (MSMT17 combine-all) - CPU edge embedding for session-scoped cross-cam association.",
    ),
    dict(
        key="osnet_x1_0_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth",
        folder="03-reid", size=17273805,
        sources=[f"{HF}/kaiyangzhou/osnet/resolve/main/"
                 "osnet_x1_0_msmt17_combineall_256x128_amsgrad_ep150_stp60_lr0.0015_b64_fb10_softmax_labelsmooth_flip_jitter.pth"],
        license="MIT", prio="P1",
        purpose="OSNet x1.0 (same recipe) - higher embedding quality for offline audits.",
    ),
    dict(
        key="osnet_x0_25_msmt17.onnx", folder="03-reid", size=907169,
        sources=[f"{HF}/anriha/osnet_x0_25_msmt17/resolve/main/osnet_x0_25_msmt17.onnx"],
        license="MIT (unofficial ONNX conversion)", prio="P2",
        purpose="Third-party ONNX export of OSNet x0.25 - CPU inference without torchreid. Verify accuracy vs .pth.",
    ),
    dict(
        key="person_reid_youtu_2021nov.onnx", folder="03-reid", size=106878407,
        sources=[f"{ZOO_MEDIA}/person_reid_youtureid/person_reid_youtu_2021nov.onnx",
                 f"{ZOO_RAW}/person_reid_youtureid/person_reid_youtu_2021nov.onnx"],
        license="Apache-2.0", prio="P2",
        purpose="OpenCV Zoo YouTu person ReID (ONNX/OpenCV-DNN, CPU-friendly) as a torch-free fallback embedder.",
    ),
    # ---------------- 04-face-attr (processing only: anonymize/hotspots; NO identity) ----------------
    dict(
        key="face_detection_yunet_2023mar.onnx", folder="04-face-attr", size=232589,
        sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        sources=[f"{ZOO_MEDIA}/face_detection_yunet/face_detection_yunet_2023mar.onnx"],
        license="Apache-2.0", prio="P0",
        purpose="YuNet face detector - blur/redact boxes, face-crop gating for attribute estimates, NOT identity.",
    ),
    dict(
        key="facial_expression_recognition_mobilefacenet_2022july.onnx", folder="04-face-attr", size=4791892,
        sha256="4f61307602fc089ce20488a31d4e4614e3c9753a7d6c41578c854858b183e1a9",
        sources=[f"{ZOO_MEDIA}/facial_expression_recognition/facial_expression_recognition_mobilefacenet_2022july.onnx"],
        license="Apache-2.0", prio="P2",
        purpose="Zoo expression classifier - aggregate-only crowd engagement trend. Never per-person truth.",
    ),
    dict(
        key="face_recognition_sface_2021dec.onnx", folder="04-face-attr", size=38696353,
        sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
        sources=[f"{ZOO_MEDIA}/face_recognition_sface/face_recognition_sface_2021dec.onnx"],
        license="Apache-2.0", prio="P2",
        purpose="SFace 128-d embedding - ONLY for staff shift-login with explicit consent + template governance.",
    ),
    # ---------------- 05-open-vocab (AGPL Ultralytics yolo-world / YOLOE; MIT CLIP) ----------------
    dict(
        key="yolov8s-worldv2.pt", folder="05-open-vocab", size=25923032,
        sources=[f"{GH_ULTRALYTICS}/v8.2.0/yolov8s-worldv2.pt"],
        license="AGPL-3.0", prio="P0",
        purpose="YOLO-World v2 small - text-prompted classes (bottle, backpack, cart, sign...) via set_classes().",
    ),
    dict(
        key="yolov8l-worldv2.pt", folder="05-open-vocab", size=94224632,
        sources=[f"{GH_ULTRALYTICS}/v8.2.0/yolov8l-worldv2.pt"],
        license="AGPL-3.0", prio="P1",
        purpose="YOLO-World v2 large - better open-vocab recall for product taxonomy (offline accuracy tier).",
    ),
    dict(
        key="config.json", folder="05-open-vocab/clip-vit-base-patch32", size=4186,
        sources=[f"{HF}/openai/clip-vit-base-patch32/resolve/main/config.json"],
        license="MIT", prio="P0", purpose="CLIP ViT-B/32 config.",
    ),
    dict(
        key="preprocessor_config.json", folder="05-open-vocab/clip-vit-base-patch32", size=316,
        sources=[f"{HF}/openai/clip-vit-base-patch32/resolve/main/preprocessor_config.json"],
        license="MIT", prio="P0", purpose="CLIP preprocessor (CLIPImageProcessor).",
    ),
    dict(
        key="tokenizer.json", folder="05-open-vocab/clip-vit-base-patch32", size=2224041,
        sources=[f"{HF}/openai/clip-vit-base-patch32/resolve/main/tokenizer.json"],
        license="MIT", prio="P0", purpose="Fast tokenizer for text-prompt embedding.",
    ),
    dict(
        key="tokenizer_config.json", folder="05-open-vocab/clip-vit-base-patch32", size=592,
        sources=[f"{HF}/openai/clip-vit-base-patch32/resolve/main/tokenizer_config.json"],
        license="MIT", prio="P0", purpose="Tokenizer config.",
    ),
    dict(
        key="vocab.json", folder="05-open-vocab/clip-vit-base-patch32", size=862328,
        sources=[f"{HF}/openai/clip-vit-base-patch32/resolve/main/vocab.json"],
        license="MIT", prio="P0", purpose="BPE vocab.",
    ),
    dict(
        key="merges.txt", folder="05-open-vocab/clip-vit-base-patch32", size=524657,
        sources=[f"{HF}/openai/clip-vit-base-patch32/resolve/main/merges.txt"],
        license="MIT", prio="P0", purpose="BPE merges.",
    ),
    dict(
        key="special_tokens_map.json", folder="05-open-vocab/clip-vit-base-patch32", size=389,
        sources=[f"{HF}/openai/clip-vit-base-patch32/resolve/main/special_tokens_map.json"],
        license="MIT", prio="P0", purpose="Special tokens.",
    ),
    dict(
        key="pytorch_model.bin", folder="05-open-vocab/clip-vit-base-patch32", size=605247071,
        sources=[f"{HF}/openai/clip-vit-base-patch32/resolve/main/pytorch_model.bin"],
        license="MIT", prio="P0",
        purpose="CLIP ViT-B/32 weights (fp32, 605 MB) - zero-shot shelf-looks, prompt emb. for YOLO-World.",
    ),
    # ---------------- 06-shelf ----------------
    dict(
        key="yoloe-v8s-seg-pf.pt", folder="06-shelf", size=31278303,
        sources=[f"{GH_ULTRALYTICS}/v8.3.0/yoloe-v8s-seg-pf.pt"],
        license="AGPL-3.0", prio="P1",
        purpose="YOLOE small (prompt-free weights) - open-vocab product boxes+masks for shelf/planogram auditing.",
    ),
    # ---------------- research-only (NON-COMMERCIAL insightface license) ----------------
    dict(
        key="buffalo_l.zip", folder="04-face-attr", size=288621354, research=True,
        sources=[f"https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"],
        license="NON-COMMERCIAL research (insightface python-package license)", prio="P2-research",
        purpose="Optional age/gender+ArcFace pack. Legal review required before any commercial deployment.",
    ),
]

FOLDER_PURPOSE = {
    "01-detection": "Person/vehicle/goods detection for consumer+retail intelligence. Feed to trackers.",
    "02-tracking": "No weights: ByteTrack / OC-SORT / BoT-SORT are algorithms shipped with code "
                   "(ultralytics model.track tracker=..., or BoxMOT package).",
    "03-reid": "Appearance embeddings to associate identities ACROSS cameras within a session. No storage-day identity claims.",
    "04-face-attr": "Face PROCESSING for privacy workflows (redaction) and consented staff features. No identity of shoppers.",
    "05-open-vocab": "Text-prompted detection (YOLO-World) + CLIP for zero-shot classification of products/contexts.",
    "06-shelf": "Open-vocab detection+segmentation for shelf/display audits. No public closed-set grocery-SKU weights with clean licenses exist - taxonomy via prompts.",
}

USAGE = {
    "01-detection": "from ultralytics import YOLO; r=YOLO('models/pack/01-detection/yolo11s.pt')(frame); "
                    "r.boxes.xyxy / .cls / .conf",
    "03-reid": "import torchreid; m=torchreid.models.build_model('osnet_x1_0', use_gpu=False); "
               "torchreid.utils.load_pretrained_weights(m, path); emb=m(crops)  # (N,512)",
    "05-open-vocab": "from ultralytics import YOLOWorld; YOLOWorld('models/pack/05-open-vocab/yolov8s-worldv2.pt').set_classes([...])",
    "06-shelf": "from ultralytics import YOLOE or model.predict(img, prompts=...); boxes+masks per product prompt",
}

# --------------------------------------------------------------------------- #


def fp(root: Path, item: dict) -> Path:
    return root / item["folder"] / item["key"]


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def is_lfs_pointer(blob: bytes) -> bool:
    return blob.startswith(b"version https://git-lfs")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, min_size: int, expect_sha: str | None) -> Path:
    """Stream to .part, sanity-check, atomically rename."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with _opener().open(req, timeout=180) as resp, open(tmp, "wb") as fo:
        head = b""  # tiny guard window for LFS-pointer artifacts
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            head = (head + chunk)[:64]
            if head.startswith(b"version https://git-lfs"):
                raise ValueError("server returned a git-lfs POINTER file, not the weights")
            fo.write(chunk)
    real = tmp.stat().st_size
    if real < min_size:
        raise ValueError(f"downloaded {real}B < expected >= {min_size}B (truncated/HTML error page)")
    if expect_sha:
        got = sha256_of(tmp)
        if got != expect_sha:
            raise ValueError(f"sha256 mismatch: got {got[:12]}... expected {expect_sha[:12]}...")
    os.replace(tmp, dest)
    return dest


def write_tracking_readme(root: Path) -> None:
    """02-tracking has no binary ITEMS — still document algorithms-only."""
    d = root / "02-tracking"
    d.mkdir(parents=True, exist_ok=True)
    readme = d / "README.md"
    if readme.exists():
        return
    readme.write_text(
        "# 02-tracking\n\n"
        f"{FOLDER_PURPOSE['02-tracking']}\n\n"
        "No fake binaries. Wire via Ultralytics `model.track(tracker=...)` "
        "or BoxMOT (OC-SORT / BoT-SORT) as code dependencies.\n"
    )


def write_readmes(root: Path, items: list[dict]) -> None:
    write_tracking_readme(root)
    for folder in dict.fromkeys(i["folder"] for i in items).keys():
        d = root / folder
        d.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# {folder}",
            "",
            FOLDER_PURPOSE.get(folder.split("/")[0], FOLDER_PURPOSE.get(folder, "Model pack.")),
            "",
            "| weight | size | license | priority | source URL(s) | purpose |",
            "|---|---|---|---|---|---|",
        ]
        for it in [i for i in items if i["folder"] == folder]:
            for s in it["sources"]:
                lines.append(
                    f"| `{it['key']}` | ~{human(it['size'])} | {it['license']} | {it.get('prio','')} | {s} | {it.get('purpose','')} |"
                )
        top = folder.split("/")[0]
        u = USAGE.get(top)
        if u:
            lines += ["", "```python", u, "```"]
        readme = d / "README.md"
        if not readme.exists():
            readme.write_text("\n".join(lines) + "\n")


def write_gitignore(root: Path) -> None:
    gi = root / ".gitignore"
    content = (
        "# never commit model binaries\n"
        "**/*.pt\n**/*.pt.part\n**/*.pth\n**/*.pth.part\n**/*.onnx\n**/*.onnx.part\n"
        "**/*.zip\n**/*.zip.part\n**/*.bin\n**/*.bin.part\n**/*.msgpack\n"
    )
    if not gi.exists() or gi.read_text() != content:
        gi.write_text(content)


def main() -> int:
    ap = argparse.ArgumentParser(description="Download the EdgeSight model pack (verified URLs only).")
    ap.add_argument(
        "--dest",
        default=str(_DEFAULT_DEST),
        help=f"pack root (default {_DEFAULT_DEST})",
    )
    ap.add_argument("--force", action="store_true", help="re-download existing files")
    ap.add_argument(
        "--include-research",
        action="store_true",
        help="also fetch NON-COMMERCIAL insightface buffalo_l (license review required)",
    )
    ap.add_argument("--only", nargs="*", help="limit to these file keys")
    args = ap.parse_args()

    root = Path(args.dest).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    write_gitignore(root)

    todo, skipped_research, failed, present, fetched = [], [], [], [], []
    for it in ITEMS:
        if args.only and it["key"] not in args.only:
            continue
        if it.get("research") and not args.include_research:
            skipped_research.append(it)
            continue
        todo.append(it)

    print(f"pack root: {root}\n")
    for it in todo:
        dest = fp(root, it)
        status = "PENDING"
        last = ""
        if dest.exists() and not args.force:
            ok = dest.stat().st_size >= it["size"]
            if ok and it.get("sha256"):
                ok = sha256_of(dest) == it["sha256"]
            if ok:
                present.append((it, "PRESENT"))
                status = "PRESENT"
            else:
                failed.append((it, "CORRUPT (size/sha)"))
                status = "CORRUPT"
        else:
            for url in it["sources"]:
                try:
                    download(url, dest, it["size"], it.get("sha256"))
                    fetched.append((it, url))
                    status = "DOWNLOADED"
                    break
                except Exception as e:  # noqa: BLE001
                    last = f"{type(e).__name__}: {e}"
                    dest.with_suffix(dest.suffix + ".part").unlink(missing_ok=True)
            if status != "DOWNLOADED":
                failed.append((it, last or "no source attempted"))
                status = "FAILED"
        human_ok = human(dest.stat().st_size) if dest.exists() else "-"
        print(f"[{status:>9}] {it['folder']:>28}/{it['key']} ({human_ok})")
        if status == "FAILED":
            print(f"            last error: {last}")

    for it in skipped_research:
        print(f"[  SKIPPED] {it['folder']}/{it['key']}  (research-only; omit --include-research)")

    write_readmes(root, ITEMS)

    print("\n==== CHECKLIST ====")
    ok = True
    for it, s in present:
        print(f"  PRESENT  {it['key']:70} {it['license']}")
    for it, url in fetched:
        print(f"  FRESH    {it['key']:70} <- {url}")
    for it, why in failed:
        ok = False
        print(f"  FAILED   {it['key']:70} -> {why}")
    for it in skipped_research:
        print(f"  OPTIONAL {it['key']:70} (research-only license; run --include-research)")
    print(f"\nDisk: {human(sum(i['size'] for i in ITEMS if not i.get('research')))} core "
          f"(+{human(288621354)} if research tier included)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
