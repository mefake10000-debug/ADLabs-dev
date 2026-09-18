# M4 — Tracking Accuracy Benchmark

**Status: baseline established, but NOT authoritative.** Every number in this
report was produced by the classical HOG+SVM fallback detector, not YOLO. See
[Environment limitation](#environment-limitation-this-run-used-hog-not-yolo)
before drawing any conclusion about production accuracy.

## Harness

`scripts/benchmark_tracking.py` runs the real `PersonDetector` -> `SimpleByteTracker`
(-> `Tripwire`, when ground truth calls for it) pipeline against a video and
compares the result to a manually-verified ground truth JSON file
(`scripts/benchmark_ground_truth/*.json`). Two ground-truth methods are
supported:

- **point-in-time headcount**: a specific frame index plus a manually counted
  number of clearly-visible pedestrians in that frame. Compared against
  `detector.detect()`'s raw detection count at that same frame ("detection
  recall").
- **tripwire crossings**: expected IN/OUT counts for a defined line, compared
  against the tracker-driven `Tripwire`'s actual counts ("count accuracy"),
  plus a rough ID-fragmentation estimate (`unique track IDs seen - expected
  unique people`) when the true unique-person count is also known.

Run it directly:
```
python scripts/benchmark_tracking.py data/sample_videos/mall_entrance_topdown_01.mp4 \
    --ground-truth scripts/benchmark_ground_truth/mall_entrance_topdown_01.json
```

## Why point-in-time headcount, not full crossing-based ground truth, for the new videos

The four newly-sourced mall clips (`data/sample_videos/SOURCES.md`) are general
concourse/promenade footage, not single-doorway entrance shots -- there's no
one obvious line to hand-count crossings against, and the crowd sizes make
frame-by-frame multi-object identity annotation (what real ID-switch-rate
metrics like IDF1/MOTA require) impractical to do by hand in this pass. A
manually-counted "how many people are visible in this exact frame" is a much
more tractable, verifiable proxy, so that's what was used for the two most
countable clips. `test_footage1.mp4` and `mall_crowd_dense_01.mp4` were judged
too dense to hand-count with confidence and were run without a ground-truth
claim (see [Results](#results)).

## Results

| Video | Backend | Frames | Ground truth | Result |
|---|---|---|---|---|
| `mall_entrance_topdown_01.mp4` | HOG+SVM fallback | 550 (22.0s) | 9 people @ frame 500 (manual count) | **9/9 detected (100% recall)**, but **66 unique track IDs** over the clip |
| `mall_promenade_01.mp4` | HOG+SVM fallback | 950 (31.7s) | 4 people @ frame 900 (manual count) | **2/4 detected (50% recall)**, **24 unique track IDs** |
| `test_footage1.mp4` | HOG+SVM fallback | 341 (11.4s) | none (crowd too dense to hand-count confidently) | **70 unique track IDs** in 11.4s -- exploratory only |
| `entrance_sample.mp4` (synthetic) | HOG+SVM fallback | 300 (22.9s) | none (flat-color synthetic rectangles, not real people) | **37 unique track IDs** -- confirms this video is unsuited for detector benchmarking (see below) |

Full console output (backend line, resolution, wall-clock time) is reproducible via the commands in [Reproducing](#reproducing-these-numbers).

### Reading the "unique track IDs" numbers

Unique-track-ID counts here are wildly higher than plausible real occupancy
(66 IDs for 9 real people; 24 for 4). This is **not** primarily a tracker
defect -- `SimpleByteTracker`'s matching/confirmation logic already has
dedicated test coverage (`tests/test_filtering.py`) for exactly this kind of
fragmentation. It's the fallback detector: HOG+SVM produces unstable,
flickering, sometimes spurious boxes frame-to-frame (confirmed directly --
see below), and every detection gap longer than `max_age` forces the tracker
to mint a new ID for what may be the same person, or a same-ID assignment to
what is actually a false-positive blob. The count-accuracy and ID-switch-rate
acceptance criteria for M4 are answered here, but the answer is "the fallback
detector, not the tracker, is the dominant source of error" -- which is
itself the useful finding this milestone was meant to produce.

### Synthetic sample videos are not valid detector benchmark inputs

`entrance_sample.mp4`/`checkout_sample.mp4` are procedurally drawn flat-color
rectangles (`scripts/generate_sample_video.py`), not photographic people.
The existing unit tests (`tests/test_pipeline_core.py`,
`tests/test_filtering.py`) correctly treat them as tracker/analytics-logic
fixtures by constructing `Track`/detection objects directly, never running
them through `PersonDetector.detect()`. Running the actual detector against
`entrance_sample.mp4` here (37 unique IDs from flat rectangles that are
obviously not people) confirms this is the right call -- these videos exist
for pipeline plumbing and visual regression, not detection accuracy.

## Environment limitation: this run used HOG, not YOLO

`PersonDetector` tries to load YOLO (`ultralytics`) first and only falls back
to the classical HOG+SVM detector if that fails
(`src/perception/detector.py::_init_model`). In this dev sandbox, `torch`
fails to load its native extension:

```
OSError: [WinError 1114] A dynamic link library (DLL) initialization routine
failed. Error loading ".../torch/lib/c10.dll" or one of its dependencies.
```

This is a local Windows environment issue (most likely a missing/mismatched
Microsoft Visual C++ Redistributable), not a defect in this repo's code --
`requirements-edge.txt` pins real, working versions of `torch`/`ultralytics`
for the actual edge deployment target, and the project's Docker image
(`docker/Dockerfile.edge`) is the environment that's supposed to run
inference, not this local sandbox. **Before treating any accuracy number in
this document as representative of production behavior, re-run
`scripts/benchmark_tracking.py` with YOLO actually loaded** (inside
`docker compose run edge-analyzer ...`, or after fixing the local torch
install) and update this document.

## Real, unplanned bug this benchmark run surfaced (already fixed)

Running this benchmark exposed two real defects, both fixed in this pass:

1. `PersonDetector._select_device()` only caught `ImportError` around
   `import torch`. A torch install that's present but broken (as above) raises
   `OSError`, which wasn't caught, crashing the whole detector instead of
   degrading gracefully. Now catches `Exception` broadly.
2. `PersonDetector._fallback_detect()` was a no-op stub that unconditionally
   returned `[]` -- meaning if YOLO ever fails to load in production, the
   pipeline would silently report **zero people, forever**, with no error and
   no visible signal beyond a startup log line. It's now a real (if less
   accurate) HOG+SVM detector, so a broken neural model degrades to worse
   accuracy rather than total, silent blindness. This also required pinning
   `opencv-python-headless<5.0.0` in `requirements-edge.txt` --
   `cv2.HOGDescriptor` was removed from the `opencv-python-headless` 5.0
   package, which would have silently broken this fallback in any future
   unpinned install.

## Reproducing these numbers

```
python scripts/benchmark_tracking.py data/sample_videos/mall_entrance_topdown_01.mp4 \
    --ground-truth scripts/benchmark_ground_truth/mall_entrance_topdown_01.json --max-frames 550

python scripts/benchmark_tracking.py data/sample_videos/mall_promenade_01.mp4 \
    --ground-truth scripts/benchmark_ground_truth/mall_promenade_01.json --max-frames 950

python scripts/benchmark_tracking.py data/sample_videos/test_footage1.mp4 --max-frames 341

python scripts/benchmark_tracking.py data/sample_videos/entrance_sample.mp4 --max-frames 300
```

## Open follow-up (not done in this pass)

- Re-run with real YOLO once the local torch install is fixed or via Docker,
  and replace this document's numbers with the authoritative ones.
- If HOG-based fallback accuracy ever matters for a real (non-dev-sandbox)
  deployment scenario, its very high false-positive/fragmentation rate here
  suggests its default `conf_thresh`/geometric filter constants need
  dedicated tuning -- not attempted here since production is expected to run
  YOLO, and tuning a safety-net path against manufactured urgency isn't
  warranted without a real case for relying on it.
- Full MOTA/IDF1-style ID-switch metrics (vs. this pass's coarser
  fragmentation proxy) would need frame-level multi-object ground-truth
  annotation, which is out of scope for a manual benchmarking pass.
