# ID-switch detector

Finds places where the tracker probably gave one person two IDs, using only the tracker's own
output, so a clip needs no hand labelling before it can be scored. Built so that when pilot
footage arrives, each clip gets a tracking-quality number and a short list of moments to check,
instead of someone watching the whole video.

- Logic: [`src/analytics/id_switch.py`](../src/analytics/id_switch.py) (`IdSwitchDetector`)
- Runner: [`scripts/detect_id_switches.py`](../scripts/detect_id_switches.py)
- Tests: [`tests/test_id_switch.py`](../tests/test_id_switch.py)

## How it decides

Every ID switch observed so far has the same shape (the cashier going 96 → 187 → 96 → 187 in
the 2026-09-23 live run is the clearest example): one ID stops being visible, and shortly after,
a **different** ID appears where it was last seen. The detector flags exactly that handoff:

- an ID that was visible last frame is gone this frame → remember where its feet were, its box
  height, and when;
- an ID appears (brand new, or returning after a gap) within `--max-gap` seconds (default 5) and
  within `--max-distance` × the lost person's box height (default 1.0) of a remembered position →
  **suspected switch**, lost ID → new ID.

Distance is measured in box heights rather than pixels so the same setting works for someone near
the camera and someone far away. Matching is nearest-first, and one disappearance can explain at
most one appearance.

That alone is far too eager in a busy shop. The first version flagged 78 "switches" in 111s of
`entrance_sample.mp4`, and looking at the flagged frames showed why: two people standing side by side, one's
detection drops for a few frames, the other one's ID "appears" nearby. So a candidate only becomes
an event if it passes the test that separates *one person with a new ID* from *two people*: **one
person can't be on screen under two IDs at the same time.**
- If the lost ID and the new ID were ever visible in the same frame before the handoff, they're
  two people and there is no candidate.
- A candidate then waits `--max-gap` seconds. If the lost ID reappears while the new one is still
  on screen, it's withdrawn. Otherwise it's reported. Events therefore arrive up to 5s after they
  happen; the timestamps are still when the handoff occurred.
- An ID that reappears after a short gap is just itself coming back, and can't be taking over
  someone else's ID.

Each event has a `kind`:
- `new_id` — a never-before-seen ID took over. The classic switch; it inflates unique-visitor counts.
- `id_reused` — an *older* ID came back in place of the one that vanished: the "switch back" half
  of a 96 → 187 → 96 flip, or two nearby people's IDs getting crossed.

## What it can't tell you

These are suspicions, not verdicts:
- **False positives:** a real person leaving and a different real person arriving at the same spot
  within the window looks identical — most likely at a doorway, the till, or the frame edge.
- **Missed switches:** two people swapping IDs while both stay visible (crossing paths) never makes
  an ID disappear, so it's invisible to this method. So is a switch where the new ID first appears
  further away than the distance limit (a fast walker at a low frame rate).

## Running it

Needs YOLO, so it runs in the edge container. Frame rate matters — see below.

```
docker compose run --rm --no-deps edge-analyzer python scripts/detect_id_switches.py \
    data/sample_videos/entrance_sample.mp4 --process-fps 3
```

`--process-fps`: the tracker counts in **frames**, not seconds (`min_hits`, `max_age`, the
stationary rule), and the live edge analyzer only manages the "Infer FPS" shown on the stream
(about 2-4 on CPU), dropping everything in between. Leave it off to see the tracker at its best
(every frame); set it near the live Infer FPS to reproduce what the dashboard actually shows.

Stop the live `edge-analyzer` first (`docker compose stop edge-analyzer`) if you're in a hurry:
both run YOLO flat out on the same CPU, and together a 107s clip took over 40 minutes.

To try other `--max-gap` / `--max-distance` values without re-running YOLO, replay a previous
run's saved tracks. It takes seconds, and needs no YOLO:

```
docker compose run --rm --no-deps edge-analyzer python scripts/detect_id_switches.py \
    data/sample_videos/entrance_sample.mp4 \
    --replay data/storage/id_switch_runs/<previous run>/tracks.jsonl --max-distance 0.6
```

## Output

