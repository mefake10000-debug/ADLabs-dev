# AD Labs EdgeSight — MVP Gap Analysis

**Scope:** Full source-level audit of the existing prototype (branch `tracker-occlusion-fix`), tracing the real data flow from RTSP ingestion through to the dashboard, against the stated MVP requirements (stable camera-local tracking, accurate entry/exit counting, occupancy, event persistence; a dashboard covering visitors/entries/exits/occupancy/traffic-over-time/peak/average/camera status/camera-level analytics/date filtering/live updates).

This is an audit only. No implementation changes were made.

---

## 1. Current Architecture

```
[rtsp-simulator: MediaMTX+ffmpeg]
        │ RTSP (or local .mp4 files)
        ▼
StreamReader (thread per camera) → FrameBuffer (ring, drop-oldest)
        │ main.py single-threaded loop, polls all cameras sequentially
        ▼
PersonDetector (YOLO, shared model instance, anthropometric + containment filtering)
        ▼
SimpleByteTracker (per camera: IoU → distance → velocity-predicted matching,
                    temporal confirmation, stationary suppression)
        ▼
   ┌────────────┬────────────┬─────────────┐
Tripwire        Zone       QueueAnalyzer   DebugOverlay (JPEG snapshot to disk)
(in/out)       (dwell)     (queue/wait)
        │
        ▼
main.py._generate_and_save_rollup() — periodic (10s) aggregate delta
        ▼
LocalBuffer (SQLite, store_rollups + camera_health tables)
        ▼
TelemetryExporter (poll unexported rows, POST batch, retry/backoff)
        ▼
FastAPI server/app.py (/api/v1/telemetry, /api/v1/live, /api/v1/history, /api/v1/cameras,
                        /api/v1/snapshot, /api/v1/stream, /api/v1/config/cameras,
                        /api/v1/device/health) → cloud_metrics.db
        ▼
   ┌───────────────────────────┬───────────────────────────────┐
server/dashboard.py (Streamlit,  server/templates/index.html
port 8501)                       (vanilla JS + Tailwind + Chart.js,
                                  served at FastAPI "/", port 8000)
```

