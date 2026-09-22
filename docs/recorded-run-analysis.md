 # Docker run on `entrance_sample.mp4` — analysis vs. benchmark (2026-09-19)

**Inputs analysed:** the screen recording of the live stream (`enterance_sample_recorded.mp4`, 61.5s), the
edge-analyzer log (`logs190926.txt`), and the dashboard telemetry export (`2026-09-19T10-38_export.csv`,
16 live rollups, 10:13:04–10:15:48 UTC). Real YOLO (`yolo26m.pt`) was loaded in Docker for this run, so unlike
the earlier HOG-only benchmark this is genuine production-model behaviour.

**Method note.** People counts below are my hand counts of clean frames — approximate (±2 in crowded
areas), not exhaustive annotation. The recording's "People Count" overlay is the pipeline's own output.

## Bottom line

The plumbing is sound; the *numbers* it produces are not yet trustworthy.

- Log ↔ CSV ↔ dashboard agree with each other exactly (see below), so persistence/sync is working.
- But "visitors", "exits", "queue" and "dwell" are all empty or misleading because **no tripwire or queue zone is
  configured**, and the tracker hides/loses exactly the people retail analytics cares about most (people standing
  at a counter).
- ID switching and disappearing boxes are two separate, reproducible mechanisms in `tracker.py` (below).

## 1. Do the three artifacts agree? Yes.

| Log line (10:13:xx) | CSV row | Match |
|---|---|---|
| `People Count: 8 live \| New Shoppers: +15 \| Total Unique: 15` | id 917: in_count 15, occupancy 8 | ✓ |
| `11 live \| +10 \| 25` | id 918: in 10, occupancy 11 | ✓ |
| `10 live \| +1 \| 26`, `8 \| +2 \| 28`, `8 \| +3 \| 31`, `10 \| +9 \| 40` | ids 919–922 | ✓ |

`current_occupancy` is the live tracker count; `in_count` is *new confirmed track IDs*. The one anomaly in the CSV,
row id 916 (`timestamp` 2026-09-18 13:05 but `received_at` 2026-09-19 10:13:14), is a stale rollup left in the edge's
SQLite outbox from yesterday's session and delivered when the container restarted. That's the outbox working as
designed, but it also means a restart replays old rollups into "today"'s views (they're dated by `received_at`).

## 2. Discrepancies vs. reality / the benchmark

| # | Dashboard/CSV says | What's actually true | Cause |
|---|---|---|---|
| 1 | **Visitors: 81** in 164s (40 in the first 61s) | The first 61s contains roughly 20–25 distinct people (hand estimate); 81 counts *new confirmed track IDs*, not people | No tripwire configured → the fallback branch in `_generate_and_save_rollup` counts unique IDs, so every ID switch is a "new visitor" |
| 2 | **Exits: 0** in every rollup | People obviously leave | Same: without a tripwire `out_count` is hard-wired to 0 |
| 3 | **Occupancy 7–11** over the 16 live rollups (overlay 8 / 7 / 9 at t=5 / 35 / 55s) | Hand count ≈ 9 / 13 / 13 at those moments → **~55–90% recall, worst when the shop is busiest** | Stationary suppression, people cut off at the frame edge (aspect filter), heads-only people at the top of frame |
| 4 | **Queue length / wait / alert: 0** | A queue-like cluster is visible at the counter | No queue zone; plus two analytics conflicts (§3) |
| 5 | **Avg dwell 8–62s** | Cashier and counter customer stayed the whole clip (60s+) | "Dwell" = average age of currently-visible tracks; ID churn keeps it low |
| 6 | Overlay FPS 13.8 (target 15) | Pipeline sustains ~13.8, not 15 | Inference-bound. `/api/v1/device/health` reports a **hard-coded** `pipeline_fps: 13.8` (gap-analysis §3), which only coincidentally matches your machine |
| 7 | Times are 10:13–10:15 | Your clock/recording says ~15:43–15:47 | Rollups are UTC (+5:30 to IST); the dashboard now labels ranges as UTC |
| 8 | Earlier benchmark doc: "entrance_sample.mp4 is synthetic; 37 IDs in 22.9s confirms it's unsuited for detector benchmarking" | **Wrong.** It's real IP-camera footage of a shop (2017 timestamp overlay). It is the best benchmark clip we have | I inferred it from `generate_sample_video.py` without opening the file. Corrected in `tracking-benchmark.md` |
| 9 | Earlier benchmark: fragmentation "is dominated by the fallback detector, not the tracker" | With real YOLO the cashier still gets 3 IDs in 61s | That claim was too strong; tracker logic is a real contributor (§4). Softened in `tracking-benchmark.md` |

