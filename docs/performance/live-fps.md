# Live annotated video FPS (detect | balanced | fast | quality)

## Current local Docker measurement (24 Oct 2026)

The active pilot profile is the `fast` preset with YOLO26n at 512 pixels and
`infer_every_n=3`. YOLOE products, OSNet ReID, and RTMPose are loaded on the
separate slow tier (32-frame enrichment cadence; RTMPose every 8 detector
updates). The camera worker is limited to one of two configured cameras. Docker
runs CPU-only PyTorch on the Mac; it does not offload inference from the host.

After recreating only `cloud-dashboard` and `edge-analyzer` to apply the updated
backend and four-core edge ceiling, the live health API was sampled five times
across 60.7 seconds while the restaurant clip was active:

| Measurement | Mean across samples | Observed range |
|---|---:|---:|
| Feed / decode | 13.1 FPS | 9.6–14.0 FPS |
| Person-model inference | 2.2 FPS | 0.2–3.4 FPS |
| Annotated display | 12.8 FPS | 8.0–14.3 FPS |

This is the measured result, not a target guarantee. The requested 15 FPS is not
met with all selected models active; inference is the limiting stage, and the
late display-rate dip shows the feed is not yet stable. The five-sample window is
too small to claim a p95. A longer labeled run is needed before asserting a
precision/recall tradeoff. Current API has no qualifying labeled result, so
accuracy is **Not measured**.

The Docker source picker returns the garage and restaurant clips from the
read-only Desktop footage mount. The active camera at this measurement was
`cam_entrance_01` using
`/app/data/test-footage/restaurant-ch17/20261016124745.mp4`; only one camera is
being processed under the current one-camera FPS budget.

## Problem

Docker on Mac ARM runs the edge analyzer **CPU-only**. With enrichment on
(pose, YuNet, demographics, YOLO-World/CLIP) and `yolo26s` on two cameras,
measured **infer FPS was ~0.3–1** while decode stayed ~10–13. The portal MJPEG
only updates when annotated JPEGs are written, so the live wall looked frozen.

A later “tighten FPS” pass (`infer_every_n=3`, `imgsz=320` as the only demo
default) improved display FPS but **missed people in frame**. Balanced
(`yolo26n` @ 416) still missed people on the client clips. Local demos now
default to **detect**: Ultralytics **yolo26s**, `imgsz=640`, `infer_every_n=2`,
enrichment off. Person confidence stays in **0.20–0.25**. Store objects use a
higher bar and are never ByteTrack people. Overlay default is a clean clipped **AABB** person box; foot trails are optional.
RF-DETR is opt-in (`DETECTOR_BACKEND=rfdetr`) only.

## Presets

`EDGE_PERF_MODE` / `performance.mode`:

| Knob | Fast | Balanced | **Detect (default)** | Quality |
|------|------|----------|----------------------|---------|
| Detector | `yolo26n` | `yolo26n` | **`yolo26s`** (nano if that file is missing) | `yolo26s` |
| `imgsz` | 320 | 416 | **640** | 640 |
| `infer_every_n` | 3 | 2 | **2** | 1 |
| Person conf | yaml 0.25 | yaml 0.25 | **0.22** (clamped 0.20–0.25) | yaml |
| Object conf | 0.45 | 0.45 | **0.45** (labels only) | 0.45 |
| Track start | yaml 0.50 | yaml 0.50 | **0.25** (persons only) | yaml |
| Enrichment | off | off | **off** | on (yaml gates) |
| Backend | yolo26 | yolo26 | **yolo26** | yolo26 unless `DETECTOR_BACKEND=rfdetr` |

Display stream is separate from analytics cadence: MJPEG JPEGs refresh every
`display_every_n` decoded frames using the **last** tracks, so the portal stays
smooth even when inference skips frames. The stream endpoint skips incomplete
JPEGs and identical payloads to avoid torn / glitchy frames.

## How to switch

```bash
# Detect (local demo default — yolo26s @ 640, people not missed)
EDGE_PERF_MODE=detect OVERLAY_BOX_STYLE=aabb docker compose up -d --force-recreate edge-analyzer

# Balanced (lighter nano letterbox)
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

Overlay style (visual only): `OVERLAY_BOX_STYLE=aabb` (default) | `foot` |
`skeleton` | `nvidia` | `parallel`. AABB shows clipped person rectangles with compact IDs;
store-object boxes remain off unless `OVERLAY_SHOW_STORE_OBJECTS=1`. See
`docs/models/foot-tracking-retail-models.md`.

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

The default `edge-analyzer` service is capped at **4 CPU cores** so a pilot
container cannot take every Docker Desktop CPU share. This ceiling does not
improve throughput by itself and can reduce peak FPS if the detector needs more
CPU. `cloud-dashboard` and the optional RTSP simulator are uncapped. No memory
limit is set because this checkout has no measured container peak-memory series.

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
# Look for perf_mode=detect, imgsz=640, infer_every_n=2, person_detector=yolo26s
# person_conf ~0.22, object_conf ~0.45, overlay_box_style=foot
# people_now should move with people visible on the MJPEG
open http://localhost:8000/api/v1/stream/cam_entrance_01
docker logs adlabs-edge-analyzer 2>&1 | grep -E 'Performance mode|Inference FPS'
```

## CLIP / autoinstall

Compose sets `YOLO_AUTOINSTALL=false` so Ultralytics cannot retry `pip install git+CLIP`
at runtime. Bake `openai-clip` via `requirements-edge.txt` and rebuild `edge-analyzer`.
