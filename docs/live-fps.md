# Live annotated video FPS (fast | balanced | quality)

## Problem

Docker on Mac ARM runs the edge analyzer **CPU-only**. With enrichment on
(pose, YuNet, demographics, YOLO-World/CLIP) and `yolo26s` on two cameras,
measured **infer FPS was ~0.3–1** while decode stayed ~10–13. The portal MJPEG
only updates when annotated JPEGs are written, so the live wall looked frozen.

A later “tighten FPS” pass (`infer_every_n=3`, `imgsz=320` as the only demo
default) improved display FPS but **missed people in frame**. Local demos now
default to **balanced**.

## Presets

`EDGE_PERF_MODE` / `performance.mode`:

| Knob | Fast | **Balanced (default)** | Quality |
|------|------|------------------------|---------|
| Detector | `models/yolo26n.pt` | `models/yolo26n.pt` | RF-DETR (or `yolo26s` if `DETECTOR_BACKEND=yolo26`) |
| `imgsz` | 320 | **416** | 640 (YOLO) |
| `infer_every_n` | 3 | **2** | 1 |
| Enrichment (pose/face/CLIP/world) | off | **off** | on (yaml gates) |
| Soft ReID | off | off | opt-in (`models.reid.enabled`) |
| `max_cameras` | **1** (compose) | **1** (compose) | null = all yaml cams |

Display stream is separate from analytics cadence: MJPEG JPEGs refresh every
`display_every_n` decoded frames using the **last** tracks, so the portal stays
smooth even when inference skips frames. The stream endpoint skips incomplete
JPEGs and identical payloads to avoid torn / glitchy frames.

## How to switch

```bash
# Balanced (local demo default — reliable people boxes)
EDGE_PERF_MODE=balanced docker compose up -d edge-analyzer

# Fast (max display FPS; may miss distant / small people)
EDGE_PERF_MODE=fast docker compose up -d edge-analyzer

# Quality (enrichment) — expect ~0.3–2 infer FPS in Docker CPU on this Mac
EDGE_PERF_MODE=quality docker compose up -d edge-analyzer

# Max FPS for a single-cam stress test
EDGE_PERF_MODE=fast EDGE_MAX_CAMERAS=1 docker compose up -d edge-analyzer

# Pack nano alternative
EDGESIGHT_DETECT_MODEL=models/pack/01-detection/yolo11n.pt \
  EDGE_PERF_MODE=balanced docker compose up -d edge-analyzer
```

Or edit `configs/pipeline.yaml` → `performance.mode` / `models.enabled`.

Overlay style (visual only): `OVERLAY_BOX_STYLE=parallel|aabb` — see
`docs/overlay-parallel-boxes.md`.

## Multi-cam tradeoffs

The main loop still runs cameras **sequentially** on one thread. Rough budget on
Docker CPU (balanced tier, M-series host):

| Setup | Infer FPS | Display FPS | People recall |
|-------|-----------|-------------|---------------|
| Docker + enrichment 2 cams | ~0.3–1 | boxes stalled | — |
| Docker CPU **fast**, 1 cam (`n=3`, 320) | ~3–5 | ~9–12 | misses more |
| Docker CPU **balanced**, 1 cam (`n=2`, 416) | ~2–4 | ~7–11 | denser boxes |
| Native macOS MPS balanced, 1–2 cams | ~6–8 | ~12–14 | best demo feel |
| quality / enrichment on Docker CPU | ~0.3–2 | tracks infer | — |

Portal `/api/v1/live` reports **measured** `infer_fps` / `display_fps` / `decode_fps` /
`perf_mode` — do not trust hardcoded health numbers. Boxes update at `infer_fps`;
the video wall can feel faster when `display_fps` is higher.

## Native macOS MPS (optional)

Compose stays CPU for a reproducible demo. For demo-target FPS on Apple Silicon:

```bash
# Stop Compose edge first (host + Docker fight over data/storage/live/*.json)
docker compose stop edge-analyzer
EDGE_PERF_MODE=balanced EDGE_MAX_CAMERAS=1 \
  TELEMETRY_LOCAL_ENDPOINT=http://localhost:8000/api/v1/telemetry \
  .venv/bin/python -m src.main
```

MPS accelerates the person detector; enrichment still prefers CPU when the light
tier owns MPS (thread-safety). Do **not** run host edge and Compose edge together.

## Verify

```bash
curl -s http://localhost:8000/api/v1/live | python3 -m json.tool | head -40
# Look for perf_mode=balanced, imgsz=416, infer_every_n=2, person_detector=yolo26n
# people_now should move with people visible on the MJPEG
open http://localhost:8000/api/v1/stream/cam_entrance_01
docker logs adlabs-edge-analyzer 2>&1 | grep -E 'Performance mode|Inference FPS'
```

## CLIP / autoinstall

Compose sets `YOLO_AUTOINSTALL=false` so Ultralytics cannot retry `pip install git+CLIP`
at runtime. Bake `openai-clip` via `requirements-edge.txt` and rebuild `edge-analyzer`.
