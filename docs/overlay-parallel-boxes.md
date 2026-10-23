# Live overlay: parallel boxes

## What changed

Person overlays on the annotated MJPEG stream default to **parallel boxes** instead of axis-aligned YOLO rectangles:

1. **Body parallelogram** — AABB sheared by track heading so opposite sides stay parallel (cheap oriented look).
2. **Ground footprint** — small isometric parallelogram under the feet (occupancy cue on retail CCTV).
3. **Track ID** — thin label at the top-left of the parallelogram; faded trajectory trail unchanged in spirit.

Zones / tripwires / queues keep the same geometry.

This is a **visual-only** change. Detection, tracking, and KPIs are untouched. LocateAnything / open-vocab download stays **FUTURE** (NVIDIA NC).

## How shear is computed

```
speed = |velocity|  (from Track, ~last 5 history points)

if speed >= 8 px/s:
  shear_x = clamp(unit_heading_x * 0.35 * bbox_width, ±0.45 * width)
else if recent history moved ≥ 4 px:
  shear_x from history direction
else:
  shear_x = 0.18 * width   # mild isometric lean when still
```

Body quad: bottom edge = AABB feet `(x1,y2)–(x2,y2)`; top edge = same width shifted by `shear_x`. That yields a parallelogram (`cv2.polylines`).

## Config

| Flag | Values | Default |
|------|--------|---------|
| `OVERLAY_BOX_STYLE` | `parallel` \| `aabb` | `parallel` |

Compose (`edge-analyzer`):

```yaml
- OVERLAY_BOX_STYLE=${OVERLAY_BOX_STYLE:-parallel}
```

Restore classic rectangles:

```bash
OVERLAY_BOX_STYLE=aabb docker compose up -d edge-analyzer
```

## API (read-only)

- `GET /api/v1/overlay` — current style + options (no write path; restart edge to change).
- Live snapshot / device health also report `overlay_box_style` when the edge is writing snapshots.

## Check locally

With Docker up (`EDGE_PERF_MODE=fast`):

- MJPEG: `http://localhost:8000/api/v1/stream/cam_entrance_01`
- Overlay flags: `http://localhost:8000/api/v1/overlay`

Portal Live tab (guided flow) embeds the same stream; site tip may be `3fd81eb` — do not revert UX.
