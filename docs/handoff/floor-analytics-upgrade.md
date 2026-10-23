# Floor Analytics Upgrade — Paths, Zone Sequences, Traction, Shelf Interest

Design contract (extension of `field-map.md`, `live.schema.json`, `calibration-entrance-glass-workflow.md`).
**Status: FUTURE/design until implemented** except where a verified pipe already exists (zone membership, foot-point history, durable event channel, YOLO-World product categories). Session track IDs only — **no cross-day identity, no cross-camera stitching** (that boundary stays with the session-scoped Re-ID gallery work; see privacy matrix).

Grounding facts reused (verified this session):
- Tracker keeps per-track foot-point history `(x, y, t)` and a `track_buffer` retirement window; `history` cap is 60 points today.
- Zones/queues/staff polygons already class per-cam with `active_tracks_in_zone {tid: entered_at}` and `zone_exit_grace_seconds: 3.0`.
- Durable event channel `POST /api/v1/telemetry/events` exists and is extendable (previous workflow doc already added glass/stop events additively).
- YOLO-World product categories already produce real historical rows (`/api/v1/analytics/products`); CLIP weights exist in-pack (05-open-vocab) but are config-gated.

---

## 0) New config (normalized, consistent with glass workflow)

```yaml
cameras:
- id: cam_entrance_01
  normalized: true
  zones:            # existing dwell polygons unchanged (normalized)
  aisles:           # NEW — corridor strips for traction/routes
  - id: aisle_3
    name: Aisle 3
    corridor:
      a: [0.10, 0.90]      # one end center (normalized 0-1)
      b: [0.10, 0.35]      # other end center
      width_frac: 0.045    # strip half-width as fraction of frame min-dim
  shelves:          # NEW — shelf faces for interest/dwell
  - id: shelf_12
    name: Shelf 12
    front_line: [[0.62, 0.70], [0.72, 0.70]]    # where people stand in front of it
    depth_frac: 0.06                             # how far "interest" reaches back from front_line
    category: "handbag"                          # optional operator-known label
    auto_category: true                          # attach YOLO-World label of the nearest detected product box

analytics:
  floor:
    sample_interval_seconds: 0.25          # path sampler cadence (per track)
    min_displacement_frac: 0.003           # dedupe jitter below this motion
    max_points_per_track: 240              # in-memory ring per active track
    rdp_epsilon_frac: 0.005                # polyline compression on retire
    interpolation_max_gap_seconds: 1.5     # beyond this, polyline shows an "uncertain gap"
    route_min_zones: 2                     # route_key formed only when ≥2 distinct zone visits
    revisit_merge_seconds: 1.5             # re-entry into same zone within this merges in place
    traction_window_seconds: 900           # rolling window (UI also offers 300 / 3600)
    floor_rollup_flush_seconds: 600        # durable floor_rollups row cadence
```

Loader behavior: `corridor` and shelf `front_line` are expanded to polygons at build time (no consumer-code change later), so existing `Zone` mechanics operate unchanged.

---

## 1) Path polyline per track_id (session-scoped, single camera)

**What it is:** sampled foot-point trajectory per active track in this camera context. The tracker already holds capped history; the change is a structured sampler that survives long lifetimes and retires into a compressed durable event.

**Schema (JSON):**

```json
{
  "camera_id": "cam_entrance_01",
  "store_id": "store_mumbai_001",
  "track_id": 1042,
  "started_at": "2026-10-23T11:41:55.020Z",
  "ended_at": "2026-10-23T11:43:41.100Z",
  "path": [
    { "t": "2026-10-23T11:41:55.020Z", "x": 0.42, "y": 0.68 },
    { "t": "2026-10-23T11:41:55.270Z", "x": 0.43, "y": 0.66 },
    { "...": "…", "gap": true, "why": "detection_outage" }
  ],
  "zones_visited_seq": ["glass_main", "aisle_3", "checkout_queue"],
  "path_dwell_seconds": 106.08
}
```

Sampling rules:
- Emit every `sample_interval_seconds` of track age with `min_displacement_frac` dedupe; polyline time ordered.
- Ring cap `max_points_per_track`; if a track outlives the cap, samples compress on the fly (oldest-first RDP at `rdp_epsilon_frac`).
- A detection shortfall longer than `interpolation_max_gap_seconds` inserts a `gap: true` marker — UI renders a dashed/uncertain segment. No fabricated interpolation (no accuracy claim).

**Algorithm (pseudocode)** — hook into the existing loop next to `self._write_live_snapshot`:

