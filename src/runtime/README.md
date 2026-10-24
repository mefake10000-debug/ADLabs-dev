# Runtime lifecycle controls

This folder owns the small process supervisor that keeps video processing OFF until an authenticated local operator starts a selected camera session.

- `supervisor.py` reads the configured camera allow-list, reports OFF/STARTING/RUNNING/STOPPING/ERROR, and launches or stops a fixed `src.main` worker command. It imports YAML and Python standard-library modules only; it does not import OpenCV, PyTorch, model registries, or video decoders.
- Input: `configs/cameras.yaml`, a required internal control key, and explicit camera IDs.
- Output: lifecycle status in `data/storage/state/live.json`; existing counts and rollups are preserved and marked stale on Stop/restart.
- Run: `python -m src.runtime.supervisor` with `CAMERAS_CONFIG`, `EDGE_STATE_DIR`, `PROCESSING_CONTROL_KEY`, `SUPERVISOR_HOST`, and `SUPERVISOR_PORT` configured. Production Docker starts this service by default; it does not start the worker.
- Test: `python3 -m unittest tests.test_processing_supervisor -v`.
- Common errors: missing key prevents supervisor startup; unknown/disabled cameras or missing files reject Start; a worker exit is reported as ERROR and requires an operator retry.

The supervisor has no Docker socket, no arbitrary command interface, and no automatic worker restart loop.