HOG-vs-YOLO on this clip (same harness and config): HOG raw-detection recall is 7–14% at two early checkpoints
(local smoke run); YOLO in your recording is ~55–90%. So the HOG numbers in `tracking-benchmark.md` are a floor, not a
prediction.

## 3. Why the queue columns are empty — root causes and proposed fix

Reproduced on the real `SimpleByteTracker` + `QueueAnalyzer` (one customer standing still in a queue zone for 20s,
13 fps):

| Configuration | Peak `queue_length` |
|---|---|
| Current defaults (`filter_stationary: true`) | **0** |
| `filter_stationary: false` | 1 |
| `filter_stationary: false` + 2 missed detections every ~2.3s | **0** |

1. **Nothing is configured.** `cameras.yaml` has no tripwire and no zones for `cam_entrance_01`, so `ctx["queues"]`
   is empty and the M0 wiring (which is correct) has nothing to read. *(Fixable now from the dashboard — see below.)*
2. **Stationary suppression removes queueing people.** `Track.is_stationary` (≥25 hits, <16px total movement) drops a
   track from the list the analytics receive. A queue *is* people standing still, so they vanish from the queue zone
   after ~2s and never reach the 5s minimum dwell.
3. **Zones forget on a single dropped detection.** The tracker only returns tracks updated within the last frame or two, and
   `Zone.update` treats absence as leaving. Two consecutive missed detections restart the dwell clock — with YOLO at
   `conf 0.5` on partially occluded people that happens constantly.

**Proposed fix (needs your go-ahead — it changes tracker/analytics semantics, so I have not touched it):**

- **Now, no code:** in *Camera Setup* (or the Calibration Studio) draw an entry tripwire at the door and a **queue**
  zone at the counter. This alone turns visitors/exits/queue from "unique IDs / 0 / 0" into real measurements — but per
  the table above, queue length will still read ~0 until the next two items land.
- **A. Stop hiding stationary people.** Return all confirmed tracks, with `is_stationary` as a flag. Tripwire keeps
  ignoring stationary tracks (it already does); zones, queue and occupancy count them; the overlay draws them dimmed so
  the video matches the numbers. Mannequin/cut-out suppression stays available as `tracking.stationary_policy:
  suppress|tag`, and staff behind the counter get a configurable **staff zone** that is excluded from occupancy/queue —
  a far better answer than guessing "staff" from lack of motion.
- **B. Zone grace period.** A track stays "in" a zone until it has been missing or outside for ~3s, so single dropped
  detections don't reset dwell.
- **C. Tests:** the three scenarios in the table become regression tests, then re-run the benchmark.

Risk: cardboard cut-outs/mannequins reappear in counts unless flagged via the staff/ignore zone or `suppress` policy.

## 4. The ID switch behind the counter — two distinct mechanisms

Observed on the cashier (woman in maroon) in the recording: **ID 13 → 70 → 78 in 61s**, with no box on her for
roughly half the clip. The man at the counter (ID 67) kept his ID but had no box for ~5s at t≈35–40s. Reproduced on
the real tracker (person tracked 5s, then hidden N frames, then reappearing at the same spot; 13 fps):

| Hidden for | Result |
|---|---|
| 20 or 44 frames (≤3.4s), same box height | **Same ID, but no box drawn** — still flagged stationary |
| 46+ frames (≥3.5s) | **New ID** (track deleted at `max_age` 45) |

1. **Boxes vanish while the track is alive** — `is_stationary` is latched from the *first* foot position and only
   clears after the foot point moves ≥22px from it. A person at a counter jitters around that threshold, so their box
   flickers on and off for seconds with the same ID. This is the "bbox disappeared for a few secs" symptom.
2. **ID switches when occlusion outlasts `max_age`.** 45 frames ≈ 3.4s at your 13.8 fps. A customer standing in front of
   the cashier occludes her for 5–15s, far beyond that. Compounding it, matching stages 2–3 reject candidates whose box
   height differs by >40%, and a cashier's box flips between full-body and upper-body-only.
