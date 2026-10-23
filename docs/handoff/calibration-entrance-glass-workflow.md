# Calibration Studio Workflow — Store Entrance (Glass View, Stop-Rate, Entry Tripwire)

Design spec, built on the verified EdgeSight pipeline (foot-point tripwires & zone membership, session-scoped ByteTrack IDs, `POST /api/v1/config/cameras` save + ~3 s hot reload, `POST /api/v1/telemetry/events` durable event channel).
**Status: FUTURE/design until implemented** — glass ROI and stop-rate fields don't exist in rollups today; this document is the implementation contract. No facial recognition anywhere. No accuracy percentages are claimed anywhere in this design — failure modes are badge-stated qualitatively.

Terms (per the brief):
- **Glass view (glass ROI)** — polygon over the storefront glass/window as seen by the camera.
- **Stop** — a track inside a glass ROI ≥ N seconds and never crossing IN on the entry tripwire (finalized, not instantaneous).
- **Entry tripwire** — directed 2-point line; IN vs OUT by crossing direction (existing semantics).

---

## 1) Operator click-steps (Calibration Studio, `:3000/dashboard/live?panel=calib`)

| Step | Action | UI behavior | Guardrail |
|---|---|---|---|
| 0 | Pick camera | Camera list from `GET /api/v1/config/cameras`; primary = first entry (per agreed convention until a picker ships) | — |
| 1 | **Mark glass polygon** | "Glass view" tool: click ≥3 points inside the store's view of the glass; click first point to close; name it; on-screen foot-point dots from the live preview show where tracks actually stand | Reject on <3 points or self-intersecting polygon |
| 2 | **Mark entry tripwire** | "Entry line" tool: click 2 endpoints (door sill across the entry), then click inside the *store side* of the line once — UI derives `in_direction` from that click and shows the arrow overlay | Line must not intersect or be contained by any glass polygon; store-side click must be one of the two open sides; both validated live before Save |
| 3 | **Set stop threshold** | Number field "stop after N seconds inside glass" — default 5.0; per-glass-ROI override available (min_stop_seconds) | Rank-check: N < 2.0 shows a yellow note ("too low: dwell becomes noisy"), N > 60 red |
| 4 | Validate | Side test: every glass polygon vertex must be on the *non-entry* side of every entry tripwire (people look in from outside, then cross) | Blocking warning if violated; Save disabled |
| 5 | **Save** | `POST /api/v1/config/cameras` → `{"status":"success"}` (verified flow); edge hot-reloads within ~3 s — log line "Configuration file modified on disk. Hot-reloading cameras & tripwires..." | Show the returned success toast; banner "applied" appears when the next snapshot carries the new ids |
| 6 | Live verify | Watch annotated MJPEG for ~60 s: purple glass ROI fill, tripwire arrow, foot-point dots padding the ROI; check crossing ticks in `/api/v1/events` | If zero crossings after your own walkthrough, direction/side is wrong — flip |
| 7 | Keep calibration signature | Existing `_calibration_signature` flow detects changes and rebuilds tripwires/zones automatically | — |

Notes kept honest: the studio already writes the yaml wholesale (verified), so the new blocks round-trip safely; saves are destructive-fresh not patch-free.

## 2) Config schema (normalized 0–1 coords)

Schema addition to `configs/cameras.yaml` (existing pixel configs keep working — `normalized: true` written only by new saves; loader converts 0–1*frame_resolution to pixels at build time).

```yaml
cameras:
- id: cam_entrance_01
  name: Main Store Floor & Entrance
  source: data/sample_videos/entrance_sample.mp4   # existing, unchanged
  fps_target: 15
  resolution: [1270, 720]
  normalized: true                                  # NEW: all coords below are 0–1 of frame width/height

  glass_views:                                      # NEW section
  - id: glass_main
    name: Facade glass
    polygon: [[0.42, 0.68], [0.58, 0.68], [0.58, 0.22], [0.42, 0.22]]   # any ≥3 points, clockwise or not
    min_stop_seconds: 5.0                           # ROI-specific override of the global threshold

  tripwires:                                        # existing keys + normalization
  - id: trip_entry
    name: Main door entrance
    type: entry                                     # NEW tag (informational; legacy configs behave as entry)
    line: [[0.80, 0.63], [0.77, 0.99]]              # exactly 2 normalized points
    in_direction: bottom_to_top                     # allowed: bottom_to_top|top_to_bottom|left_to_right|right_to_left

  zones:                                            # existing; same normalization
  - id: glass_step_zone                             # optional: glass dwell *counts* also feed traction aggregates
    name: Facade glass area
    type: dwell
    polygon: [[0.42, 0.68], [0.58, 0.68], [0.58, 0.22], [0.42, 0.22]]

analytics:                                          # global stop-rate config (per-ROI override wins)
  glass_stop_threshold_seconds: 5.0
  entry_attribution_seconds: 90                     # window after which a STOP without IN is finalized
```

