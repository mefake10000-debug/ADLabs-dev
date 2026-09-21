# M4 — Tracking Accuracy Benchmark

**Status: baseline established, but NOT authoritative.** Every number in this
report was produced by the classical HOG+SVM fallback detector, not YOLO.

> **Correction (2026-09-19):** an earlier version of this document called `entrance_sample.mp4` synthetic. That
> was wrong -- it is real IP-camera footage of a shop, and the best benchmark clip in the repo. Only
> `checkout_sample.mp4` is synthetic. See [recorded-run-analysis.md](recorded-run-analysis.md) for the analysis of a
> real-YOLO Docker run on it, and `scripts/benchmark_ground_truth/entrance_sample.json` for hand-counted checkpoints.

> **Update (2026-09-20): the HOG fallback detector was removed.** It recovered only 7-14% of people on real shop
> footage, so it produced plausible-but-wrong numbers rather than a useful degraded mode; in the Docker image it
> would not even have run (`ultralytics` pulls in the full `opencv-python` 5.0, which has no `cv2.HOGDescriptor`,
> silently defeating the `<5.0.0` pin described below). `PersonDetector` now raises at startup when
> `perception.require_model` is true (the default for the edge pipeline) and the benchmark script refuses to run
> without YOLO. Every HOG-based number in this file is historical and only a floor. Sections below that describe the
> HOG fallback as a fix are superseded by this note.

Below, this report's caveat still applies: See
[Environment limitation](#environment-limitation-this-run-used-hog-not-yolo)
before drawing any conclusion about production accuracy.

## Harness

`scripts/benchmark_tracking.py` runs the real `PersonDetector` -> `SimpleByteTracker`
(-> `Tripwire`, when ground truth calls for it) pipeline against a video and
compares the result to a manually-verified ground truth JSON file
(`scripts/benchmark_ground_truth/*.json`). Two ground-truth methods are
supported:

- **point-in-time headcount**: one or more `checkpoints` (frame index + manually
  counted visible people). At each, the harness reports the detector's raw count
  *and* the tracker's output (what analytics/dashboard actually see, after `min_hits`
  and stationary suppression), so the cost of the tracker's filtering is measured
  directly. Detector/tracker settings come from `configs/pipeline.yaml`.
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
| `entrance_sample.mp4` (real shop CCTV) | HOG+SVM fallback | 300 (22.9s) | none at the time (5 hand-counted checkpoints added 2026-09-19) | **37 unique track IDs**; a later checkpoint run shows HOG raw-detection recall of only 7-14% on this clip. Superseded by the real-YOLO run in [recorded-run-analysis.md](recorded-run-analysis.md) |

Full console output (backend line, resolution, wall-clock time) is reproducible via the commands in [Reproducing](#reproducing-these-numbers).

### Reading the "unique track IDs" numbers

Unique-track-ID counts here are wildly higher than plausible real occupancy
(66 IDs for 9 real people; 24 for 4). With the HOG fallback the detector is the
dominant cause: it produces unstable, flickering, sometimes spurious boxes
frame-to-frame, and every detection gap longer than `max_age` makes the tracker mint
a new ID. This document originally went further and said the tracker was not a
significant contributor. A later real-YOLO Docker run disproves that: the tracker
itself fragments identities (a cashier got three IDs in 61s) through its `max_age`
and stationary-suppression logic -- see
[recorded-run-analysis.md](recorded-run-analysis.md).

### `checkout_sample.mp4` is synthetic; `entrance_sample.mp4` is not

`checkout_sample.mp4` (18KB) is a procedurally drawn scene
(`scripts/generate_sample_video.py`) and is not a valid detector benchmark input.
`entrance_sample.mp4` was previously described here as synthetic too; that was an
assumption drawn from the generator script that I did not verify against the file,
and it is incorrect -- it is real shop CCTV (see the correction at the top).

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

For authoritative numbers, run inside the edge container (real YOLO); rebuild first so the
image picks up `scripts/`:

```
docker compose build edge-analyzer
docker compose run --rm edge-analyzer python scripts/benchmark_tracking.py \
    data/sample_videos/entrance_sample.mp4 \
    --ground-truth scripts/benchmark_ground_truth/entrance_sample.json
```

The commands below are the local (HOG-fallback) runs behind the table above:

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