```
on each infer frame, for each active track t (foot point p, time now):
    sampler = track_paths.setdefault(t.track_id, TrackPath())
    if numpy(p - sampler.last_point) >= min_displacement_frac or (now - sampler.last_t) >= sample_interval_seconds:
        sampler.append({t: now, x, y in 0..1})        # ring with max_points_per_track
        if sampler.was_compressed_recently:
            sampler.rdp_compress(epsilon=rdp_epsilon_frac)

on track retire (leaves active list > track_buffer):
    emit_post_telemetry_events({
        event: "track_path",
        camera_id, track_id,
        path: compressed polyline (RDP, gap markers preserved),
        started_at, ended_at, path_dwell_seconds = ended_at-started_at,
        zones_visited_seq: episode_sequence.track_key
    })
    release sampler memory
```

Housekeeping: nothing crosses sessions or cameras; paths persist only via durable events for aggregation; in-memory ring freed on retire/flush.

## 2) Zone sequence (A → B → C) with enter/exit times

**Source hook:** existing zone membership (`active_tracks_in_zone.entered_at` in), exit at disappearance (grace 3 s applied by current code). Add an episode logger plus per-track sequence key.

**Schema:**

```json
{ "track_id": 1042, "seq": [
    { "zone": "entrance", "enter_at": "…11:41:55Z", "exit_at": "…11:42:12Z", "dwell_s": 17.1 },
    { "zone": "aisle_3",  "enter_at": "…11:42:14Z", "exit_at": "…11:43:02Z", "dwell_s": 48.0 },
    { "zone": "aisle_3",  "enter_at": "…11:43:20Z", "exit_at": "…11:43:30Z", "dwell_s": 10.0 },
    { "zone": "checkout_queue", "enter_at": "…11:43:31Z", "exit_at": null, "dwell_s": null }
  ],
  "route_key": "entrance>aisle_3>checkout_queue"      // consecutive same-zone episodes within revisit_merge_seconds merge into their run
}
```

**Algorithm:**

```
zone_episode_log per cam:  # in mem ring, capped; also posted on retire as event "track_zones"
on zone Z membership plus:
    if tid not in Z.active_tracks_in_zone:
        Z.active_tracks_in_zone[tid] = now          # already happens today
        episode[tid].start(Z, now)
on zone Z membership minus (after grace):
    ep = episode[tid].end(Z, now)
    if ep.dwell >= 0:
        seq.track_append(Z.id, ep)
        if last_two_in_seq are same Z within revisit_merge_seconds: collapse

route_key = ">".join(zone ids that appear as FIRST-visit of a consecutive run) with route_min_zones ≥ 2 else drop
```

## 3) Traction score per aisle/zone — formula = unique × dwell × revisit

All in a rolling window W = `traction_window_seconds` (default 15 min), per camera, per zone/aisle polygon (aisle corridor expanded to polygon).

Definitions (raw and honestly composable — no normalizing junk):
- `U` = distinct session track_ids with ≥1 completed episode in the polygon within W.
- `D` = mean dwell seconds per unique track (total completed dwell / U). An in-flight (still-inside) episode contributes `now - enter_at` to discourage undercounting; dwell is timestamp-based, not the stationary flag.
- `R` = revisit rate = (unique tracks with ≥2 episodes in W) / U, ∈ (0, 1].

```
zone_traction_score = U × D × R
```

Units: log-free "person-seconds with revisit weighting"; display normalized for bars only by `score / max(scores of that window)` — arithmetic display, not a claim.

**Algorithm (rollup tick, every 10 s):**

```
episodes_ring (ring buffer of closed episodes + in-flight, TTL = W)
for each zone or aisle_poly in camera:
    E = episodes for poly in W
    U = len({e.track_id})
    D = mean over (per unique track: sum of that track's episode dwells)   # totals honest re multi-episodes
    R = count(track_id with >=2 episodes)/U  (0 if U == 0)
    emit zone_traction row {zone_id, U, D, R, score}
flush durable row into floor_rollups every floor_rollup_flush_seconds
```

Suggested realistic ranges (tunable, not claims): window 300–3600 s. Edge case: a zone with 1 unique visitor gives U=1, R=0 → score = 0 — the revisit factor intentionally zeroes singletons, so the UI must show U and D alongside the score (display both raw components and the score) or long-dwell browsers become invisible.

## 4) Shelf interest — proximity + optional category label

**Mapping:** the shelf polygon is the union of `front_line` (where people stand) expanded `depth_frac` behind it (where the display juts out) — one polygon. Interest episode starts when the track's foot-point enters the polygon (same membership machinery); dwell accumulates until exit + grace.

**Category labeling (optional, when weights exist):**
- Primary existing option *(verified working historically)*: YOLO-World open-vocab boxes from the products model — attach the category of the nearest product box (centroid distance ≤ box diagonal) to the shelf's interest episode. `category_source: "yolo_world"`.
- Optional depth option (config-gated, FUTURE): CLIP zero-shot labels on the shelf-region crop with a fixed prompt list per store — `category_source: "clip"`. Off by default; enabling stays a store config choice; no accuracy claims in copy.
- Operator-fixed: `category: "handbag"` wins if set (`category_source: "fixed"`).