Validation rules the UI (and loader) enforce:
- polygon ≥3 non-collinear points; tripwire exactly 2 endpoints.
- All coords within [0,1]; diagonal lengths on screen ≥ 8 px after scaling.
- No glass polygon vertex on the entry side of the tripwire.
- `min_stop_seconds` values numeric within 2–60; default from `analytics.glass_stop_threshold_seconds`.
- Multiple glass ROIs per camera allowed (store may have 2 windows); duplicates share the tripwire.

## 3) Real-time event schema (extends verified `POST /api/v1/telemetry/events`)

One event channel, discriminator field `event` — backwards-compatible (events without `event` continue to mean trip crossings):

```json
// trip_in / trip_out — map to direction=in|out on existing POST /api/v1/telemetry/events
{
  "store_id": "store_mumbai_001",
  "device_id": "edge_node_macmini_01",
  "camera_id": "cam_entrance_01",
  "event": "trip_in",                 // or "trip_out"
  "direction": "in",                  // canonicalized field kept for symmetry
  "wire_id": "trip_entry",
  "track_id": 1042,                   // session-scoped
  "crossed_at": "2026-10-23T11:45:02.318Z",
  "event_timestamp": "2026-10-23 11:45:02"
}

// glass_enter — first foot-point entry into a glass ROI by a NEW track id (per episode boundaries below)
{
  "store_id": "…",
  "device_id": "…",
  "camera_id": "cam_entrance_01",
  "event": "glass_enter",
  "glass_id": "glass_main",
  "track_id": 1033,                    // session-scoped
  "entered_at": "2026-10-23T11:41:55.020Z",
  "min_stop_seconds": 5.0
}

// glass_dwell_ms — emitted on ROI exit (accepted as-is; *not* a stop claim by itself)
{
  "store_id": "…",
  "device_id": "…",
  "camera_id": "cam_entrance_01",
  "event": "glass_dwell_ms",
  "glass_id": "glass_main",
  "track_id": 1033,
  "entered_at": "2026-10-23T11:41:55.020Z",
  "left_at": "2026-10-23T11:42:14.100Z",
  "dwell_ms": 19080
}

// stop_without_entry — event fires as soon as dwell in glass reaches N seconds (e.g. 5 s) and is later finalized
// without having cross-filtered by window boundary; payload carries episode + outcome info:
{
  "store_id": "…",
  "device_id": "…",
  "camera_id": "cam_entrance_01",
  "event": "stop_without_entry",
  "status": "final",                    // glass-only stop, no IN crossing by the same track
  "glass_id": "glass_main",
  "track_id": 1033,
  "entered_at": "…",
  "left_at": "…",
  "dwell_ms": 5123,
  "redacted_face_detections_count": 0
}

// stop_candidate — transient non-durable line when the glass dwell *just* crosses the threshold (in-memory only, could also be offered as GET-only);
{
  "store_id": "…",
  "device_id": "…",
  "camera_id": "cam_entrance_01",
  "event": "glass_stop_reached",
  "glass_id": "glass_main",
  "track_id": 1033,
  "dwell_ms": 5003
}

// stop_converted — STOP eligibility with a later IN crossing inside the entry_attribution_seconds window:
{
  "store_id": "…",
  "device_id": "…",
  "camera_id": "cam_entrance_01",
  "event": "stop_converted",
  "glass_id": "glass_main",
  "track_id": 1088,
  "entered_at": "…",
  "left_at": "…",
  "dwell_ms": 7120,
  "crossed_at": "2026-10-23T11:44:58.002Z",
  "wire_id": "trip_entry"
}
```

dataset variants:
```json
{
  "event": "glass_roi_ping",             // optional coarse preview only; never persisted
  "glass_id": "glass_main",
  "foot_point": [0.47, 0.51],
  "dwell_ms": 1200
}
```

## 4) KPI formulas (dashboard cards; per camera, per window [t1, t2])

