"""Downloads every model EdgeSight depends on, into ./models/.

Run once after cloning:

    python scripts/download_models.py

The weights are large (~190MB total) and are git-ignored, so they are fetched rather
than committed. Re-running is cheap: files that already exist and match the expected
size are skipped.
"""
import os
import sys
import hashlib
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(ROOT, "models")
ONNX_DIR = os.path.join(MODELS_DIR, "onnx")

ULTRALYTICS_BASE = "https://github.com/ultralytics/assets/releases/download/v8.4.0"

# (filename, url, expected_min_bytes)
ULTRALYTICS_MODELS = [
    # Production person detector (docs/model-benchmark.md)
    ("yolo26s.pt", f"{ULTRALYTICS_BASE}/yolo26s.pt", 8_000_000),
    ("yolo26m.pt", f"{ULTRALYTICS_BASE}/yolo26m.pt", 40_000_000),
    ("yolo26m-pose.pt", f"{ULTRALYTICS_BASE}/yolo26m-pose.pt", 40_000_000),
    ("yolo26m-seg.pt", f"{ULTRALYTICS_BASE}/yolo26m-seg.pt", 40_000_000),
    ("yolov8s-worldv2.pt", f"{ULTRALYTICS_BASE}/yolov8s-worldv2.pt", 20_000_000),
]

ONNX_MODELS = [
    (
        "onnx/face_detection_yunet_2023mar.onnx",
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx",
        200_000,
    ),
    (
        "onnx/age_gender_vit.onnx",
        "https://huggingface.co/onnx-community/age-gender-prediction-ONNX/"
        "resolve/main/onnx/model.onnx",
        100_000_000,
    ),
]

# YOLO-World encodes the class names at runtime with CLIP, so the CLIP text encoder
# is a required runtime dependency for the open-vocabulary product model. Ultralytics
# looks for it under `<project>/weights/clip/`.
CLIP_DIR = os.path.join(ROOT, "weights", "clip")
CLIP_MODELS = [
    (
        "ViT-B-32.pt",
        "https://openaipublic.azureedge.net/clip/models/"
        "40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af/ViT-B-32.pt",
        300_000_000,
        "40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af",
    ),
]


def _download(url: str, dest: str, label: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    print(f"  downloading {label} ...", flush=True)
    with urllib.request.urlopen(url, timeout=120) as resp, open(tmp, "wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        written = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
            written += len(chunk)
            if total:
                pct = written / total * 100.0
                print(f"\r    {written / 1e6:7.1f}MB / {total / 1e6:.1f}MB ({pct:5.1f}%)", end="", flush=True)
    print()
    os.replace(tmp, dest)
    return os.path.getsize(dest)


def _quantize_demographics() -> str:
    """Builds the INT8 copy of the demographic model.

    The demographic network is the single most expensive step in the enrichment tier
    (~0.5s/face in FP32 on this Mac's CPU). Dynamic INT8 quantization cuts that to
    ~0.28s/face and shrinks the checkpoint from ~345MB to ~87MB, with predictions
    that stay within ~0.5 years of the FP32 model on the sample footage.

    This is a build step, not a runtime one, so `onnx` is only needed here.
    """
    src = os.path.join(ONNX_DIR, "age_gender_vit.onnx")
    dest = os.path.join(ONNX_DIR, "age_gender_vit_int8.onnx")
    if not os.path.exists(src):
        return "skipped (FP32 source missing)"
    if os.path.exists(dest):
        return f"present ({os.path.getsize(dest) / 1e6:.1f}MB)"
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError:
        return "skipped (pip install onnx to enable)"
    try:
        quantize_dynamic(
            src, dest,
            weight_type=QuantType.QInt8,
            extra_options={"MatMulConstBOnly": True},
        )
    except Exception as e:
        return f"FAILED ({e})"
    return f"built ({os.path.getsize(dest) / 1e6:.1f}MB)"


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    failures = []

    print("Ultralytics checkpoints:")
    for name, url, min_bytes in ULTRALYTICS_MODELS:
        dest = os.path.join(MODELS_DIR, name)
        if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
            print(f"  {name}: present ({os.path.getsize(dest) / 1e6:.1f}MB)")
            continue
        try:
            size = _download(url, dest, name)
            print(f"  {name}: downloaded ({size / 1e6:.1f}MB)")
        except Exception as e:
            print(f"  {name}: FAILED ({e})")
            failures.append(name)

    print("ONNX models:")
    for rel, url, min_bytes in ONNX_MODELS:
        dest = os.path.join(MODELS_DIR, rel)
        if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
            print(f"  {rel}: present ({os.path.getsize(dest) / 1e6:.1f}MB)")
            continue
        try:
            size = _download(url, dest, rel)
            print(f"  {rel}: downloaded ({size / 1e6:.1f}MB)")
        except Exception as e:
            print(f"  {rel}: FAILED ({e})")
            failures.append(rel)

    print("INT8 quantization:")
    status = _quantize_demographics()
    print(f"  age_gender_vit_int8.onnx: {status}")
    if status.startswith("FAILED"):
        failures.append("age_gender_vit_int8.onnx")

    print("CLIP text encoder (YOLO-World class names):")
    for name, url, min_bytes, sha256 in CLIP_MODELS:
        dest = os.path.join(CLIP_DIR, name)
        if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
            print(f"  {name}: present ({os.path.getsize(dest) / 1e6:.1f}MB)")
            continue
        try:
            size = _download(url, dest, name)
            digest = hashlib.sha256(open(dest, "rb").read()).hexdigest()
            if digest != sha256:
                print(f"  {name}: CHECKSUM MISMATCH (got {digest})")
                failures.append(name)
                continue
            print(f"  {name}: downloaded ({size / 1e6:.1f}MB, checksum verified)")
        except Exception as e:
            print(f"  {name}: FAILED ({e})")
            failures.append(name)

    if failures:
        print(f"\nFAILED: {', '.join(failures)}")
        return 1
    print("\nAll models present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
