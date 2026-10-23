# Foot tracking + retail CV models (mefake)

People UI defaults to **coordinates / foot marks**, not heavy AABB boxes.
Retail intelligence pack expands with license-clean phase-2 downloads.

## Overlay (`OVERLAY_BOX_STYLE`)

| Value | Behavior |
|-------|----------|
| **`foot`** (default) | Red mark at ground contact + faint ID + trail. No heavy person box. |
| `skeleton` | Thin joint lines (when RTMPose keypoints present) + red foot. |
| `nvidia` | LocateAnything pallet look-alike (inset rails + corner caps). Optional. |
| `parallel` | Sheared parallelogram + footprint (lighter peer option). |
| `aabb` | Classic YOLO rectangles. |

Alias: `pallet` → `nvidia`.

**Scope:** models + overlay = **people vs store objects** only. Queue / staff /
territory / dwell polygons stay **client-owned calibration** (cameras.yaml /
portal calib). Edge draws them as configured; it does **not** auto-mark or rewrite
those zones.

Primary position for tripwire IN/OUT, zone dwell, and trajectories is always
`track.foot_point` (pose ankles when available, else bbox bottom-center).

## Live API

Per-camera live JSON now includes:

```json
"tracks": [
  { "id": 3, "foot": [412.5, 680.0], "dwell_s": 4.2, "bbox": [...], "stationary": false }
],
"overlay_box_style": "foot",
"models": { "pose": true, "rtmpose": true, "overlay_box_style": "foot", ... }
```

`GET /api/v1/overlay` → `{ overlay_box_style, options, default: "foot" }`.

## Models (approved downloads)

Run (disk-gated; default dry-run):

```bash
python3 scripts/download/download_pack_models_phase2.py --download \
  --only rtmpose-t rtmpose-s moondream2-config \
  --min-free-gb 4
```

| Item | License | Role |
|------|---------|------|
| RTMPose-t/s ONNX | Apache-2.0 | Ankle feet, skeleton, fall-candidate |
| YOLO26n/s (Ultralytics) | AGPL pilot OK | Person + COCO; quality may use yolo26s |
| YOLOE / YOLO-World | AGPL pilot | Shelf / open-vocab (quality) |
| CLIP ViT-B/32 | MIT | Shelf/display interest |
| OSNet ReID | — | Session-only when quality |
| Moondream2 config | Apache | Nightly shelf QA stub (full weights opt-in) |

**Skip / gated (unchanged):** LocateAnything-3B (NVIDIA NC), SKU-110K NC, P2PNet academic-only, MiVOLO GATED (no raw age/gender LIVE).

ONNX unpack writes `models/pack/07-pose/rtmpose-t.onnx` and `rtmpose-s.onnx`
(unique names — SDK zips both contain `end2end.onnx`).

## Runtime env

```
OVERLAY_BOX_STYLE=foot          # default
ENABLE_RTMPOSE=1                # load ankles when ONNX present
RTMPOSE_VARIANT=t               # t|s
RTMPOSE_EVERY_N=4               # throttle for Docker CPU
EDGE_PERF_MODE=detect          # demo default: yolo26s, imgsz 640, infer every 2
                                # balanced|fast = nano speed; quality unlocks enrichment
```

Prefer **rtmlib** (`pip install rtmlib`); ORT SimCC fallback if rtmlib missing.

## Models strip

`GET /api/v1/models/stack` → `rtmpose` status **LIVE** when ONNX on disk and
`RTMPOSE_RUNTIME_LOADED=1` (set by edge after successful load). Dashboard
`LiveModelsStrip` shows ON.

## Verify (red foot on stream)

1. `docker compose up -d` with pack mounted (`./models` → `/app/models`).
2. Confirm `models/pack/07-pose/rtmpose-t.onnx` exists.
3. `GET /api/v1/overlay` → `overlay_box_style=foot`.
4. Open MJPEG `/api/v1/stream/<cam_id>` — people show a **red circle at the feet**, faint ID, grey trail; no big cyan boxes.
5. Live JSON `tracks[].foot` near bbox bottom (or ankles when pose ticks).
6. Stack: `rtmpose` run_state ON after edge warm-up.

## Related

- `docs/models/model-stack-policy.md`
- `docs/performance/overlay-parallel-boxes.md` (parallel option retained)
- `scripts/download/download_pack_models_phase2.py`