Definitions:
- Entries (window): count of `trip_in` with `crossed_at ∈ [t1, t2)` → card **Entries**.
- Exits: count of `trip_out` with `crossed_at ∈ [t1, t2)` → card **Exits**.
- Glass entrants: episodes whose `glass_enter.entered_at ∈ [t1, t2)` → denominator for Stop-rate and Conversion.
- Stops: count of `stop_without_entry` with `status=final` **and** `left_at`∈window when measured post-attribution, or entered_at∈window for an in-flight live view (both gated on X = episode-roof leaving ROI with or without crossing):
  `stop_rate = finalized stop_without_entry episodes / glass entrants (family window).`
  In-flight variant (live card): denominator = glass entrants so far; numerator = currently-pending + completed stops; card renders with a **"settling"** state while attribution windows are open.
- Conversion (glass→entry):
  `conversion_glass_to_entry = trip_in whose track_id has ≥1 glass_enter episode (entered_at within [t1,t2)) / glass entrants`
  (if using conversion of all entries instead of glass-episodes only, fall back to per-camera totals; keep the formula family constant in one page).

Reference: stop-rate math lives **only on events** (dwell ms + finalized outcome). It independently cross-checks `people_now` occupancy but must never be derived from zone occupancy alone.

## 5) Failure modes & PARTIAL badge rules

| # | Failure mode | Mechanic | Untreated effect | UI handling / badge copy (no accuracy %) |
|---|---|---|---|---|
| 1 | **Occlusion / cluster at glass** | Tracker works per-box; 2+ people touching merge into one box or drop below height filter | Undercount of entrants (numerator&denominator shrink) | When ROI track density in frame > threshold: badge **PARTIAL** — "Crowded view — pause counts are floor-bounded, not exact" (qualitative; no invented accuracy) |
| 2 | **Camera angle / inward-facing entrance camera** | Glass may not be visible from inside the store; ROI would cover shoppers not glass | ROI doesn't measure the intended behavior | Step-1 guardrail: confirm in preview; if the ROI covers interior, badge **PARTIAL** — "Glass ROI not observable from this angle; drawn region shows interior floor" |
| 3 | **Double-count from ID churn** | ByteTrack assigns a new ID after a long-enough gap (session IDs recycle through tracker churn) | Same person = 2 glass episodes, converts to 2 entrants | If episode churn rate spiked (new-ID density in ROI vs history): badge **PARTIAL** — "ID switching may inflate pause counts; entries & exits may both rise" |
| 4 | **Sample footage looping** | ~20–30 s sample loops re-create tracks; trips can over/under attribute | Long-run rates meaningless | When source is identified as a looping sample: badge **PARTIAL** — "Sample footage loops; long-window stop-rate/conversion shown, long-run trend not meaningful" |
| 5 | **Direction mis-calibration** | Wrong side click flips IN/OUT | entries/exits swap; conversion > 1 possible | Step-6 live verify; if two consecutive lines show exits>entries with net impossible patterns: badge **PARTIAL** — "Tripwire direction may be flipped; please re-draw with the in-arrow toward the store" |
| 6 | **Foot-point edge cases** | Person leans in with foot just outside ROI; or stands with foot inside ROI but body outside | Episode miss / phantom | Show foot-point dot markers in preview overlay; if operators report systematic misses: `min_stop_seconds` tuning + badge **PARTIAL** — "Edge-of-glass pauses may be missed; tune polygon edge toward the doorway" |
| 7 | **Attribution tail** | Stop finalization waits for the attribution window | Live stop-rate lags window end, settles later | Live card shows "settling (X pending)" until window closes — never shows partial numerators as final |
| 8 | **No glass or no pause behavior** | Footfall always crosses without pauses | stop_rate legitimately ≈ 0 | **LIVE** zero (measured), not PARTIAL — only render *measured* zeros |

Badge discipline: these badges are *state descriptions from real computations* (density, churn ratio, source type, side checks) — never confidence percentages, never guessed accuracy. Where no such diagnostic exists yet, leave the badge off rather than pretend.

## Data-flow notes (implementation contract)

- All events ride the existing durable events channel; the `event` enum grows Additively. Old consumers ignoring unknown `event` values stay correct (trip rows unchanged).
- Glass episode bookkeeping is per camera-context (in-memory, like the current Re-ID gallery / staff tagging), pruned when the track retires (`track_buffer` window) or after `entry_attribution_seconds`.
- Final events (stop_without_entry / stop_converted) count only finalized outcomes; KPI cards above already encode settling vs final explicitly:
  `stop_rate_final = stops_final / glass_entrants` (default card)
  `stop_rate_live = (stops_final + stops_pending) / glass_entrants` (only shown with the settling badge).
- Occupancy cards stay on `people_now` (active tracks); stop-rate does not replace occupancy semantics.
