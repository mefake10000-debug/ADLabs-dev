# How EdgeSight's metrics are actually calculated

This is the ground-truth reference for every number the ops dashboard and Calibration Studio
show — written from the code as it exists today, not from what the feature was originally meant
to do. If this doc and the code ever disagree, trust the code and fix this doc.

Each section names the dashboard label, the API field it comes from, the exact formula, the
source file, and the gotchas that have actually caused confusion in testing so far.

## 1. Where a number starts: the tracker's `active_tracks`

Every metric below is computed from the list of `Track` objects `SimpleByteTracker.update()`
returns each frame ([`src/perception/tracker.py`](../src/perception/tracker.py)). A detection
only becomes part of that list once:

- it (or a detection matched to the same track) had confidence ≥ `track_thresh` (default 0.5,
  `configs/pipeline.yaml` → `tracking.track_thresh`) at least once to start the track — lower-
  confidence detections can only *extend* an existing track, never create one;
- the track has been matched for `min_hits` consecutive frames (default 4) — `_active_list()`
  filters out anything younger than that, so a brand-new detection doesn't count for ~4 frames
  (under a second at 15fps);
- it hasn't gone more than 1 frame without a fresh match (`time_since_update <= 1`) — a track
  that's briefly lost stops appearing in `active_tracks` immediately, but isn't *deleted* (and so
  can still be re-matched) until it's been missing for `max_age` frames (default 45, ~3s at
  15fps).

A track additionally carries `is_stationary` (`Track.update()`): true once it has ≥25 hits and
has moved less than 16px total from where it first appeared, false again once it's moved ≥22px.
With `stationary_policy: "tag"` (the default), stationary tracks stay in `active_tracks` — they
just render dimmer with a "(still)" label in the debug overlay. With `"suppress"`, they're
dropped from `active_tracks` entirely, which also means they stop counting for every metric
below, including queue length. **`stationary_policy: "suppress"` will make queue length
permanently read low**, since queueing is exactly what makes someone stationary — this is not a
recommended setting for a camera with a queue zone.

## 2. Footfall / entries & exits — requires a tripwire

**Dashboard:** "Visitors Today" (top KPI), "Visitors in Range" / "Exits in Range" (historical),
the Crossing Events tab.
**Source:** [`src/analytics/tripwire.py`](../src/analytics/tripwire.py) `Tripwire.update()`.

Each frame, for every active track that (a) hasn't already crossed this tripwire and (b) isn't
`is_stationary`, the tripwire checks whether the line segment from the track's *previous* foot
position to its *current* foot position (`track.history[-2]` → `track.history[-1]`) intersects
the tripwire's line, using a standard segment-intersection test. If it does, a 2D cross product
against the tripwire's own direction vector decides "in" vs "out" (`in_direction: top_to_bottom`
or `bottom_to_top`, set per-tripwire), and:

- `in_count` or `out_count` increments by 1;
- the track ID is added to `_crossed_track_ids` so the **same track can never cross the same
  tripwire twice** — this is deliberate lifetime deduping, not a bug, so a person standing near
  the line and jittering doesn't get double-counted;
- a durable crossing event is persisted independently of the 10s rollup (`local_buffer.save_event`
  in `src/main.py`), which is what the Crossing Events tab reads — so it survives even if the
  process crashes between rollups.

**Gotcha:** this only fires for movement that actually crosses the exact line you drew. A person
walking parallel to the tripwire, or crossing a few pixels outside its endpoints, is invisible to
it — footfall numbers reading low or zero usually means the tripwire's placement doesn't match
where people actually walk in that specific camera angle, not a counting bug. Recalibrating the
tripwire against real footage (rather than reusing coordinates from a different clip) is expected
and necessary per camera.

## 3. Store occupancy / "People In View"

**Dashboard:** "People In View" KPI, API field `net_occupancy`.
**Source:** `src/main.py` → `EdgePipeline._generate_and_save_rollup()`.

This is **not** a raw count of people visible in frame. It's one of two different things
depending on whether the camera has a tripwire configured:

```python
if ctx["tripwires"]:
    current_occupancy = max(0, current_in - current_out)   # cumulative net crossings, ever
else:
    current_occupancy = len(ctx["current_active_tracks"])  # raw count, this instant
```

