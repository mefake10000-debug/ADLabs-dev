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
| `imgsz` | 416 | 640 |
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

| Cameras | Expected infer FPS (per cam, rough) |
|---------|--------------------------------------|
| 1 | ~10–15+ |
| 2 | ~5–10 each (shared CPU) |
| 3+ | often below demo target — use `EDGE_MAX_CAMERAS=1` or `2` |

Portal `/api/v1/live` reports **measured** `infer_fps` / `decode_fps` / `perf_mode`
from live snapshots — do not trust hardcoded health numbers.

## Native macOS MPS (optional)

Compose stays CPU for a reproducible demo. For higher FPS without Docker GPU:

```bash
# Host Python with torch MPS (outside Compose)
EDGE_PERF_MODE=fast python -m src.main
```

MPS accelerates the person detector; enrichment still prefers CPU when the fast
tier owns MPS (thread-safety). Do **not** point Compose at host MPS — the
container cannot see it.

## Verify

```bash
curl -s http://localhost:8000/api/v1/live | python3 -m json.tool | head -40
# Look for infer_fps, decode_fps, models.perf_mode, models.person_detector
docker logs adlabs-edge-analyzer 2>&1 | grep -E 'Performance mode|Inference FPS'
```