3. *(Cosmetic)* Displayed IDs passed ~100 by t≈59s while only ~40 tracks were ever confirmed (per the CSV): `_next_id` increments for
   tentative tracks that never confirm. IDs on screen look like people counts and aren't.

**Proposed fix (also awaiting your go-ahead):**
- Item A above fixes mechanism 1 outright.
- **Anchored re-acquisition:** keep a *dormant* copy of any track that was stationary ≥N seconds for up to ~60s; a new
  detection with similar size within a small radius of that anchor adopts the old ID. Occlusion of a stationary person
  can't have moved them, which is why this is safe for counters and unsafe for walkers. Risk: a *different* person
  taking the same spot inherits the ID, so keep the radius/size tolerances tight and measure.
- Relax the 40% height gate for dormant/anchored tracks; compare box centre and width instead.
- Assign a display ID only when a track confirms.
- If the benchmark still shows real ID-switch rates after that, evaluate appearance embeddings (ByteTrack+ReID /
  BoT-SORT) — not before.

## 5. Recommended order

1. In Docker, get a **YOLO baseline** on this clip (5 hand-counted checkpoints are in
   `scripts/benchmark_ground_truth/entrance_sample.json`; the harness now uses `configs/pipeline.yaml` and reports raw
   detections vs tracker output separately, which quantifies the stationary-filter cost directly):
   `docker compose run --rm edge-analyzer python scripts/benchmark_tracking.py data/sample_videos/entrance_sample.mp4 --ground-truth scripts/benchmark_ground_truth/entrance_sample.json`
   (the `scripts/` folder is baked into the image, so rebuild with `docker compose build edge-analyzer` first).
2. Draw the tripwire and queue zone from the dashboard (also now testable end to end).
3. Approve/adjust A–C above and the anchored re-acquisition; I implement them behind tests and re-run the benchmark to
   prove the change.

## 6. Housekeeping observations

- `entrance_sample.mp4` has no documented origin or licence. It shows identifiable people (staff and customers) in a
  UK shop and was committed in the initial commit. If it came from a research dataset or a third party, worth
  confirming consent/licence before it travels beyond your machine (same standard applied to the Oxford dataset).
- The 55MB `enterance_sample_recorded.mp4` is untracked; I have not committed it (repo bloat; it's a screen
  capture with faces).
- Five `data/sample_videos/frame_*.jpg` files show as deleted in `git status` — not by me; restore or commit as you
  prefer.

## 7. Update: real-YOLO benchmark on `entrance_sample.mp4` (2026-09-19)

`yolo26m.pt`, `configs/pipeline.yaml`, every frame processed, 1401 frames, 66 unique track IDs, 449.5s wall-clock.

| frame | hand count | raw detections | tracker output | raw recall | tracker recall |
|---|---|---|---|---|---|
| 150 | 14 | 9 | 8 | 64% | 57% |
| 650 | 13 | 10 | 7 | 77% | 54% |
| 900 | 15 | 8 | 8 | 53% | 53% |
| 1150 | 13 | 5 | 4 | 38% | 31% |
| 1400 | 10 | 8 | 7 | 80% | 70% |
| **mean** | | | | **63%** | **53%** |

**What this changes in the analysis above**

- It matches the recording-based estimate (55–90%), so the earlier occupancy finding stands: the dashboard sees about half
  the people in view.
- **I over-weighted the tracker.** The tracker's confirmation + stationary filter costs about 10 points (0–3 people per
  frame). The bigger loss, ~37 points, happens *before* the tracker: people YOLO doesn't return, or that the size/aspect
  filters (`min_height 95`, `min_area 3000`, `min_aspect_ratio 1.0`) discard. Fixing stationary suppression is still right
  for queue analytics and box flicker (section 3–4), but it will not fix occupancy on its own.
- Frame 1150 is the worst (5 of 13). That frame has a large woman cut off by the bottom edge and a crowded top-of-frame,
  the kind of people those filters are designed to drop. I can't tell from these numbers whether YOLO missed them or the
  filters did. The harness now prints that split (below).
- 66 IDs in 107s at every-frame processing (0.62/s), versus 81 in 164s (0.49/s) in your live run; if the ~20–25 people
  per 61s hand estimate holds, that is roughly 1.6–2× inflation either way.