With a tripwire: it's `max(0, total entries - total exits)` at that one tripwire, accumulated
since the process started (or since the tripwire was last hot-reloaded — see §6). If nobody has
crossed that specific line yet, or entries and exits have netted out, this reads 0 or low **even
with people clearly visible elsewhere in the frame** — that's expected, not a bug. Without a
tripwire: it's simply `len(active_tracks)` for that exact frame at rollup time.

Multi-camera aggregation (`server/app.py` → `get_live_metrics`) sums each camera's own latest
rollup's `current_occupancy` — so a 2-camera store's "People In View" is the sum of each camera's
own tripwire-net-or-raw-count, not a deduplicated store-wide headcount (the same physical person
seen by two cameras is not detected as the same person across cameras — there's no cross-camera
re-identification in this codebase).

## 4. "Total Unique" / visitor fallback (no tripwire)

**Dashboard:** shown in the edge log line only today (`Total Unique: N`); feeds "Visitors Today"
as a fallback when a camera has no tripwire.
**Source:** `src/main.py` — `ctx["tracked_ids_today"]`, a `set()` that
`ctx["tracked_ids_today"].update(t.track_id for t in active_tracks)` adds to every single frame,
for every camera, regardless of tripwires. It never resets except when a camera is hot-reloaded
with a source/FPS change (a fresh tracker context is built) — it is **not** a daily counter
despite the name; it accumulates for the lifetime of that camera context.

**Gotcha:** because `SimpleByteTracker` can assign a *new* ID to the same person after an
ID-switch (see `docs/recorded-run-analysis.md` §13 for a concrete example — someone occluded for
more than `max_age`/15fps ≈ 3 seconds gets a new ID when reacquired), this number is an upper
bound on unique visitors, not an exact count. It over-counts by roughly however many ID switches
happened.

## 5. Zone dwell (non-queue zones)

**Dashboard:** "Avg Store Dwell" KPI when a `dwell`-type zone exists for the camera (falls back
to per-track time-in-frame otherwise, see below); zone `avg_dwell_seconds` in the API.
**Source:** [`src/analytics/zones.py`](../src/analytics/zones.py) `Zone.update()` /
`get_metrics()`.

