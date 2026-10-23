# Local model runtime — 23 October 2026

Work is on `codex/local-model-repair`, based on the actual Cursor checkout at `2e6f225`. Friend mains and remote branches were not changed.

The live inference process runs natively on Apple MPS. The API runs natively at 127.0.0.1:8000, and the operations view at 127.0.0.1:8501/dashboard/live/ops. The existing website remains on localhost:3000/dashboard/live.

Enabled in the main pipeline: YOLO26s at 640, YOLO26m pose, RTMPose-t, OSNet ONNX, YuNet, YOLO-World with CLIP, and MiVOLO v2. Demographic outputs remain cohort aggregates with k=10. MiVOLO weights are loaded strictly from the official checkpoint, using the official model implementation in the local vendor directory.

RF-DETR Nano runs continuously in a separate CPU validation process. Its detections are deliberately not added to visitor totals, which would double-count people. Its state is recorded in `local-runtime/rfdetr-state.json` with successful inference count, source frame, timestamp, and duration. It is not a fused tracking input.

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

Cached ankle coordinates now follow the body between pose passes. Pose-refined coordinates also update the same history used by tripwires. OSNet and RTMPose sessions use bounded CPU worker pools, including the rtmlib path. Shelf-gap candidates use actual product detections instead of an empty list.

Tests: full environment suite completed 193 tests, 3 skipped. Final source suite completed 187 tests, 4 skipped. Separate installed-weight checks passed all three ONNX worker-budget checks.

## Limits observed

This Mac has 8 GB RAM. The full simultaneous workload causes substantial memory pressure and low inference throughput. A loaded model is not evidence of high recall or smooth tracking. Missed people, occluded feet, and crowded-scene accuracy still need a measured footage benchmark; they are not declared solved. No claim is made that every installed YOLO size runs as a live ensemble.

Stopping Docker Desktop was rejected by automatic approval review because it could affect unrelated Docker work. Only project containers were stopped; the duplicate analyzer restart policy was disabled. The user subsequently explicitly approved stopping Docker Desktop, and that shutdown was requested.
