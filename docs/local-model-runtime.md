# Local model runtime — 23 October 2026

Work is on `codex/local-model-repair`, based on the actual Cursor checkout at `2e6f225`. Friend mains and remote branches were not changed.

The active review deployment is the isolated Docker project `adlabs-review`: API at `127.0.0.1:8001`, portal at `127.0.0.1:3001/dashboard/live?panel=video`. It uses Docker CPU inference; this is distinct from the optional native Apple MPS launcher below. The superseded legacy API container on port 8000 is stopped, not removed.

The consolidated main pipeline uses YOLO26s at 640/MPS, RTMPose-t, OSNet ONNX, YuNet, YOLOE prompt-free product segmentation, and MiVOLO v2 when the demographic gate allows it. The duplicate YOLO26m pose path, YOLO-World + CLIP product path, and legacy age/gender ONNX are not loaded together with their replacements. The slow tier runs every 16 decoded frames and RTMPose every 4 detector frames. Demographic outputs remain cohort aggregates with k=10. MiVOLO weights are loaded strictly from the official checkpoint, using the official model implementation in the local vendor directory. The live model strip reports the worker state, cadence, and loaded model list. Full rationale and scoring are in `docs/model-stack-evaluation-2026-10-23.md`.

RF-DETR Nano is an optional secondary CPU audit, not a live visitor-count model. It is disabled during the primary live run and exits if the edge database lock is held. To run it separately after stopping the live edge, set `EDGE_RUN_RFDETR_AUDIT=1`; its detections are never added to visitor totals. A second detector process must not compete with the primary edge runtime.

Shelf-gap geometry now consumes measured product boxes. Reliable out-of-stock alerts still require calibrated shelf regions; this remains PARTIAL. The second camera is a test-pattern clip and is excluded from live inference. Client zone polygons are preserved.

## Local launch files

The native profile uses the machine-local camera/model paths. Start it with the tracked launcher, which builds a temporary runtime config and points frames/telemetry at the host API's shared storage:

- `scripts/run_native_live.py`: recommended MPS + parallel enrichment + clean AABB live profile.
- `local-runtime/run-gpu.py`: compatibility wrapper for the current native setup.
- `local-runtime/rfdetr-live.py`: independent RF-DETR validation; refuses to compete with a live edge process.
- `local-runtime/pipeline.native.yaml`: machine-specific model weights and local storage source; launcher overrides cadence and shared DB path.
- `local-runtime/cameras.yaml`: camera geometry shared with the native API.
- `.venv`: isolated dependencies, including compatible CLIP setuptools and MiVOLO timm versions.

Run inference from the repository root with `.venv/bin/python -u scripts/run_native_live.py`. Run the secondary detector only when the main edge is stopped: `EDGE_RUN_RFDETR_AUDIT=1 .venv/bin/python -u local-runtime/rfdetr-live.py`.

Active logs during this session: `/tmp/adlabs-native-live.log`, `/tmp/adlabs-rfdetr-live.log`, `/tmp/adlabs-native-api.log`, `/tmp/adlabs-native-ops.log`.

## Fixes and verification

Cached ankle coordinates now follow the body between pose passes. Pose-refined coordinates also update the same history used by tripwires. RTMPose ankle refinement is throttled in the detector loop; pose/face, demographics/products, and OSNet use bounded parallel worker passes, with model locks protecting shared instances. Shelf-gap candidates use actual product detections instead of an empty list. Person filters now admit boxes down to 55 px high and 1,200 px², with ByteTrack starting at 0.42 confidence. The local launcher selects clipped AABB boxes with compact ID tags; store-object boxes are hidden by default.

Tests: full environment suite completed 217 tests with 3 optional skips; model-worker concurrency, RF-DETR audit gating, single-writer lock, and clean overlay tests pass. UI types pass `tsc --noEmit`; lint has existing non-failing warnings.

## Limits observed

With the primary stack alone on this 8 GB Mac, recent live frames show FEED/JPEG around 9–12 FPS and MODEL around 4–9 FPS, varying with scene load. The sample feed shows live tracks after lowering the small-person filters. There is no independent hand-labeled benchmark, so this does not establish recall or false-positive rates. The live model strip reports loaded YOLO26s, YOLO26m pose, YOLO-World/CLIP, OSNet, RTMPose, and MiVOLO plus a running 3-worker slow-model scheduler. The second configured file is a color-bar test pattern, so it is not a second-person view. Shelf-gap geometry stays PARTIAL until shelf regions are calibrated. Other YOLO sizes are installed as selectable weights, not a live ensemble.