Every frame, for every active track: point-in-polygon (ray casting) against `track.foot_point`
(the bottom-center of the bounding box — where someone's feet are, not their head). A track
inside the polygon gets `entry_time` recorded the first time it's seen inside; `dwell_seconds =
max(0.5, current_time - entry_time)` is finalized and pushed onto a rolling window of the last
100 completed dwells **only once the track has been missing from the zone for more than
`exit_grace_seconds`** (default 3.0s, `configs/pipeline.yaml` → `analytics.zone_exit_grace_seconds`)
— a single missed detection while someone's still standing there doesn't truncate their dwell
time. `avg_dwell_seconds` is the mean of that rolling window; it's 0.0 until at least one dwell
has completed (someone has to *leave* the zone before their dwell counts).

**Fallback (`src/main.py`, no zones configured at all):** `avg_dwell` is instead
`mean(track.last_seen - track.first_seen for track in current_active_tracks)` — the average
time-in-frame of whoever happens to be visible *right now*, recomputed fresh every rollup. This
is why you can see real, non-zero `avg_dwell_seconds` numbers even with no zone drawn at all: it
doesn't require any calibration, just people being tracked.

## 6. Queue length & wait time

**Dashboard:** "Cashier Queue Length" KPI, "Checkout Queue Congestion Trend" chart, the 🚨
congestion alert banner.
**Source:** [`src/analytics/queue_analyzer.py`](../src/analytics/queue_analyzer.py)
`QueueAnalyzer.update()`. A `QueueAnalyzer` wraps its own internal `Zone` (point-in-polygon +
exit-grace exactly as §5), then layers queue-specific logic on top:

- `queue_length` = the count of tracks currently inside the polygon (`zone.active_tracks_in_zone`)
  whose **continuous time inside the polygon so far is ≥ 5.0 seconds**. Someone who just walked
  through the queue polygon on their way elsewhere, or has been there for 4 seconds, does **not**
  count as "in queue" yet — this 5-second floor is hardcoded, not configurable per zone today.
- `avg_wait_seconds` = mean of those same ≥5s dwell times for everyone currently waiting; if
  nobody currently qualifies, it falls back to the mean of the last 10 *completed* dwells in that
  zone (people who already finished checking out), so the number doesn't just snap to 0 the
  instant the queue empties.
- The congestion alert (`alert_active`) fires if `queue_length > max_comfortable_queue` (per-zone,
  default 4, set when the zone is drawn) **or** `avg_wait_seconds > congestion_threshold_seconds`
  (default 120s).

**Gotcha (the one that caused real confusion this session):** a queue zone has to actually exist
in `configs/cameras.yaml` and be picked up by hot-reload (§8) for any of this to run at all — if
it was never successfully saved (see the Calibration Studio's old double-click-to-close bug,
fixed in this branch), every queue number silently reads 0 the entire time, with no error
anywhere, because there's simply no `QueueAnalyzer` instance running.

## 7. Multi-camera aggregation (the cloud API)

**Source:** `server/app.py` → `get_live_metrics()` (`GET /api/v1/live`).

Each edge camera pushes its own 10-second rollup independently (`push_interval_seconds`,
default matches `rollup_interval_seconds`, 10s in `configs/pipeline.yaml`). When the dashboard
asks for store-wide numbers (no `camera_id` filter), the API takes **each camera's own most
recent rollup row** (`MAX(id) GROUP BY camera_id`, not one global "whatever synced last") and
combines them: `current_occupancy` and `queue_length` are **summed** across cameras,
`queue_alert_active` is **OR**'d (any camera in alert trips the store-wide banner),
`avg_queue_wait_seconds` and `avg_dwell_seconds` are **averaged** across cameras (not weighted by
how many people are actually in each camera's queue/zone). `total_visitors` /`total_exits` (the
historical KPIs) are a straight `SUM(in_count)` / `SUM(out_count)` over the day's rollups instead,
which is not subject to the "latest row per camera" concern since it aggregates every rollup, not
just the newest one.

## 8. Hot-reload: when does a calibration change actually take effect?

**Source:** `src/main.py` → `check_hot_reload()` / `_apply_camera_config_update()`. The edge
polls `configs/cameras.yaml`'s mtime every 3 seconds. A calibration-only change (tripwire/zone
added, edited, or removed — detected by comparing a JSON signature of `tripwires`+`zones`) flushes
a rollup with the *old* tripwire counts first, then rebuilds fresh `Tripwire`/`Zone`/
`QueueAnalyzer` objects and resets the rollup's `last_in_count`/`last_out_count` baselines to 0.
**A tripwire or zone edit resets its own counters to zero** — expected, not a bug, since the new
line/polygon is geometrically a different thing than the old one. A source or FPS change instead
tears down and rebuilds the *entire* camera context (fresh tracker, fresh `tracked_ids_today`),
since it's a different video feed. Total time from saving a calibration change to it actually
running: up to ~3s (poll interval) for hot-reload, plus up to ~10s (rollup interval) +
~10s (push interval) + ~5s (dashboard auto-refresh) before a *changed* number is visible on the
ops dashboard — worth remembering before concluding "it didn't save" when a number hasn't updated
after only a couple of seconds.

## Quick reference

| Dashboard label | API field | Needs calibration? | Resets to 0 when... |
|---|---|---|---|
| Visitors Today | `total_visitors` | Tripwire (else falls back to unique-ID count) | Never (cumulative); tripwire edit resets its own counters |
| People In View | `net_occupancy` | No (raw count) / Tripwire (net count) if configured | N/A (raw) / tripwire edit resets counters |
| Cashier Queue Length | `queue_length` | Yes — a `queue`-type zone | Zone removed, or nobody dwelling ≥5s |
| Avg Store Dwell | `avg_dwell_seconds` | No (falls back to raw track time-in-frame) | N/A |
| Checkout Queue Congestion (chart) | `queue_length`, `avg_queue_wait_seconds` history | Yes — a `queue`-type zone | Same as above |
| Peak Traffic Hour / Avg Visitors per Hour | `hourly_breakdown` | Tripwire | Never (historical aggregate) |
