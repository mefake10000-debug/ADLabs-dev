# Edge FPS Optimization Implementation Plan

> **For agentic workers:** Implement each task in order with focused tests and reviewable commits.

**Goal:** Improve displayed/effective FPS on an M-series Mac by skipping safe detector calls, showing short-horizon track predictions between detections, and measuring each rate without changing measured analytics.

**Architecture:** A per-camera `FrameScheduler` scores small grayscale frame differences and combines that score with track state and a forced-inference deadline. Bounded detector workers keep inference off the render loop; the tracker supplies read-only prediction views for overlays, while tripwires, zones, counts, and enrichment update only from real detector results. Per-camera timing counters flow through `live.json` and the existing Model Health screen.

**Tech Stack:** Existing OpenCV/NumPy, Python threading, existing YOLO26s/pose, ONNX face/demographic models, YOLO-World product model, Next.js/TypeScript, unittest and node tests.

**Spec:** User-provided FPS optimization brief, 2026-10-24.

## Global Constraints

- Never touch `main`; work on `fps-optimization-enhance` in both repositories.
- Do not touch any `website-*` branch.
- Do not download or add model weights.
- Keep MPS inference on the fast tier; enrichment stays off MPS when the detector uses MPS.
- Do not use predicted positions for tripwire, zone, queue, or count updates.
- Force detection at least at the configured `min_inference_fps` deadline; no tracks, scene cuts, or high motion force immediate inference.
- Maintain backwards-compatible live-state fields and privacy behavior.

## Audit Answers and Baseline

- **Configured/used models:** Person detector resolves to existing `models/yolo26s.pt`; pose uses existing `models/yolo26m-pose.pt`; face uses YuNet ONNX; age/gender uses the existing INT8 ONNX when present; product interest uses existing `models/yolov8s-worldv2.pt`; head-pose is a lightweight heuristic. Pose/face/demographic/product work is in the slow tier and only runs with active tracks. OSNet is enabled/registered and load-attempted for status, but has no embedding consumer; local OSNet weights are absent. CLIP and shelf are disabled. RF-DETR is not in the active configuration/code path.
- **Measured fast-tier baseline:** 45 frames from the configured restaurant clip with the configured `yolo26s` on MPS: detector+tracker throughput 10.03 FPS; mean detector call 99.5 ms (median 97.2 ms); mean tracker update 0.13 ms. This isolated measurement excludes threaded decode, rendering, and enrichment. The clip metadata is 25 FPS; the configured reader target is 15 FPS.
- **Scheduling ruling:** When frame activity rises, keep the detector responsive and back off CPU enrichment by up to 2× the configured interval. This protects the fast tier; it trades slower pose/face/product refresh for person tracking freshness under load.
- **Safe skip boundary:** Skip detector calls only for existing confirmed tracks in low-motion scenes. No tracks, unconfirmed/recovering tracks, scene changes, high activity, or reaching the inference deadline forces a real detector call. Predictions are overlay-only and expire after a short horizon.
- **Impact measurement:** Compare detector calls/FPS, rendered FPS, skip percentage, detector duration, and sample-clip track/crossing outputs; report measured values separately from the configured source rate.
- **Prediction risk:** Linear velocity is useful only for short gaps. It will be bounded, non-mutating, visually marked as predicted, and excluded from analytics so extrapolation cannot create a crossing or dwell event.

## Review Focus

- Empty scene with a person entering during a static interval — test that no-track state forces detection.
- Sudden lighting/camera scene change — test that the frame-difference spike forces detection.
- Slow/stationary tracked person — test that skips never exceed the configured minimum inference rate.
- Fast mover or lost/unconfirmed track — test that it does not receive the long stationary cadence.
- Predicted box near a tripwire — test that prediction views do not mutate tracker history or enter analytics.

---

### Task 1: Motion-aware per-camera inference scheduler

**Files:** Create `src/optimization/__init__.py`, `src/optimization/frame_scheduler.py`; test `tests/test_frame_scheduler.py`; modify `configs/pipeline.yaml`.

**Interface:** `FrameScheduler(config).decide(frame, tracks, now, feed_fps) -> ScheduleDecision`, where decision exposes `run_inference`, `reason`, `motion_score`, and `cadence_frames`. Modes are conservative/balanced/aggressive; `min_inference_fps` defaults to 5, motion threshold to 0.01, prediction is enabled, and the safety deadline is time-based.

- [x] Add tests for first/no-track inference, static occupied cadence, high-motion inference, scene-change inference, and forced minimum-rate inference.
- [x] Run focused tests and confirm expected failures.
- [x] Implement downscaled grayscale frame difference with OpenCV; fall back to inference if frame analysis is unavailable.
- [x] Run focused tests and confirm they pass.

### Task 2: Bounded prediction views and analytics-safe scheduling

**Files:** Modify `src/perception/tracker.py`, `src/main.py`; test `tests/test_tracker_prediction.py` and scheduler integration in `tests/test_pipeline_core.py`.

**Interface:** `SimpleByteTracker.prediction_views(timestamp, max_age_seconds=0.4) -> List[Track]` returns copied track views with translated boxes and `prediction_only=True`; it must not mutate tracker state. The main loop calls analytics only after real detector inference and uses prediction views only for rendering between detector calls.

- [x] Test predicted displacement, expiry, unchanged source history/velocity, and prediction marker.
- [x] Integrate per-camera scheduler state; force real inference for empty/recovering tracks; preserve the fast detector and current MPS/CPU routing.
- [x] Run focused tests and existing tripwire/zone/tracker tests.

### Task 3: Per-camera performance telemetry

**Files:** Modify `src/main.py`, `server/app.py`; tests in `tests/test_api.py` and `tests/test_pipeline_core.py`.

**Interface:** Add additive `camera.perf` fields: `feed_fps`, `model_inference_fps`, `effective_fps`, `skip_rate`, `detector_ms_avg`, `motion_score`, and `last_schedule_reason`. Effective FPS counts frames actually written to the live overlay. Legacy `fps_decode` and `fps_inference` remain.

- [x] Test JSON and API passthrough for missing/new metrics without breaking old payloads.
- [x] Measure real calls, skips, render writes, and detector duration in bounded windows; log a compact per-camera line.
- [ ] Run API and pipeline tests.

### Task 4: Model Health display, config docs, and validation

**Files:** Modify website `src/lib/edgesight.ts`, `src/lib/data-freshness.ts`, `src/app/screens/Pipeline.tsx`, related tests, `configs/pipeline.yaml`, and both handoff docs.

- [ ] Add website tests for all four FPS/skip metrics and null/unavailable states.
- [x] Display Feed FPS, Model Inference FPS, Effective FPS, and detector skip rate per camera; never infer a missing rate.
- [x] Document cadence modes, thresholds, model usage audit, and limits in code/config docs.
- [x] Run the full backend suite, website tests, lint, and production build.
- [x] Re-run the same sample-clip measurement; compare timings and tracker/crossing behavior. Full live-stack and crossing parity still require a live camera run.
- [ ] Commit on the requested branches.
