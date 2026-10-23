# Calibration Guide — Entrance Camera (glass view)

Camera: `cam_entrance_01` — "Main Store Floor & Entrance"
Source: `data/sample_videos/entrance_sample.mp4` · fps_target 15 · 1270×720 (current verified config)

## Verified current calibration

- Tripwire `entrance_tripwire`: horizontal sample line (160, 520) → (1110, 520), `in_direction: bottom_to_top` (re-draw if FOV differs).
- Queue zone `queue_zone_1790217226558` — "Checkout Queue" (6-point client polygon; restored after template overwrite).
- Staff zone `staff_zone_1790733394769` — "Staff Area" (5-point client polygon, left-mid floor).

**Client-owned:** queue / staff / dwell polygons are never auto-written. Calibration Studio **Apply entrance template** is an explicit button and sets the entrance tripwire only.

All values above were read directly from `configs/cameras.yaml` on 2026-10-23.

## What the entrance camera produces

| Field | Meaning | Producer |
|---|---|---|
| `people_now` / `per_camera[].occupancy` | Customers physically on the floor right now (matches YOLO overlay IDs) | YOLO person boxes + session-scoped ByteTrack |
| `total_visitors` / `total_exits` | Cumulative tripwire IN / OUT for the session | Tripwire crossings (foot-point across the line) |
| `/api/v1/events` rows | One row per crossing: wire_id, session track_id, direction, timestamp | Durable event persistence |
| Zone dwell / occupancy in entrance zones | Traction aggregates (avg dwell seconds, occupancy counts) | Zone membership + exit grace 3 s |
| `staff_now` | People who stayed ≥10 s inside a staff zone get sticky-tagged; excluded from `people_now` | Staff-zone geometry (`staff_min_seconds_in_zone: 10.0` verified default) |

## How to recalibrate (verified working flows)

1. **Calibration Studio (recommended)**: open `:3000/dashboard/live?panel=calib` (portal route `/dashboard/live/calibrate` → :8000). Draw tripwire/zone polygons, hit Save.
2. **Direct API**: `GET`/`POST /api/v1/config/cameras` (works through the portal proxy at `:3000/api/v1/...` — same origin, no CORS setup).
3. Save behavior (verified by test this session): POST returns `{"status":"success"}`, the yaml is written, and the edge hot-reloads cameras & tripwires within ~3 s — log line: `Configuration file modified on disk. Hot-reloading cameras & tripwires...`. No restart needed.

## Entrance-specific rules

- Draw the tripwire **across the entry direction**, splitting "outside/door" from "inside".
- `in_direction: bottom_to_top` means a foot-point crossing upward (toward the store) counts as IN. If your new footage is oriented differently, flip it in the studio; wrong direction = `total_visitors` recording OUT events as IN.
- Entrance counters get their IN/OUT from **track foot-points** — boxes crossing are not enough, the foot point (~person's bottom center) must cross the line.
- **Keep the line short but complete.** The tripwire only counts crossings through its segment; long lines crossing exam aisles inflate counts.
- `people_now` (occupancy) is **not** derived from the tripwire. Since 2026-10-23 the DB rollup stores active tracks — so glass view, DB rollups, and the dashboard all match (fixed 0-live vs overlay-5 desync source).
- The tracker tags a visitor as **staff sticky** after 10 s inside a drawn staff zone; from then on they leave `people_now` and only appear in `staff_now`. Don't put queue or browsing areas inside staff polygons.

## What is NOT on this camera yet (honest gaps)

- **Stop-rate (glass-view dwell threshold)**: FUTURE — the tracker already computes stationary seconds, but there's no name/dashboard field today. UI copy: "The tracker already computes stationary seconds — we show nothing rather than estimate."
- Face boxes are redaction-only (YuNet). No identity is stored or shown, ever.

## Privacy posture

- Only counts, session-scoped numeric IDs, wire IDs, zone aggregates leave the edge. No images of persons are persisted; annotated JPEGs carry boxes only.
- See `privacy-badge-matrix.md` for the full per-section matrix.
