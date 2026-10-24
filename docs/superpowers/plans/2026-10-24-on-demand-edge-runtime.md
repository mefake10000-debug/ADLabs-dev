# On-Demand Edge Runtime Implementation Plan

> This is the planning record, not the status source of truth. Current implementation, verification, scorecard, and recovery manifest are in [`docs/handoff/foundation-audit.md`](../../handoff/foundation-audit.md). Do not interpret unchecked planning boxes as current status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep EdgeSight fully OFF after startup and add an authenticated, idempotent local control path that starts and stops only selected configured cameras.

**Architecture:** A lightweight standard-library supervisor runs in the edge container without importing the CV pipeline or loading weights. It starts the existing pipeline as a child only after an authorized request and terminates that child to unload models. The existing versioned FastAPI service exposes authenticated control endpoints and relays narrowly defined commands to the supervisor over the private Compose network; no Docker socket or arbitrary command execution is used.

**Tech Stack:** Python 3.11, FastAPI, stdlib `subprocess`/HTTP server, Docker Compose, unittest.

**Spec:** User request in this task (no spec file in the repository).

## Global Constraints

- Never edit, commit to, reset, rebase, merge into, or push to `main`; never touch `website-*` branches.
- Work only in the existing worktree branch `ai/foundation-audit-fix`, based on `20c0b66bba6ec58abdbfb6671801f7cfe5a38386`; this name is applied by renaming the already existing isolated local branch in place.
- Processing is OFF by default; startup, health checks, telemetry, and machine restart must not decode video, run inference, or load model weights.
- Do not download, enable, replace, or train models; use only existing code/configuration and keep weights outside images and Git.
- Keep queues bounded, prioritize person detection, and never feed predicted boxes into business counts.
- The control API must use a required secret, validate camera IDs against local configuration, be idempotent/auditable, and remain private/local. No Docker socket or arbitrary commands.
- Mount model weights read-only in the supervisor container; the worker may load them only after Start.
- Stop preserves historical rollups and changes current live state to OFF/stale; Docker restart returns to OFF.
- Missing model/source/error data stays unavailable/null and must not become a zero-valued business metric.
- Do not claim tenant authentication, accuracy, licensing, or performance without evidence; public customer control remains blocked until user/store authorization exists.

## Review Focus

- Missing or malformed model/source configuration: reject Start with a precise reason; remain OFF.
- Repeated Start/Stop requests and simultaneous requests: one worker/session only; stable idempotent response.
- Worker startup failure or early exit: transition to ERROR with reason; no tight retry loop.
- Stop during startup or a blocked decoder: bounded shutdown, cleared child state, and OFF confirmation only after process exit.
- Unconfigured secret or non-local control caller: reject control and expose no camera source credentials.
- Docker restart or health request: leave the supervisor OFF without opening a stream or importing model libraries.

---

### Task 1: Lazy pipeline worker and camera scope

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_pipeline_core.py`

**Interfaces:**
- Consumes configured camera IDs from a new `--camera-ids` CLI option.
- Produces a worker entry point that constructs and starts `EdgePipeline` only in the child process and filters selected IDs against enabled configured cameras.

- [ ] Add tests proving selected IDs filter the camera set and unknown/empty selections fail instead of silently running every camera.
- [ ] Run focused tests and confirm the missing selection behavior fails.
- [ ] Implement worker argument parsing and camera filtering without changing model implementations or count semantics.
- [ ] Verify focused tests pass.

### Task 2: OFF-by-default supervisor lifecycle

**Files:**
- Create: `src/runtime/supervisor.py`
- Create: `src/runtime/README.md`
- Create: `tests/test_processing_supervisor.py`

**Interfaces:**
- `GET /internal/processing/status` returns state, session ID, selected camera IDs, timestamps, worker PID, model/load errors, and freshness.
- `POST /internal/processing/start` accepts only `{camera_ids: string[]}` and returns `STARTING`/`RUNNING`/`ERROR` state with session ID.
- `POST /internal/processing/stop` returns `STOPPING` until the child exits, then `OFF`.
- Supervisor constructors/status paths must not import `src.main`, OpenCV, torch, or model registries.

- [ ] Write lifecycle tests for OFF startup, authorization, configured camera allow-list, idempotent Start/Stop, worker failure, and stop cleanup.
- [ ] Run tests to observe expected failures.
- [ ] Implement an authenticated standard-library HTTP supervisor and managed child process; use a single bounded worker and no automatic restart.
- [ ] Verify subprocess exit unloads the child’s model memory and removes its stale state.
- [ ] Run focused tests and verify passing behavior.

### Task 3: Versioned API and private Docker startup

**Files:**
- Modify: `server/app.py`
- Modify: `docker-compose.yml`
- Modify: `docker/Dockerfile.edge`
- Modify: `.dockerignore`
- Modify: `configs/pipeline.yaml`
- Test: `tests/test_api.py`
- Test: `tests/test_processing_supervisor.py`

**Interfaces:**
- `POST /api/v1/processing/start`, `POST /api/v1/processing/stop`, and `GET /api/v1/processing/status` require `X-API-Key` even if existing optional write-key configuration is unset.
- API commands relay only the fixed start/stop/status shapes to the internal supervisor; they do not execute caller-provided commands.
- Compose default starts the API/control service and idle supervisor only; simulator is opt-in under the `simulator` profile; worker is a child started only by Start.
- Supervisor receives the model directory as a read-only mount; only the started worker loads the model files.
- Stop records processing OFF/stale in the current live-state payload and does not delete SQLite rollups or persisted historical data.

- [ ] Write API tests for missing/wrong/correct key, unavailable supervisor, idempotency, and fixed camera payload.
- [ ] Run focused tests to observe failure.
- [ ] Make control secret mandatory for lifecycle routes, relay commands over the internal network, and bind published development ports to loopback.
- [ ] Change Docker entrypoint to the model-free supervisor; remove automatic inference service restart and simulator startup; use approved read-only weight mount only at worker runtime.
- [ ] Preserve historical rollups on Stop and write an OFF/stale live state; test Docker/container restart returns to OFF without stream/model startup.
- [ ] Validate Compose configuration and run focused API tests.

### Task 4: Documentation, model audit, and verification

**Files:**
- Modify: `README.md`
- Create: `docs/processing.md`
- Create: `docs/docker-run.md`
- Create: `docs/models-runtime.md`
- Create: `docs/data-security.md`
- Create: `docs/troubleshooting.md`

- [ ] Document OFF/STARTING/RUNNING/STOPPING/ERROR, safe local Start/Stop, model registry versus loaded/inference status, and Docker service profiles.
- [ ] Clearly record branch-local missing weights, the existing but count-only local evaluation reports, the API authentication/tenant-scope limitation, and backend limitations.
- [ ] Audit docs and repository paths for business/marketing material versus technical runtime/model/operations documentation; move or consolidate only when references and history can be preserved safely.
- [ ] Record model relevance by registered/enabled/loaded/inference consumer state; do not infer successful loading from config flags.
- [ ] Test decoder support only for available, permitted sample sources and report unsupported formats; do not save public video or extracted frames.
- [ ] Run `python3 -m unittest discover tests -v`, Compose config validation, and available OFF/START/STOP smoke checks; report unavailable dependencies honestly.
- [ ] Review diff for secret/data leakage, stage only intended worktree files, and commit with `[RUNTIME]`, `[API]`, `[DOCKER]`, and `[DOCS]` labels as separate purpose commits.