**New finding: inference is ~3 fps, and the live loop isn't what I assumed.** The benchmark ran at 3.1 frames/s of
detection. The overlay's "FPS 13.8" is `reader.fps_actual`, the *decode* rate. `FrameBuffer.get()` pops the **oldest**
frame (FIFO), contradicting its own comment ("inference always operates on newest frame"), so when inference lags decode
the live tracker sees roughly every 4th frame, ~1–2s behind real time. If so, every frame-count threshold in
`tracker.py` (`max_age 45`, `min_hits 4`, stationary `hits >= 25`) means ~4× more wall-clock time than the 13 fps I assumed
in section 4, and per-step motion is ~4× larger, which hurts IoU matching. I have not confirmed the live rate: the new
code logs and overlays it (`Decode FPS … | Inference FPS …`), so one run of the live pipeline settles it.

**Next measurements (no behaviour changes):**
1. Re-run the benchmark command — it now adds a table splitting each checkpoint into YOLO boxes at conf ≥ 0.25, at the
   configured conf, size-rejected and aspect-rejected. That says whether to relax the filters, raise `imgsz`, or change model.
2. Rebuild/restart the live stack and read the `Inference FPS` in the rollup log line (and the overlay).
3. Then decide together: throughput (smaller model, `imgsz`, frame-skipping that keeps the newest frame) vs filters vs the
   tracker changes in sections 3–4. The order will depend on those two measurements.

## 9. `main` vs branch: live test + comparative benchmark (2026-09-22)

Mihir ran the same live-pipeline test against `main` (initial commit, no branch fixes) in a separate git worktree/
Docker Compose project (`-p adlabs-main`), using the same `entrance_sample.mp4`, then a 34-minute run (`dashboard
stats.csv`, `docker edge analyzer logs.txt`), plus the branch's benchmark harness run against `main`'s own
`src/`/`configs/` (image `adlabs-main-edge-analyzer`, harness copied in read-only from the branch, not committed to
`main`).

### `main`'s dashboard was dead on arrival (found and fixed for the test only)

`docker logs adlabs-cloud-dashboard` showed nothing but Streamlit's own noise; the browser showed "Connection
refused" to `localhost:8000`. Root cause, confirmed by exec'ing into the container:
```
OSError: [Errno 30] Read-only file system: '/app/server/static'
```
`main`'s `docker-compose.yml` bind-mounts `./server:/app/server:ro`. `app.py` calls
`os.makedirs(STATIC_DIR, exist_ok=True)` at import time; that's a no-op if the directory already exists, but
`server/static/` doesn't exist in a fresh `main` checkout (git doesn't track empty directories, and `main` never
got the `.gitkeep` placeholder that fixes this). So the container tries to *create* the directory inside a
read-only mount, `EROFS`, uvicorn dies before binding port 8000 -- while `streamlit run` (backgrounded separately in
the same shell `CMD`) starts fine. That's exactly the split observed: dashboard UI up, API silently dead, and the
edge container's `Telemetry sync failed for N records` warnings piling up every rollup because there was nothing to
sync to.

Fixed for the test by creating the directory on the host (`mkdir server/static` in the `ADLabs-main` worktree,
container restarted) -- confirmed by the log: `Telemetry sync failed` on every rollup from 11:45:26 through
11:58:07, then `Successfully synced` from 11:58:17 onward, matching when the fix was applied. This is precisely
what commit `2b75a4a` ("add missing static dir") already fixes on the branch; I'd previously (wrongly) dismissed
that commit as redundant because `app.py` "creates the directory anyway" -- I hadn't accounted for the read-only
bind mount making that creation itself fail. Not a code change requested for `main` (main is being used as a
read-only baseline); noted here so the reasoning isn't re-litigated.

### Cross-check: log / CSV agree, same as before

`current_occupancy` and `in_count` in `dashboard stats.csv` match the corresponding `People Count` / `New Shoppers`
log lines exactly once sync resumed (e.g. row 0: `in_count 7, occupancy 6` at 12:04:06-17 vs. log `People Count: 6
live | New Shoppers: +7`). Persistence/sync itself behaves identically to the branch; only the static-dir crash was
different.

`Total Unique` climbs unbroken to 968 by the 34-minute mark (`tracked_ids_today` never resets) -- this is a
pre-existing bug present **identically on both `main` and the branch** (untouched by M0/M1), just far more visible
here because this run was ~17x longer than the earlier 2-minute tests. `queue_length` is 0 in every row, but `main`
has no queue zone configured and no UI to add one, so this run can't distinguish "no zone" from the M0 bug it can't
reach.

