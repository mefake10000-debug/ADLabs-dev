# RF-DETR integration (Roboflow SOTA object detection)

**Status:** selectable Apache-2.0 SOTA / AGPL-swap path. **YOLO26n stays the default fast path.**

## Research summary (2026-10)

| Item | Value |
|------|--------|
| Model | **RF-DETR** (Roboflow) — real-time DETR + DINOv2 backbone |
| Package | `rfdetr` on PyPI (`pip install 'rfdetr>=1.3,<2'`, Python ≥ 3.10) |
| License | **Apache-2.0** for code + COCO N/S/M/L weights |
| Prefer | **RFDETRNano** / **RFDETRSmall** (disk + latency) |
| Skip | XL / 2XL — **PML 1.0 Plus** (`rfdetr[plus]`), not free |
| Why RF-DETR | Current Roboflow SOTA OD; N = 48.4 COCO AP⁵⁰:⁹⁵ @ 2.3 ms T4 TRT; S = 53.0 @ 3.5 ms |
| Alternatives considered | D-FINE / LW-DETR also Apache — RF-DETR preferred per model-stack policy + survey |

Upstream: [github.com/roboflow/rf-detr](https://github.com/roboflow/rf-detr) · [rfdetr.roboflow.com](https://rfdetr.roboflow.com/latest/learn/run/detection/)

### Weight IDs

| Variant | Class | Published filename | GCS source |
|---------|-------|--------------------|------------|
| Nano | `RFDETRNano` | `rf-detr-nano.pth` | `https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth` |
| Small | `RFDETRSmall` | `rf-detr-small.pth` | `https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth` |

Cache dir: `RF_HOME` (canonical) or `ROBOFLOW_HOME` → default `~/.roboflow/models`. Compose sets `RF_HOME=/app/models/pack/01-detection/rfdetr`.

### Device notes

| Device | Notes |
|--------|--------|
| **CUDA** | Best path; optional `optimize_for_inference()` / inductor |
| **MPS** (Apple) | Works via torch; prefer native edge over Docker CPU |
| **CPU** | Supported but heavy vs YOLO26n — keep `EDGE_PERF_MODE=fast` + YOLO for Docker Mac ARM demos |

## Env flags

| Flag | Values | Default |
|------|--------|---------|
| `DETECTOR_BACKEND` | `yolo26` \| `rfdetr` | `yolo26` when `EDGE_PERF_MODE=fast`; **`rfdetr` when `quality`** |
| `RFDETR_VARIANT` | `nano` \| `small` | `nano` |
| `RFDETR_WEIGHTS` | path or bare filename | pack path if present, else published bare name |
| `RF_HOME` | cache dir | Compose: `/app/models/pack/01-detection/rfdetr` |
| `EDGE_PERF_MODE` | `fast` \| `quality` | `fast` |
| `EDGESIGHT_DETECT_MODEL` | YOLO path | YOLO only (ignored by RF-DETR path) |
| `OVERLAY_BOX_STYLE` | `parallel` \| `aabb` | peer overlay — **orthogonal**; boxes still xyxy |

## How to switch

```bash
# Fast path (default) — YOLO26n
EDGE_PERF_MODE=fast DETECTOR_BACKEND=yolo26 docker compose up -d edge-analyzer

# SOTA / Apache path — RF-DETR Nano
pip install 'rfdetr>=1.3,<2'   # once, on edge host or quality image
python3 scripts/download_pack_models_phase2.py --download --only rfdetr-nano

EDGE_PERF_MODE=quality DETECTOR_BACKEND=rfdetr RFDETR_VARIANT=nano \
  docker compose up -d edge-analyzer

# Or: quality alone defaults DETECTOR_BACKEND→rfdetr
EDGE_PERF_MODE=quality docker compose up -d edge-analyzer

# Force YOLO even in quality
EDGE_PERF_MODE=quality DETECTOR_BACKEND=yolo26 docker compose up -d edge-analyzer
```

## Pipeline wiring

1. `resolve_performance()` → `detector_backend` / `rfdetr_variant` / `rfdetr_weights`
2. `PersonDetector(backend=…)` loads YOLO **or** `RFDETRNano`/`RFDETRSmall`
3. `detect()` always returns `{bbox: [x1,y1,x2,y2], confidence, class_id}` (COCO person = 0)
4. `SimpleByteTracker` + zone/tripwire analytics unchanged
5. Overlay (AABB or parallel) draws whatever xyxy boxes come out
6. `ModelRegistry` kind `rfdetr` mirrors the ultralytics load pattern
7. `GET /api/v1/models/stack` → `rfdetr` row: **LIVE** when selected+loaded, else **PACKED** / **OFF**

## Install / verify (no full Docker rebuild required)

```bash
# Host / venv
pip install 'rfdetr>=1.3,<2'
python3 -c "from rfdetr import RFDETRNano; print('ok', RFDETRNano)"
python3 -c "from src.perception.detector_backend import resolve_detector_backend; \
  import os; os.environ['EDGE_PERF_MODE']='quality'; print(resolve_detector_backend())"
python3 scripts/download_pack_models_phase2.py --only rfdetr-nano   # dry-run
# Optional fetch (disk-gated; nano ~350 MB — skip if disk tight; demos stay on YOLO26n):
python3 scripts/download_pack_models_phase2.py --download --only rfdetr-nano --min-free-gb 1

# Stack API (with API up)
curl -s localhost:8000/api/v1/models/stack | python3 -m json.tool | head
```

Compose documents the same one-liner on `edge-analyzer` (weights stay out of the image).

`rfdetr` is **commented optional** in `requirements-edge.txt` so the default Docker CPU image stays YOLO-lean. Bake it into a quality image only when needed.

## Policy

See `docs/model-stack-policy.md`. SKU-110K and LocateAnything-3B remain SKIP / FUTURE — not part of this path.
