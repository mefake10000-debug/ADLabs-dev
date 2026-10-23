# Live overlay: NVIDIA parallel / pallet boxes

## What changed

Person (+ store-object) overlays on the annotated MJPEG stream default to
**`nvidia`** — a LocateAnything Parallel Box *look-alike* drawn with OpenCV /
Ultralytics boxes (visual only). **Do not download LocateAnything-3B** (NVIDIA NC).

Each person box:

1. **Body parallelogram** — AABB sheared by track heading (opposite sides stay parallel).
2. **Inset parallel rail** — inner pallet frame.
3. **Corner caps** — short L-brackets at each corner (Metropolis / NVIDIA cue).
4. **Ground footprint** — small isometric parallelogram under the feet.
5. **Label bar** — `person ID:N` (+ dwell seconds when the track peer fills `dwell_s`).

Store objects (COCO retail classes from the same Ultralytics pass, plus YOLOE /
YOLO-World open-vocab when enrichment is on) use the same pallet frame with their
**class name** on the label bar. People are always drawn on top (person priority).

Zones / tripwires / queues keep the same geometry.

## Config

| Flag | Values | Default |
|------|--------|---------|
| `OVERLAY_BOX_STYLE` | `nvidia` \| `parallel` \| `pallet` \| `aabb` | `nvidia` |
| `DETECTOR_BACKEND` | `yolo26` \| `yolo11` \| `rfdetr` | `yolo26` (Ultralytics) |

Aliases: `parallel` and `pallet` resolve to `nvidia`.

Compose (`edge-analyzer`):

```yaml
- OVERLAY_BOX_STYLE=${OVERLAY_BOX_STYLE:-nvidia}
- DETECTOR_BACKEND=${DETECTOR_BACKEND:-yolo26}
- EDGE_PERF_MODE=${EDGE_PERF_MODE:-balanced}
```

Restore classic rectangles:

```bash
OVERLAY_BOX_STYLE=aabb docker compose up -d edge-analyzer
```

## Label rules

| Source | Label text |
|--------|------------|
| Tracked person | `person ID:<id>` (+ `Ns` dwell, `STAFF`, `(still)`) |
| COCO store object | YOLO `names[class_id]` (handbag, bottle, …) |
| Open-vocab (YOLOE / World) | vocabulary / mapped class name |

## API (read-only)

- `GET /api/v1/overlay` — current style + options (no write path; restart edge to change).
- Live snapshot / device health also report `overlay_box_style` when the edge is writing snapshots.

## Check locally

With Docker up (`EDGE_PERF_MODE=balanced`, `DETECTOR_BACKEND=yolo26`):

- MJPEG: `http://localhost:8000/api/v1/stream/cam_entrance_01`
- Overlay flags: `http://localhost:8000/api/v1/overlay`

## Shear math (body parallelogram)

```
speed = |velocity|  (from Track, ~last 5 history points)

if speed >= 8 px/s:
  shear_x = clamp(unit_heading_x * 0.35 * bbox_width, ±0.45 * width)
else if recent history moved ≥ 4 px:
  shear_x from history direction
else:
  shear_x = 0.18 * width   # mild isometric lean when still
```