### The tracker bug on `main` is two bugs, and it's worse than "ID switches"

Read in full (`git show main:src/perception/tracker.py`):

1. `Track.mark_missed()` hardcodes `if self.time_since_update > 15` -- it ignores the `max_age` the tracker was
   actually constructed with (`pipeline.yaml`'s `track_buffer: 30`). Only the *pruning* step
   (`self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]`) uses the real value.
2. `Track.update()` never resets `self.state = "active"`. So a track that flips to `"lost"` at 15 missed frames
   (~1.1s at the observed 13.8fps) but hasn't yet hit `max_age=30` frames is still sitting in `self.tracks` -- and
   if it keeps winning the IoU/distance match against the real person walking past (likely; they haven't gone
   anywhere), `time_since_update` resets to 0 on every match, so it's *never* pruned either. It becomes a permanent
   zombie: silently absorbing that person's real detections every frame, `state` stuck at `"lost"`, filtered out of
   `active_list` (`if t.state != "active": continue`) forever. The box doesn't reappear later under that ID -- it's
   just gone. A new track/ID only appears once the zombie finally fails to match (person moves far enough, or
   height changes >40%), ages past `max_age=30` (~2.1-2.3s at 13.8fps), and gets pruned, freeing that detection up
   again.

This is a materially different (and worse) failure mode than "IDs expire after N seconds": it's detections being
silently swallowed by an invisible track that will never render again, not a clean expiry. It directly explains
both hand observations from the recording: "IDs switch only after >3s hidden" (the zombie's spatial grip typically
lasts that long before failing) and "fewer boxes than people in frame" (some of the missing people are detected
every frame, just absorbed by a zombie). Config (`track_buffer` in `pipeline.yaml`) can't fix this -- both are code
bugs, not tunable thresholds. Both are already fixed on the branch (commit `e825468`, predating this session):
`mark_missed(max_age=self.max_age)` uses the real config, and `Track.update()` explicitly resets
`state = "active"` on re-match.

### Comparative benchmark: branch's harness against `main`'s own tracker/detector

Same 5 hand-counted checkpoints, same `entrance_sample.mp4`, `main`'s own `src/perception/{detector,tracker}.py`
and `configs/pipeline.yaml` (unmodified) mounted into `main`'s own built image; only the benchmark script itself
(read-only, not part of `main`) came from the branch, so it's a neutral measuring instrument.

| | raw detection recall | tracker-output recall | unique track IDs |
|---|---|---|---|
| **branch** (earlier run) | 63% | **53%** | 66 |
| **main** (this run) | 63% | **45%** | **73** |

Raw recall is identical (same model, same `pipeline.yaml` perception thresholds -- expected). The gap is entirely
in what the tracker does with those detections, and `main` loses on both axes at once: fewer people rendered *and*
more IDs created -- exactly the zombie-track signature (detections silently absorbed, while unrelated new tracks
still spawn around the gap). Sharpest single checkpoint:

| frame | hand count | branch tracker output | main tracker output |
|---|---|---|---|
| 650 | 13 | 7 (54%) | **4 (31%)** |

So: fixing the two tracker bugs alone (already done on the branch) is worth roughly **8 points of tracker-output
recall and 7 fewer spurious IDs** on this clip, independent of anything else still open in sections 3-4 above
(stationary suppression, queue zone, two-stage matching). (Wall-clock for this run was 2191s vs. ~500s for prior
solo runs -- confounded by CPU contention from the still-running live `main` stack sharing the same 12-CPU Docker
Desktop VM; not a meaningful throughput comparison, excluded from the table.)

### New finding: `docker-compose.yml` `container_name` blocks running two stacks side by side

Both `main` and the branch hardcode `container_name: adlabs-edge-analyzer` / `adlabs-cloud-dashboard` /
`adlabs-rtsp-simulator` (not templated with the Compose project name). `docker compose -p adlabs-main up` therefore
creates containers *literally named* `adlabs-edge-analyzer` etc. -- identical names to the branch's own stack in
`ADLabs-dev`, just tracked under a different Compose project label internally. Compose's normal
`<project>_<service>_<index>` naming would have avoided this automatically. Running the two side by side (as this
comparison did) works only because one side was stopped; starting both at once would either collide on the
container name or one Compose project would silently adopt/recreate the other's container. Worth removing the
hardcoded `container_name` lines (or templating them) before anyone needs two environments up at once again.