**Schema (durable aggregate):**

```json
{ "shelf_id": "shelf_12", "camera_id": "cam_entrance_01", "category": "handbag", "category_source": "yolo_world",
  "U": 9, "total_dwell_s": 141.2, "avg_dwell_s": 15.7, "revisits": 4, "window_seconds": 900 }
```

Privacy: foot-point proximity only; no face, no identity, no glance/pose required. (Optional glance/attention stays where it lives today — engagement enrichment, separate contract.)

## 5) Dashboard JSON — `GET /api/v1/analytics/floor?window_seconds=900[&camera_id=]`

New aggregate endpoint (10 s rollups feed it; durable rows from `floor_rollups` give history/charts). Proposed response:

```json
{
  "store_id": "store_mumbai_001",
  "camera_id": null,
  "generated_at": "2026-10-23T11:58:02Z",
  "window_seconds": 900,
  "top_routes": [
    { "route_key": "entrance>aisle_3>checkout_queue", "count": 38, "share_of_routes": 0.19, "median_path_dwell_seconds": 212.4 }
  ],
  "zone_traction": [
    { "zone_id": "aisle_3", "zone_kind": "aisle", "U": 26, "total_dwell_s": 2418.0, "avg_dwell_s": 93.0,
      "revisit_rate": 0.31, "traction_score": 738.6, "share_of_traction": 0.22, "trend": "up" }
  ],
  "shelf_dwell": [
    { "shelf_id": "shelf_12", "camera_id": "cam_entrance_01", "category": "handbag", "category_source": "yolo_world",
      "U": 9, "total_dwell_s": 141.2, "avg_dwell_s": 15.7, "revisits": 4, "window_seconds": 900 }
  ],
  "coverage_note": "session-cam only; no cross-day identity"
}
```

Durable rows (charts across windows):

```sql
CREATE TABLE IF NOT EXISTS floor_rollups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  store_id TEXT NOT NULL,
  device_id TEXT NOT NULL,
  camera_id TEXT NOT NULL,
  kind TEXT NOT NULL,                 -- 'route' | 'zone_traction' | 'shelf'
  key TEXT NOT NULL,                  -- route_key | zone_id | shelf_id
  window_seconds INTEGER NOT NULL,
  metrics_json TEXT NOT NULL,
  computed_at TEXT NOT NULL
);
```

Per-shelf cards: unique counts from in-flight episodes render LIVE once proximity mapping ships; CLIP-labeled categories render PARTIAL until enablement.

## 6) Calibration Studio marking — floor zones, aisle corridors, shelf faces

Tool flow (same Save + ~3 s hot reload as today, verified):

| Tool | Clicks | Resulting field | Loader expansion |
|---|---|---|---|
| Floor zone (dwell) | ≥3 polygon points, close on first | `zones[]` polygon (existing) | unchanged |
| **Aisle corridor** | Click center of corridor at end A, click center of end B, drag width slider | `aisles[] {id, name, corridor:{a,b,width_frac}}` | offset ±width/2 perpendicular to A→B at both ends → 4-corner strip polygon |
| **Shelf face** | Draw a straight front edge (2 clicks along the shelf front), then drag depth | `shelves[] {id, name, front_line, depth_frac, category?, auto_category}` | offset the front line inward by `depth_frac` → face polygon; dwell vs proximity uses this |

Validation (UI + loader, per the glass-workflow guardrails style):
- corridor `a ≠ b`, length on-screen ≥ 8 px scaled, `0.02 ≤ width_frac ≤ 0.2`;
- face `front_line` endpoints tolerance ≥ 6 px scaled apart; `0.01 ≤ depth_frac ≤ 0.25`;
- `auto_category: true` requires the products model present in `models.product` config (this config already exists, verified) — if absent, UI flips to `category` manual or warns and saves `category_source: fixed/none`;
- corridors may not fully overlap other corridors; shelf faces not overlapping corridor strips (guard the standing-zone semantics);
- all coords within [0,1] when `normalized: true`.

## Badge honesty (final)

- Floor zones + traction: LIVE after implementation (from verified zone membership machinery). Until then: FUTURE with copy "Traction is a designed upgrade; heatmap (verified) remains the traction view today."
- Paths / route sequences: FUTURE now; on run date, `top_routes` = LIVE for eligible sessions, with "cross-cam fusion = FUTURE (session Re-ID boundary)".
- Shelf proximity: LIVE after implementation. Category label: `yolo_world` = PARTIAL→LIVE per camera when products model enabled; `clip` = FUTURE/config-gated.
- Anything broken (outage, reload mis-config): fall back to the global rule — honest PARTIAL/empty, never fabricated numbers (same discipline as privacy-badge-matrix.md).