Written to `data/storage/id_switch_runs/<video>_<fps>_<timestamp>/` (gitignored — the clips
are real CCTV footage of real people and shouldn't go into the repo):

| File | What it is |
|---|---|
| `events.jsonl` | One suspected switch per line — machine-readable, easy to diff between runs or load into a spreadsheet. |
| `summary.json` | Run settings (including the tracker config used) and totals: unique IDs, candidates, how many were withdrawn as two different people, suspected switches by kind. |
| `tracks.jsonl` | Every processed frame's tracks (ID, box, stationary). Input for `--replay`. |
| `event_NNN_<mm-ss.s>.mp4` | A short annotated clip per event: from 1.5s before the lost ID was last seen to 2s after the new ID appeared, with every track's box and ID drawn. **Red** = the lost ID, **green** = the ID that took over, thin yellow = everyone else. Skip with `--no-clips`. |

The console prints a one-line-per-event table. A real `events.jsonl` line (entrance_sample,
every frame -- a confirmed true switch, the same woman re-IDed on the spot after 4.3s):

```json
{"time": 66.07, "lost_id": 44, "new_id": 49, "kind": "new_id", "gap_seconds": 4.28,
 "distance_px": 5.2, "distance_heights": 0.04, "lost_was_stationary": false,
 "lost_bbox": [595.1, 37.1, 647.6, 167.8], "new_bbox": [594.1, 39.0, 653.3, 163.2],
 "frame": 865, "video_time": "01:06.1", "clip": "event_011_01-06.1.mp4"}
```

`video_time` is position in the source video, so you can also jump straight to it in any video player.

**Disk use:** clips are H.264, about 0.5-1 MB each -- the 15-event every-frame run of
`entrance_sample.mp4` is 16 MB in total, the 20-event 3 fps run 13 MB. None of it is tracked by
git (`data/storage/id_switch_runs/` is in `.gitignore`), so it costs local disk only and never
reaches the repo; delete a run folder whenever you're done with it. Clips play at the rate the
tracker saw the video, so a `--process-fps 3` run gives choppy 3 fps clips on purpose. (Where
`ffmpeg` isn't installed the script falls back to OpenCV's writer: same clips, roughly 6x larger.)

Why a separate file rather than the edge log: the edge log is operational (rollups, reloads,
errors) and scrolls fast; switch events are review material you want to keep per run, compare
between runs and settings, and annotate. If this is later wired into the live pipeline, the same
rule applies: write events to their own `id_switches.jsonl` next to the database, and put at most
a one-line count in the main log.

## Validating a run by hand

Nothing needs recording while the script runs: watch each event's clip.
- Same person in the red box (before) and the green box (after) → **true switch**.
- Two different people (one left, another arrived) → **false positive**.

Tracking quality for a clip is then roughly *confirmed switches per minute of footage*, and the
share of false positives tells you whether `--max-gap` / `--max-distance` need tightening for that
camera angle.

## Results on `entrance_sample.mp4` (2026-09-29)

110.8s of footage, real YOLO, tracker settings from `configs/pipeline.yaml`:

| Run | Frames | Unique IDs | Candidates | Withdrawn (two people) | Suspected switches |
|---|---|---|---|---|---|
| First version, every frame (no two-people test) | 1452 | 57 | 78 | -- | **78** |
| Every frame | 1452 | 57 | 24 | 9 | **15** (all `new_id`) |
| 3 fps (what the live analyzer sees) | 291 | 49 | 31 | 11 | **20** (14 `new_id`, 6 `id_reused`) |

**Spot check of 7 of the 15 every-frame events by eye** (originally from still frames; the clips now show the same moments in motion):

| Time | Switch | What it shows | Verdict |
|---|---|---|---|
| 00:09.2 | 4 -> 17 | girl in red vs. a different girl with a backpack; the girl in red is still standing there, just undetected | false |
| 00:10.6 | 17 -> 18 | the backpack girl again; 17's box had grown to swallow a second child | true |
| 00:12.1 | 2 -> 20 | woman at the shelf vs. a girl further up | false |
| 00:20.4 | 6 -> 25 | someone half out of frame at the door | unclear |
| 00:31.5 | 10 -> 32 | two women standing side by side | likely false |
| 01:02.2 | 28 -> 46 | woman in grey; 28's box had merged her with the woman in front | likely true |
| 01:06.1 | 44 -> 49 | same woman, same spot, 4.3s later | true |

**Reading this honestly:** about half the reported events are real switches. That makes the tool
useful for **triage** -- 15 moments to check instead of 111 seconds of crowded video -- but its
count is not yet a trustworthy "switches per minute" score on its own. The remaining false
positives are nearly all the same case: a person whose detection drops out while they're still
standing there, with a *different* nearby person getting a new ID at the same moment. Position and
timing alone can't separate that from a real switch.

Two things the true positives show about the tracker itself: switches cluster where one box
**merges two people** (17 -> 18, 28 -> 46) -- the merged box then loses one of them -- and at a
**crowded back aisle** where people stand still while others walk past.

**Next refinement, if the false-positive rate matters once pilot clips arrive:** compare what the
lost and new person *look like* (a colour histogram of each box's contents). Untested so far, but
all three false positives above are people in clearly different clothing, which is exactly what
that catches; the two merged-box true positives are the ones it might wrongly reject. The same
appearance signal is what's needed to recognise staff away from their staff zone (see
`docs/metrics.md` section 9).

**Manual clip review (Mihir, 2026-10-02, 3 fps run):** consistent with the spot check above. Many
of the flagged events give the new ID to a *different* person; the genuine ones are mostly the same
person partly hidden by a shelf or by another shopper and then re-detected under a new ID. Judged
good enough as a triage tool for now, on one clip; the real verdict comes from running it on the
pilot clips.