Three docker services (`rtsp-simulator`, `edge-analyzer`, `cloud-dashboard`) — the compose file and volume/mount design (configs shared read-write from the dashboard container, read-only into edge, enabling the calibration studio's hot-reload) is coherent and correct.

**Notable structural fact not mentioned in the README:** there are two independent, overlapping dashboard UIs (Streamlit `server/dashboard.py` and a hand-built SPA in `server/templates/index.html` served directly by FastAPI). They read the same API but are separately maintained and have diverged in features.

---

## 2. Implemented Components (genuinely work)

| Component | File | Assessment |
|---|---|---|
| RTSP/file ingestion | `src/ingestion/stream_reader.py` | Threaded, auto-reconnect with backoff, file looping, real-time playback throttling for file sources. Solid. |
| Frame ring buffer | `src/ingestion/frame_buffer.py` | Correct thread-safe drop-oldest buffer using a `Condition`. |
| Person detection | `src/perception/detector.py` | YOLO wrapper with device auto-selection (CUDA/MPS/CPU), anthropometric filtering (height/width/aspect/area) and contained-duplicate suppression. Covered by `tests/test_filtering.py`. |
| Tracking core | `src/perception/tracker.py` | 3-stage greedy matching (IoU → last-position distance → velocity-predicted position), temporal confirmation (`min_hits`), stationary-fixture suppression. Recently improved on this branch (state-reset bug fix, velocity prediction, `max_age` tuning) — see project memory `project-tracker-occlusion-work`. |
| Tripwire in/out counting | `src/analytics/tripwire.py` | Correct segment-intersection + cross-product direction logic; per-track-id crossing dedup. Covered by both test files including a "lingers near line" dedup regression test. |
| Zone dwell tracking | `src/analytics/zones.py` | Correct ray-casting point-in-polygon, entry/exit dwell accumulation, rolling 100-session window. Tested. |
| Queue analytics (computation) | `src/analytics/queue_analyzer.py` | Correct in isolation: 5s minimum-dwell-to-count-as-waiting, congestion alert thresholds on both length and wait time. Tested — **but see §5, its output is discarded before persistence.** |
| Local SQLite buffering | `src/storage/local_buffer.py`, `schema.sql` | Correct outbox-style unexported/exported flagging, straightforward schema. |
| Cloud telemetry sync | `src/telemetry/exporter.py` | Good design: retry across cloud+local endpoints, only marks exported on success, keeps unsent data safely local on failure. This is exactly the resilience story the README promises. |
| Cloud ingestion API | `server/app.py` `/api/v1/telemetry`, `/health` | Works as documented. |
| Debug/HUD overlay renderer | `src/visualizer/debug_overlay.py` | Correct, draws tracks/tripwires/zones/queues; reused for both the MJPEG stream and snapshot endpoints. |
| Docker orchestration | `docker-compose.yml`, `docker/*` | Three-service split is sound; config volume sharing between dashboard (writable) and edge (read-only) correctly enables calibration hot-reload across containers. |
| Unit tests | `tests/test_pipeline_core.py`, `tests/test_filtering.py` | Genuinely good coverage of the analytics primitives in isolation (tripwire, zone, queue, filtering, stationary suppression). |

---

## 3. Partially Implemented Components

| Component | What's missing |
|---|---|
| **Queue metrics end-to-end** | `QueueAnalyzer` computes correct values every frame, but `EdgePipeline._generate_and_save_rollup` (`src/main.py:315-317`) **hardcodes `queue_len = 0`, `avg_wait = 0.0`, `alert_active = 0`** and never reads `ctx["queues"]`. The values never reach SQLite, so they can't reach the cloud or dashboards either. See §5 — this is the single highest-priority correctness bug in the repo. |
| **Device/camera health monitoring** | `HealthMonitor` (`src/telemetry/health.py`) is instantiated in `main.py:55` but `get_system_stats()` is **never called anywhere**. `LocalBuffer.log_camera_health()` is **never called anywhere**. `StreamReader.dropped_frames` (`stream_reader.py:33`) is initialized but **never incremented**. The `camera_health` SQLite table exists in the schema and is never written to. `/api/v1/device/health` in `server/app.py:238-256` returns a **hardcoded `pipeline_fps: 13.8`** regardless of actual performance, only `cpu`/`mem` are real (via `psutil`, if installed). This is fully scaffolded plumbing with no wiring — "camera status" in the dashboard is not real telemetry today. |
| **Camera config hot-reload** | `EdgePipeline._apply_camera_config_update` (`src/main.py:249-286`) only updates tripwires/zones for camera IDs that already exist in `camera_contexts`. It cannot add a newly-configured camera or remove a deleted one without a process restart — despite the calibration UI implying live camera management. |
| **Calibration Studio (index.html)** | The "Draw Tripwire / Draw Zone Polygon / Save & Hot-Apply" canvas UI (`server/templates/index.html:253-330`) works for its happy path, but: (a) its nav view (`view-calibration`) has **no sidebar button** — it's unreachable through normal navigation; (b) `saveCalibration()` (line 614) **unconditionally replaces the entire `cameras.yaml` with a single hardcoded camera (`cam_entrance_01`)**, silently discarding any other configured cameras; (c) the "Camera & Device Settings" view's `Update Camera Stream` button calls `saveCameraSettings()`, which **is never defined** — clicking it throws a JS `ReferenceError` and does nothing; (d) the camera selector's `onchange="onCameraChange()"` likewise calls an **undefined function**. |
| **"Queue Operations" dashboard view** | `view-title` mapping and a `chartQueueInstance` variable reference a `view-queue` panel (`index.html:347,362,370`) that has no corresponding HTML section and no nav button. Planned, abandoned mid-build. |
| **Historical analytics filtering** | `/api/v1/history` (`server/app.py:157-166`) only accepts `store_id` + `limit` — no date-range parameters at all, despite "historical date filtering" being an explicit MVP dashboard requirement. |
| **Camera-level analytics** | `store_rollups`/`telemetry_rollups` both store `camera_id`, but neither `/api/v1/live` nor `/api/v1/history` accept or group by it — dashboards can only ever show store-wide aggregates, not per-camera breakdowns, even though the data model supports it. |

---

## 4. MVP Gaps (explicit comparison against stated requirements)

### Core CV

| Requirement | Status |
|---|---|
| Person detection | ✅ Implemented and filtered reasonably (§2) |
| Persistent tracking IDs | ✅ Implemented |
| Stable IDs while in view | ✅ Reasonable (IoU + distance + velocity stages) |
| Recovery from temporary detector misses | ✅ Recently improved this branch (velocity-predicted re-matching, `max_age` extended) — **not yet benchmarked**, see §6/§8 M4 |
| Reduced ID switches during occlusion | ⚠️ Improved, but the tripwire-crossing check after a long occlusion re-match uses a straight line between the pre-occlusion and post-reappearance foot points (§5) — can misfire |
| Accurate entry/exit counting | ⚠️ Logic is correct; accuracy depends on tracker ID stability, which is unverified in practice (no ground-truth benchmark exists) |
| Duplicate counting prevention | ✅ Per-track-id dedup set in `Tripwire` |
| Current occupancy | ⚠️ Computed as an unverified running `in − out` delta with **no periodic resync/drift correction** — errors compound over a long session (§5) |
| Visitor/entry/exit metrics | ✅ Computed correctly, delta-based rollups |
| **Event persistence** | ❌ **Not implemented.** Only periodic (10s) aggregate deltas are persisted (`store_rollups`). There is no durable per-crossing event record (track_id, camera_id, direction, timestamp). If a rollup interval is lost (crash between generation and flush) the underlying individual crossings are unrecoverable and unauditable. |

### Dashboard

| Requirement | Status |
|---|---|
| Visitors / entries / exits | ✅ present in both dashboards (subject to the occupancy caveat above) |
| Current occupancy | ✅ present |
| Visitor traffic over time | ✅ present (bar/line charts in both UIs) |
| Peak traffic | ❌ Not computed anywhere — no endpoint or UI element derives a peak-hour/peak-interval metric from the rollup history |
| Average traffic | ❌ Not computed anywhere |
| Camera status | ❌ Not real (see Health Monitoring gap above — everything downstream of `HealthMonitor`/`camera_health` is dead code) |
| Camera-level analytics | ❌ Not implemented (API doesn't filter/group by `camera_id`, UI camera selector is hardcoded to a single option) |
| Historical date filtering | ❌ Not implemented (API only supports `limit`) |
| Live updates | ✅ Present via polling (Streamlit `st.rerun()` every 5s; SPA `setInterval` 3s/10s) — not push-based but adequate for MVP scale |
| Queue length / wait / alerts | ❌ **Broken end-to-end** — computed correctly at the edge, discarded before persistence (§3), and both dashboards additionally hardcode-zero it a second time on the read path (`server/app.py:142-144`) |

---

## 5. Critical Correctness Issues (priority order)

1. **Queue analytics data loss (Critical).** `src/main.py:315-317` hardcodes queue rollup fields to zero instead of reading `ctx["queues"]`. Compounded by `server/app.py:142-144` (`get_live_metrics`) also hardcoding `queue_length`/`avg_queue_wait_seconds`/`queue_alert_active` to `0`/`0.0`/`False` instead of reading them from the `latest` row it already fetched (the columns exist and would be populated once bug #1 above is fixed). **Both bugs must be fixed for the queue feature — fully implemented in `queue_analyzer.py` — to work at all.** No existing test caught this because `main.py`'s orchestration and the FastAPI read endpoints have zero test coverage.

2. **Occupancy has no drift correction.** `current_occupancy = max(0, current_in - current_out)` (`main.py:296`) is a pure running counter with no periodic resync against ground truth (e.g., count of currently-active tracks, or a periodic zone-based recount). Any missed or duplicated crossing (inherent risk any tracker has, worse under occlusion/crowding) permanently biases occupancy for the rest of the session. For a retail floor running for a full business day this is a meaningful accuracy risk, not just theoretical.

3. **Tripwire crossing test during occlusion recovery uses a "teleport" segment.** `Tripwire.update` (`src/analytics/tripwire.py:41-44`) tests the line between `track.history[-2]` and `track.history[-1]`. When a track is re-acquired via the new Stage-3 velocity-predicted match after several missed frames (`tracker.py:215-242`), those two history points can be seconds and many pixels apart — a straight line between them may spuriously cross (or fail to cross) the tripwire even if the person's *actual* unobserved path did the opposite. This interacts directly with this branch's stated goal (occlusion recovery) and should be validated with the "person occluded while crossing the doorway" scenario specifically, ideally by sampling the predicted path at multiple points rather than a single 2-point segment.

4. **ID-switch → duplicate/missed counting is only mitigated, not eliminated.** If occlusion exceeds `max_age` (now 45 frames / ~3s at 15fps, or 45→ further increased to match `track_buffer` in the uncommitted config change), the lost track is dropped and a re-appearing person gets a new ID. If that ID-switch happens to straddle a tripwire crossing, it can produce a duplicate or missed count. This is inherent to any single-camera tracker-based counting approach and cannot be fully "fixed," but its practical frequency is currently unmeasured — no benchmark exists that reports ID-switch rate or count-accuracy against a labeled video (§8 M4 addresses this).

5. **No event-level persistence (see §4).** Beyond being a stated MVP requirement, this is also a data-integrity issue: a crash or restart between two rollup flushes loses the underlying crossings with no way to reconstruct or audit them, and it blocks future POS/conversion-rate correlation (flagged as a priority in `docs/research/competitor_analysis_vcount.md` — see project memory `reference-strategy-docs`) which needs event-level, not just 10-second-bucket, granularity.

6. **`tracked_ids_today` never resets and is unbounded.** `main.py:148,185,299-301` — used as the unique-visitor counter fallback when no tripwires are configured. It is a `set()` that accumulates every track ID ever seen for the lifetime of the process, with no daily reset despite the name and no cap. For a long-running edge deployment this is both a slow memory leak and a metric that silently stops meaning "today" after the first midnight.

7. **Timestamp correctness — minor.** Rollup timestamps use `time.strftime(..., time.gmtime(...))` (UTC) while the dashboard displays them unlabeled and the Streamlit sidebar/API defaults imply store-local context (`store_mumbai_001`, IST). Not a bug, but a real source of confusion once a manager compares a queue alert time against a wall clock — should be made explicit (store timezone config + labeled UTC in API, converted for display).

---

## 6. Performance Issues

- **Single-threaded, serialized per-camera processing.** `EdgePipeline.start()`'s main loop (`main.py:169-229`) processes every camera's detect → track → analytics → overlay-render → disk-write sequentially in one thread, once per outer loop iteration. `PersonDetector.detect()` (a blocking YOLO forward pass) and the synchronous `cv2.imwrite` snapshot write both happen inline. With more than 1-2 cameras this directly limits achievable per-camera FPS and is exactly the "how many streams can one Mac mini handle" question `product.md` flags as a P1 research item — currently unanswered in code or benchmark.
- **Frame snapshot export is synchronous disk I/O inside the hot loop** (`main.py:197-214`), every 2nd processed frame per camera. Under load this adds latency to the very loop that's also trying to keep up with all cameras' inference.
- **No batched inference.** Each camera's frame is sent through `model.predict()` individually; multiple simultaneous camera streams can't share a single batched GPU/ANE forward pass.
- **Tracker matching is O(tracks × detections) greedy nested loops** (`tracker.py:_match`), run three times (IoU/distance/velocity stages) per frame per camera. Fine at typical single-camera retail-scene crowd sizes (a few to ~20 people); would degrade in dense scenes, but is not a near-term concern at MVP scale.
- **`benchmark_performance.py` only measures detector+tracker latency on synthetic random-noise frames**, not the full per-camera loop (overlay render, disk write, rollup generation) and not multi-camera concurrency — so it cannot currently answer the "N streams per Mac mini" question it was written for.
- **No backpressure signal from `FrameBuffer` to `StreamReader`.** The ring buffer silently drops the oldest frame when full (correct policy for "always process newest"), but nothing surfaces "we are dropping frames" as a health/queue-depth metric — which ties back to the dead `HealthMonitor`/`camera_health` gap in §3.

---

## 7. Architecture Issues

- **Two competing dashboard implementations** (`server/dashboard.py` Streamlit app + `server/templates/index.html` vanilla-JS SPA served by FastAPI) read the same backend but have diverged: the SPA has live-stream + calibration studio + device widget that Streamlit lacks; Streamlit has cleaner historical charting. Maintaining both doubles UI work for every new metric and has already produced inconsistent behavior (queue metrics hardcoded to zero appear in both, but would need fixing twice; date filtering would need building twice). A single dashboard should be chosen for MVP (see §8, decision required — not purely technical, flagged separately below).
- **`main.py` `EdgePipeline` is a large orchestrator doing ingestion polling, detection, tracking, analytics dispatch, overlay rendering, disk I/O, rollup computation, and hot-reload in one loop/class.** It is currently the only place several bugs (queue hardcoding) can hide because there is no seam to unit-test the rollup-generation logic in isolation from the live camera loop. Splitting "build a rollup from current analytics state" into a pure, independently-testable function (no I/O) would have caught the §5 bug #1 immediately and should be part of any refactor.
- **Config coupling via shared filesystem volume** (dashboard container writes `cameras.yaml`, edge container polls its mtime every 3s) is a reasonable lightweight design for a single-node pilot, but has no conflict handling if both a human edit and the calibration UI write concurrently, and the calibration UI's "replace whole file with one hardcoded camera" bug (§3) makes this coupling actively dangerous today for any multi-camera deployment.
- **No API versioning/data-contract boundary between edge and cloud beyond an implicit dict shape.** `RollupItem`/`TelemetryPayload` Pydantic models in `server/app.py` do give schema validation on receipt, which is good — but the edge side (`local_buffer.save_rollup`) has no corresponding validation, so a schema drift would fail silently at the edge and loudly (400) at the cloud.

---

## 8. Recommended Implementation Plan

Sequenced so each milestone is independently shippable and low-risk; later milestones depend on earlier ones only where noted.

> **Status (2026-09-24):** M0-M4 done. Before starting M5/M6, five bug fixes plus dependency
> pinning/CI/API-key/credential-redaction/healthcheck hygiene were completed, followed by a live
> tier-3 verification pass that found and fixed two more real bugs (a Streamlit calibration-save
> race condition, and the Calibration Studio requiring a native double-click to close a zone --
> see `docs/performance/recorded-run-analysis.md` §9-13 for the full evidence trail, before/after benchmark,
> and live verification write-ups). `docs/product/metrics.md` is now the code-grounded reference for how
> every dashboard number is actually calculated. **M5 and M6 are both still open** -- neither has
> been started, and both are explicitly **deferred on purpose**: the team plans to acquire real
> CCTV clips from multiple pilot retail stores, and M5 (multi-camera performance) / M6 (health
> monitoring) are better sequenced against that real footage/hardware rather than built
> speculatively now. The two "Open decisions" below (dashboard consolidation, occupancy drift
> correction) are also both still open; this session narrowed the dashboard-consolidation
> question somewhat by making the Calibration Studio the single place tripwires/zones are
> created or removed (closing the two-writer race bug class) without fully retiring either UI.
> Full consolidation is intentionally **left out of this push** pending a team discussion, not
> forgotten. There is no M7 defined anywhere in this plan yet -- if one's needed (e.g. pilot
> rollout/go-live), it should be scoped explicitly rather than assumed.
>
> **Next priority after this push (per team direction, 2026-09-24):** before spending more effort
> on the specific tracking gaps below, first validate that tracking/ID-assignment itself holds up
> cleanly (no ID switches, no dropped tracks) across the *new* pilot clips once they arrive --
> not just `entrance_sample.mp4`. The two known gaps from this branch's benchmark work --
> ID-switch after occlusion exceeding `max_age` (~3s), and the frame-1150-class detector misses
> at certain camera angles (§8 M4 evidence, `docs/performance/recorded-run-analysis.md` §11) -- are being
> deliberately left unfixed for now, since real pilot footage may show a different camera angle,
> lighting, or occlusion pattern than this sample clip, and any tuning done against
> `entrance_sample.mp4` specifically could turn out to be the wrong fix (or already irrelevant)
> once that data exists.

### M0 — Fix queue-metrics data loss (Critical, do first)
- **Files:** `src/main.py` (`_generate_and_save_rollup`), `server/app.py` (`get_live_metrics`)
- **Change:** Read real `queue_length`/`avg_wait_seconds`/`alert_active` from `ctx["queues"]` (aggregate across queues on a camera, e.g. max length / max wait / any alert) instead of the hardcoded zeros; have `get_live_metrics` read those columns from `latest` instead of hardcoding.
- **Why:** Highest-severity bug — a fully-implemented, tested feature is silently inert end-to-end.
- **Dependencies:** None.
- **Tests required:** New test extending `tests/test_pipeline_core.py` that runs a `QueueAnalyzer` through `EdgePipeline`-equivalent rollup generation and asserts non-zero queue fields reach the saved rollup dict; a `server/app.py` test (new `tests/test_api.py`) asserting `/api/v1/live` echoes non-zero queue fields from a seeded DB row.
- **Acceptance criteria:** A synthetic scenario with 3+ people dwelling >5s in a queue polygon produces non-zero `queue_length`/`avg_queue_wait_seconds`/`queue_alert_active` visible in both SQLite tables and the `/api/v1/live` response.

### M1 — Per-event persistence
- **Files:** `src/storage/schema.sql` (new `crossing_events` table), `src/storage/local_buffer.py` (new `save_event`), `src/analytics/tripwire.py` (emit event on crossing instead of/in addition to updating counters), `src/main.py` (persist events as they occur, not just on rollup boundary), `server/app.py` (new `telemetry_events` table + ingestion), schema mirrored on cloud side.
- **Why:** Closes the explicit MVP "event persistence" gap (§4) and gives durable audit trail + a foundation for future POS/conversion correlation.
- **Dependencies:** None (parallel to M0).
- **Tests required:** Assert a tripwire crossing produces exactly one persisted event row with correct `track_id`/`camera_id`/`direction`/`timestamp`; crash-recovery style test (kill before rollup flush) confirming events survive independently of the 10s rollup.
- **Acceptance criteria:** Every IN/OUT crossing is individually queryable after the fact, independent of rollup aggregation.

### M2 — Consolidate to a single dashboard
- **Files:** Decision-dependent — either retire `server/dashboard.py` and finish `server/templates/index.html` (fix `onCameraChange`/`saveCameraSettings`, wire the orphaned calibration view into nav, fix `saveCalibration()`'s destructive single-camera overwrite to merge instead of replace), or the reverse.
- **Why:** §7 — duplicated UI surface area, and the SPA already has the richer live/calibration UX while Streamlit has cleaner charts; picking one avoids building every future feature twice.
- **Recommendation (not yet decided — needs your input):** Keep the FastAPI-native SPA as primary since it's already colocated with the API (single port/service story, no separate Streamlit process) and has the calibration workflow the product needs for pilot camera setup; port its missing "clean historical charts" from Streamlit. This is a product call, not purely technical — flagging per your instruction not to swap frameworks without cause.
- **Dependencies:** None functionally, but do after M0/M1 so the dashboard being finished actually has correct data to show.
- **Tests required:** None automatable for Streamlit removal itself; add a smoke test hitting the chosen dashboard's HTML/JS entry point if kept.
- **Acceptance criteria:** One dashboard, all currently-working features preserved, previously-broken buttons (`onCameraChange`, `saveCameraSettings`) either implemented or removed, calibration view reachable from nav.

### M3 — Camera-level analytics, date filtering, peak/average traffic
- **Files:** `server/app.py` (`/api/v1/live`, `/api/v1/history` gain `camera_id` + `start_date`/`end_date` params; new `/api/v1/analytics/summary` for peak/average), dashboard (chosen from M2) adds camera filter + date picker + peak/average KPI cards.
- **Why:** Closes remaining explicit MVP dashboard gaps (§4).
- **Dependencies:** M2 (build once, in the surviving dashboard).
- **Tests required:** API tests for each new query parameter combination; peak/average computed against a seeded multi-day rollup set with a known answer.
- **Acceptance criteria:** A manager can filter to one camera and an arbitrary date range and see visitors/entries/exits/occupancy/peak/average for that slice.

### M4 — Tracking accuracy benchmark (before touching the tracker further)
- **Files:** Extend `scripts/benchmark/test_count.py` into a repeatable benchmark harness; add 1-2 hand-labeled ground-truth counts for the existing sample videos.
- **Why:** Per your constraint, do not replace ByteTrack without evidence. We currently have *zero* measured ID-switch rate or count-accuracy number — the occlusion-recovery work on this branch is plausible-looking code but unverified. This milestone produces the evidence needed to decide if further tracker tuning (vs. a different algorithm) is warranted, and directly informs whether §5 issues #3/#4 need urgent attention or are already acceptable.
- **Dependencies:** Independent — can run in parallel with M0-M3.
- **Tests required:** N/A (this *is* the test/benchmark work).
- **Acceptance criteria:** A documented count-accuracy and ID-switch-rate number for `entrance_sample.mp4`/`checkout_sample.mp4` (and the currently-untracked `test_footage1.mp4`, per `project-tracker-occlusion-work` memory) against manually verified ground truth, checked into `docs/` or `scripts/`.

### M5 — Multi-camera pipeline performance (only if M4 or real pilot cameras show it's needed)
- **Files:** `src/main.py` (move per-camera detect/track/analytics into a worker per camera, or async batching), `scripts/benchmark/benchmark_performance.py` (extend to full-loop, multi-camera).
- **Why:** §6 — current design is provably single-threaded across cameras; don't build this speculatively, build it once the benchmark (extended per M4/this milestone) shows it's the actual bottleneck at the camera counts pilots will use.
- **Dependencies:** M4's benchmark harness extended to multi-camera synthetic load.
- **Tests required:** Throughput regression test (N synthetic streams sustain target FPS).
- **Acceptance criteria:** Documented max concurrent-camera count at target FPS/latency on representative hardware.

### M6 — Wire up health/camera-status monitoring
- **Files:** `src/main.py` (call `HealthMonitor.get_system_stats()` and `LocalBuffer.log_camera_health()` periodically per camera using `StreamReader.is_connected`/`fps_actual`), `server/app.py` (`/api/v1/device/health` reads real per-camera status from `camera_health` instead of hardcoded `pipeline_fps`), dashboard camera-status widget reads real data.
- **Why:** Closes the "camera status" MVP dashboard gap (§3/§4) and gives operational visibility needed before a real pilot (site survey / Phase 1 technical validation per `product.md`).
- **Dependencies:** None, can run anytime after M0.
- **Tests required:** Assert `camera_health` rows are written on a schedule and reflect a simulated disconnect.
- **Acceptance criteria:** Dashboard camera-status panel shows real online/offline/fps/dropped-frame data, not constants.

---

## 9. Keep / Refactor / Replace

| Component | Action | Reason |
|---|---|---|
| `StreamReader` + `FrameBuffer` | **KEEP** | Correct threaded reader with reconnect/loop logic and a correct thread-safe drop-oldest ring buffer. No changes needed for MVP. |
| `PersonDetector` (YOLO wrapper, filtering, dedup) | **KEEP** | Well-implemented and covered by real tests; filtering thresholds are tunable via config already. |
| `SimpleByteTracker` | **KEEP, tune** | Do not replace pending M4's benchmark. Recent occlusion-recovery changes are architecturally sound (velocity prediction is a standard, appropriate technique); what's missing is *evidence*, not a different algorithm. |
| `Tripwire` | **REFACTOR** | Core geometry/dedup logic is correct and tested; needs the occlusion-crossing edge case addressed (§5 #3) and should emit discrete events (M1) instead of only updating in-memory counters. |
| `Zone` | **KEEP** | Correct polygon/dwell logic, no known issues. |
| `QueueAnalyzer` | **KEEP** (computation) | The analytics logic itself is correct and tested — the bug is entirely in `main.py` failing to read its output (M0), not in this module. |
| `EdgePipeline` (`src/main.py`) | **REFACTOR** | Fix the queue-hardcoding bug (M0), extract rollup-building into a pure/testable function, make hot-reload able to add/remove cameras, move synchronous disk writes and (eventually) per-camera inference off the single hot loop. |
| `LocalBuffer` / `schema.sql` | **REFACTOR (extend)** | Rollup persistence is solid; add an events table (M1) and start actually writing `camera_health` (M6). |
| `TelemetryExporter` | **KEEP** | Retry/backoff/local-durability design is exactly right for an edge-offline-resilient architecture; no changes needed. |
| `HealthMonitor` / `camera_health` table | **REFACTOR (finish wiring)** | Currently dead code end-to-end (M6) — either finish it or it should be removed so it stops implying capability that doesn't exist. |
| `server/app.py` (FastAPI) | **REFACTOR** | Ingestion/telemetry endpoints are solid; fix hardcoded queue/health fields, add date-range and camera_id filtering (M0, M3, M6). |
| `server/dashboard.py` (Streamlit) | **DECIDE (likely REPLACE by consolidation, not by a new framework)** | Functional but duplicates `index.html`'s job; recommend retiring in favor of finishing the SPA (M2) rather than introducing a third stack. Explicitly not recommending React/Next.js — no technical reason found to justify a stack change. |
| `server/templates/index.html` (SPA) | **REFACTOR** | More feature-complete than Streamlit for MVP needs (live stream, calibration) but has real bugs: two undefined onclick handlers, one unreachable view, one destructive save operation, and vestiges of an abandoned "Queue Operations" view (M2). |
| `src/visualizer/debug_overlay.py` | **KEEP** | Correct and already shared cleanly between snapshot/stream endpoints. |
| `docker-compose.yml` / `docker/*` | **KEEP** | Sound service split and volume design; no changes needed for MVP. |
| `tests/test_pipeline_core.py`, `tests/test_filtering.py` | **KEEP, EXTEND** | Good unit coverage of analytics primitives; add coverage for `main.py` orchestration (rollup generation) and `server/app.py` endpoints — their absence is exactly why the §5 #1 bug shipped unnoticed. |
| `scripts/benchmark/benchmark_performance.py` | **REFACTOR (extend)** | Currently only measures detector+tracker latency on synthetic frames; needs to cover the full per-camera loop and multi-camera concurrency to actually answer the Mac-mini-scaling question (M4/M5). |
| `scripts/benchmark/test_count.py` | **REFACTOR (extend into M4's benchmark harness)** | Useful manual script today; formalize into a repeatable accuracy benchmark with ground truth. |

---

## Open decisions needing your input before implementation starts

1. **Dashboard consolidation (M2):** confirm keeping the FastAPI-native SPA (`index.html`) as primary and retiring Streamlit, or the reverse — recommendation given above, not assumed.
2. **Occupancy drift correction (§5 #2):** confirm whether a periodic resync mechanism is in scope for MVP or an accepted known limitation for the pilot.
3. **Timezone handling (§5 #7):** confirm whether store-local time display is needed for MVP or UTC-only is acceptable for the pilot phase.
