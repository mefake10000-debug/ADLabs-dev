# Local model runtime — 23 October 2026

Work is on `codex/local-model-repair`, based on the actual Cursor checkout at `2e6f225`. Friend mains and remote branches were not changed.

The live inference process runs natively on Apple MPS. The API runs at 127.0.0.1:8000, and the operations view at 127.0.0.1:8501/dashboard/live/ops. The existing website remains on localhost:3000/dashboard/live. Docker Desktop was stopped after the user explicitly approved a force stop.

Enabled in the main pipeline: YOLO26s at 640, YOLO26m pose, RTMPose-t, OSNet ONNX, YuNet, YOLO-World with CLIP, and MiVOLO v2. Pose and face passes run concurrently; after face assignment, demographics, products, and ReID run as independent jobs. Demographic outputs remain cohort aggregates with k=10. MiVOLO weights are loaded strictly from the official checkpoint, using the official model implementation in the local vendor directory. The model strip now reads current worker state and shows loaded models as ON.

RF-DETR Nano runs continuously in a separate CPU audit process. Its detections are deliberately not added to visitor totals, which would double-count people. Its state is recorded in `local-runtime/rfdetr-state.json` with successful inference count, source frame, timestamp, and duration. It is not a fused tracking input. A live status expires when the audit has not completed an inference in 15 seconds.

Shelf-gap geometry now consumes measured product boxes. Reliable out-of-stock alerts still require calibrated shelf regions; this remains PARTIAL. The second camera is a test-pattern clip and is excluded from live inference. Client zone polygons are preserved.

## Local launch files

The workspace-local launchers and settings are ignored by Git because they reference this machine's existing assets:

- `local-runtime/run-gpu.py`: main GPU inference, with UTC timestamps matching the API and client-editable cameras.yaml.
- `local-runtime/rfdetr-live.py`: independent RF-DETR validation.
- `local-runtime/pipeline.native.yaml`: enabled model configuration and existing storage database.
- `local-runtime/cameras.yaml`: camera geometry shared with the native API.
- `.venv`: isolated dependencies, including compatible CLIP setuptools and MiVOLO timm versions.

Run inference from the repository root with `.venv/bin/python -u local-runtime/run-gpu.py`. Run the secondary detector with `.venv/bin/python -u local-runtime/rfdetr-live.py`.

Active logs during this session: `/tmp/adlabs-native-live.log`, `/tmp/adlabs-rfdetr-live.log`, `/tmp/adlabs-native-api.log`, `/tmp/adlabs-native-ops.log`.

## Fixes and verification

Cached ankle coordinates now follow the body between pose passes. Pose-refined coordinates also update the same history used by tripwires. OSNet and RTMPose sessions use bounded CPU worker pools, including the rtmlib path. Shelf-gap candidates use actual product detections instead of an empty list. Person filters now admit boxes down to 55 px high and 1,200 px², with ByteTrack starting at 0.42 confidence. The local launcher selects clipped AABB boxes and labels; RTMPose still feeds foot-based analytics.

Tests: full environment suite completed 193 tests, 3 skipped. Final source suite completed 187 tests, 4 skipped. Separate installed-weight checks passed all three ONNX worker-budget checks.

## Limits observed

With the requested stack live on this 8 GB Mac, measured camera inference is about 1.4–2.7 FPS while RF-DETR shares the CPU. The sample feed shows 9–12 current people after lowering the small-person filters. There is no independent hand-labeled benchmark, so this does not establish recall or false-positive rates. The local model strip reports YOLO26s, YOLO26m pose, YOLO-World/CLIP, OSNet, RTMPose, MiVOLO, and RF-DETR ON only while their worker evidence is current. Shelf-gap geometry stays PARTIAL until shelf regions are calibrated. Other YOLO sizes are installed as selectable weights, not a live ensemble.
