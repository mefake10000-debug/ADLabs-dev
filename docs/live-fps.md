# Live annotated video FPS (fast vs quality)

## Problem

Docker on Mac ARM runs the edge analyzer **CPU-only**. With enrichment on
(pose, YuNet, demographics, YOLO-World/CLIP) and `yolo26s` on two cameras,
measured **infer FPS was ~0.3–1** while decode stayed ~10–13. The portal MJPEG
only updates when annotated JPEGs are written, so the live wall looked frozen.

## Default: fast tier

`performance.mode: fast` (and compose `EDGE_PERF_MODE=fast`) means:

| Knob | Fast | Quality |
|------|------|---------|
| Detector | `models/yolo26n.pt` | `models/yolo26s.pt` |
| `imgsz` | 320 | 640 |
| `infer_every_n` | 2 | 1 |
| Enrichment (pose/face/CLIP/world) | **off** | on |
| Soft ReID | off | opt-in (`models.reid.enabled`) |
| `max_cameras` | **1** (demo default) | null = all yaml cams |

Display stream is separate from analytics cadence: MJPEG JPEGs refresh every
`display_every_n` decoded frames using the **last** tracks, so the portal stays
smooth even when inference skips frames. Dual-cam Docker CPU still works if you
set `performance.max_cameras: null` or `EDGE_MAX_CAMERAS=` empty — expect ~0.5
infer FPS.

## How to switch

```bash
# Fast (demo default)
EDGE_PERF_MODE=fast docker compose up -d edge-analyzer

# Quality (enrichment) — expect ~0.3–2 infer FPS in Docker CPU on this Mac
EDGE_PERF_MODE=quality docker compose up -d edge-analyzer

# Max FPS for a single-cam demo
EDGE_PERF_MODE=fast EDGE_MAX_CAMERAS=1 docker compose up -d edge-analyzer

# Pack nano alternative
EDGESIGHT_DETECT_MODEL=models/pack/01-detection/yolo11n.pt \
  EDGE_PERF_MODE=fast docker compose up -d edge-analyzer
```

Or edit `configs/pipeline.yaml` → `performance.mode` / `models.enabled`.

## Multi-cam tradeoffs

The main loop still runs cameras **sequentially** on one thread. Rough budget on
Docker CPU (fast tier, M-series host):

Measured on this Mac (2026-10-23), honest `/api/v1/live` + edge logs:

| Setup | Infer FPS | Display FPS |
|-------|-----------|-------------|
| **Before** Docker + enrichment (pose/YuNet/World) 2 cams | **~0.3–1** | boxes stalled |
| **After** Docker CPU fast, 1 cam | **~1–3** (log) | MJPEG follows JPEG writes |
| **After** native macOS MPS fast, 1–2 cams | **~6–8** | **~12–14** (last-track overlay) |
| quality / enrichment on Docker CPU | **~0.3–2** | tracks infer |

Portal `/api/v1/live` reports **measured** `infer_fps` / `display_fps` / `decode_fps` /
`perf_mode` — do not trust hardcoded health numbers. Boxes update at `infer_fps`;
the video wall can feel faster when `display_fps` is higher.

## Native macOS MPS (optional)

Compose stays CPU for a reproducible demo. For demo-target FPS on Apple Silicon:

```bash
# Stop Compose edge first (host + Docker fight over data/storage/live/*.json)
docker compose stop edge-analyzer
EDGE_PERF_MODE=fast EDGE_MAX_CAMERAS=1 \
  TELEMETRY_LOCAL_ENDPOINT=http://localhost:8000/api/v1/telemetry \
  .venv/bin/python -m src.main
```

MPS accelerates the person detector; enrichment still prefers CPU when the fast
tier owns MPS (thread-safety). Do **not** run host edge and Compose edge together.

## Verify

```bash
curl -s http://localhost:8000/api/v1/live | python3 -m json.tool | head -40
# Look for infer_fps, display_fps, decode_fps, models.perf_mode, models.person_detector
docker logs adlabs-edge-analyzer 2>&1 | grep -E 'Performance mode|Inference FPS'
```

## CLIP / autoinstall

Compose sets `YOLO_AUTOINSTALL=false` so Ultralytics cannot retry `pip install git+CLIP`
at runtime. Bake `openai-clip` via `requirements-edge.txt` and rebuild `edge-analyzer`.
