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
