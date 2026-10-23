# Calibration Guide — Floor, Queue & Staff zones

Applies to both cameras (`cam_entrance_01`, `cam_checkout_01`) and any new camera you add to `configs/cameras.yaml`.

## Zone types and what they drive (verified from source)

| Zone type | Producer | Fields it feeds | Key config defaults (verified) |
|---|---|---|---|
| `queue` | `QueueAnalyzer` | `queues[].queue_length`, `avg_wait_seconds`, `alert_active`; store-level `queue_length`, `avg_queue_wait_seconds` | `max_comfortable_queue: 4`, `congestion_threshold_seconds: 120.0` |
| `staff` | `Zone(type=staff)` + sticky tagging | `staff_zones[].tagged_ids`; tags session IDs into `staff_now` (excluded from customers after 10 s) | `staff_min_seconds_in_zone: 10.0` |
| `dwell` (default) | `Zone` | `zones[].occupancy`, `avg_dwell_seconds`; store `avg_dwell_seconds` | `zone_exit_grace_seconds: 3.0` (a 3 s tracking gap doesn't reset dwell) |

All defaults were read from `src/main.py` and `configs/pipeline.yaml` on the running repo.

## Current verified zones

**cam_checkout_01** — "Checkout Floor" (fps_target 15 after today's fix):
- Queue zone `queue_zone_checkout_01` — "Checkout Queue": polygon (200,400) → (600,400) → (600,700) → (200,700), type `queue`.
- Staff zone `staff_zone_checkout_01` — "Staff Counter": polygon (50,100) → (280,100) → (280,350) → (50,350).

**cam_entrance_01** — see `calibration-entrance.md`.

## How to draw good zones

**Queue zones**
1. Polygon must cover the *standing line area*, not aisle traffic — draw it tight around where people actually wait.
2. A person counts in the queue when their foot-point is inside the polygon and they stay (stationary policy `tag` keeps standing people counted, verified `stationary_policy: tag`).
3. Waiting seconds accumulate as `avg_wait_seconds`; the alert fires on comfort threshold (`max_comfortable_queue`, `congestion_threshold_seconds`).
4. Ages people leave: `avg_queue_wait_seconds` resets from exits after the 3 s grace — so stair bumps don't spike the number.

**Staff zones**
1. Draw over counters/desks where staff *stand still for ≥10 seconds* — that's the tagging threshold before someone is reclassified as staff.
2. Anyone tagged staff is removed from `people_now` (customer occupancy) immediately, so store occupancy stays customer-only.
3. Keep staff polygons away from customer paths; a customer browsing 10 s at the counter becomes "staff" in the KPI.

**Dwell zones (floor traction)**
1. Any polygon not typed `queue`/`staff` is a dwell zone: reports occupancy + `avg_dwell_seconds` per zone → drives Floor traction cards and route heatmap context.
2. Overlap cautiously: a foot-point can sit in two zones, and store occupancy sums cameras (double-counting overlap documented in `occupancy_note`).

## Applying changes

- Studio: `:3000/dashboard/live?panel=calib` → select camera → draw → Save (verified: hot reload ~3 s, no restart).
- REST: `POST /api/v1/config/cameras` with the full camera list (works through the portal proxy too).
- Verify after save: the snapshot at `/api/v1/live/snapshot?camera_id=<id>` shows your `zones[]`/`queues[]` within one refresh.

## Honest data notes for this camera (verified)

- `checkout_sample.mp4` measured **0 person detections** at the sampled positions (5 s, 15 s of a 20 s 15 fps clip) with the production detector settings — so checkout numbers currently stay at true zero. When better footage is provided (people ≥ ~95 px tall in frame, 720p+, ≥15 fps), the same calibration produces nonzero queue/staff data automatically. We do not fake numbers for missing footage (badge: PARTIAL with empty-state copy).
- Footage requirement for accuracy (any camera): people well-lit, torso-height ≥ ~95 px at the detection resolution, static camera, no aggressive motion blur at 15 fps.
