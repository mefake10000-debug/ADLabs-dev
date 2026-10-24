# AD Labs EdgeSight

## 🗺️ What's in this repo (plain-English map)

If you're new here, start with these two files:
- **[product.md](product.md)** — the plan: what problem we're solving and what we're trying to build.
- **[README.md](README.md)** — how to actually run it.

Then here's what every folder is, in one sentence each:

| Folder | What's actually in it |
|---|---|
| `src/` | The real "brain" of the project — the Python code that watches camera video, finds people, tracks them, and figures out things like how long they waited in line. |
| `server/` | The part that takes what `src/` figured out and turns it into a website/dashboard you can look at, plus the API other programs talk to. |
| `models/` | The AI models (pre-trained — we didn't train these ourselves) that actually detect people, poses, faces, etc. in video. |
| `configs/` | Settings files — things like "which cameras to use" and "how fast vs. how accurate should detection be," without touching code. |
| `docker/` | Instructions for packaging this project into a box ("container") so it runs the same way on any computer. |
| `scripts/` | One-off helper programs — downloading models, testing speed, generating sample videos. Not part of the live product, just tools to use while building it. |
| `tests/` | Automatic checks that make sure we didn't break anything when we change code. |
| `data/` | Sample video files and local storage used for testing/demos. |
| `docs/` | Every written explanation of a decision, a tradeoff, or how a piece works — see the map below. |

### Inside `docs/`, grouped by topic:

| Sub-folder | What it answers |
|---|---|
| `docs/architecture/` | "How does data flow from the camera to the dashboard?" |
| `docs/models/` | "Which AI models are we using, and why those ones?" |
| `docs/performance/` | "Why is the video sometimes laggy, and how do we fix it?" |
| `docs/product/` | "What are we actually supposed to be building?" |
| `docs/research/` | "What do competitors do, and how are we different?" |
| `docs/integration/` | "How does this connect to the website?" |
| `docs/tools/` | "How do I prepare/record test footage?" |
| `docs/handoff/` | A complete snapshot for someone picking this project up fresh. |

For the exact model source paths and the process for adding one safely, start with
[`docs/models/adding-models.md`](docs/models/adding-models.md). The model catalog,
runtime loader, live worker, and dashboard each report different stages; a model is
shown as running only when a fresh worker snapshot confirms it.

The website lives in the separate sibling repository at `../website/`; it is not part of this repo.

> **On-Premise Retail Edge AI & Computer Vision Analytics Platform for Existing CCTV Infrastructure**

## Current local friend-review build (23 Oct 2026)

This private `ADLabs-dev` checkout is being prepared under the `mefake10000-debug`
account for personal review. Local follow-up work is in `fps-optimization-enhance`,
created from `codex/local-model-repair`; those edits remain uncommitted and have not been pushed. The friend’s main branch is
untouched. This checkout is the source for the Docker pilot run below.

See [`docs/model-stack-evaluation-2026-10-23.md`](docs/model-stack-evaluation-2026-10-23.md)
for the researched use-case scores and keep/disable decisions. The checked-in base
profile defaults to one YOLO26n people detector. This machine's private local switch
override additionally enables YOLOE, OSNet, and RTMPose. The all-role run now publishes
every decoded frame and detects every third frame, but still does not reach 15 FPS.
MiVOLO age/gender remains off unless its privacy gate is explicitly approved.

The live path uses YOLO26n for person detections and ByteTrack IDs. Red foot marks are
drawn together with visible person boxes and labels. The current local profile also
turns on YOLOE product categories, OSNet short-visit ReID, and RTMPose foot refinement.
CLIP and RF-DETR are alternate detector/product paths, not duplicate simultaneous
workers. Shelf-gap requires an ROI; MiVOLO demographics remain privacy-gated. A model
is shown ON only when runtime evidence confirms activity; otherwise it remains waiting/off.
Counts and charts come from actual tracks, crossings, and calibrated zones; absent
signals stay zero or unknown.

Earlier detector-only Docker samples measured 4–9 inference FPS and 10–12 displayed
FPS. With YOLOE products, OSNet ReID, and RTMPose enabled alongside YOLO26n, the latest
live samples measured 1.2–2.4 inference FPS and 11.3–12.2 displayed FPS. One final
Docker resource snapshot showed the edge worker at 311% CPU and 1.29 GiB memory; Docker
still uses the host CPU. This does not meet the 15 FPS target.
The entrance sample itself is 13.1 FPS, so its unique source frames cannot reach 15 FPS.
The local profile uses 512-pixel detection input and samples the slower product/ReID
models less often; it now draws full person boxes and IDs because foot-only marks were
hard to read. Docker on Apple Silicon is CPU-only here and does not offload work from
the host CPU. Meeting 15 FPS with all models active requires a hardware-accelerated edge
runtime or a lower-cost model schedule; the current Mac/Docker combination has not
demonstrated it. Garage and restaurant clips are mounted read-only at 20 and 25 FPS.
Missing tripwires or zones produce zero/unknown values, not estimates.

### Run this checkout in Docker

Start Docker Desktop, then from this directory run:

```bash
docker compose -f docker-compose.yml -f compose.local-models.yaml \
  up -d --build cloud-dashboard edge-analyzer
```

This local profile starts the API/dashboard and edge worker (two containers). It uses
the selected local entrance clip and does not start the optional RTSP simulator. The
two pilot images currently total about 3.5 GB. The obsolete 11 GB-class images and
four stopped legacy containers were removed. Docker build cache was subsequently
pruned; its verified current size is recorded in the audit below. See
[`docs/docker-pilot-image-audit-2026-10-23.md`](docs/docker-pilot-image-audit-2026-10-23.md).
The API is published at `http://localhost:8001`; the API docs are at
`http://localhost:8001/docs`. The portal in `../website` can then run at port 3001
with `EDGE_SIGHT_URL=http://127.0.0.1:8001` set at build and start time. Inspect with:

```bash
docker compose -f docker-compose.yml -f compose.local-models.yaml ps
docker compose -f docker-compose.yml -f compose.local-models.yaml logs -f edge-analyzer
```

See [`docs/handoff/2026-10-23-local-live-review.md`](docs/handoff/2026-10-23-local-live-review.md)
for the change log, state of verification, and exact file map. See
[`docs/branch-map.md`](docs/branch-map.md) for the friend-review and working branches.
The latest CPU/FPS, Docker, Vercel and Desktop audit is in
[`docs/handoff/2026-10-23-performance-cleanup-audit.md`](docs/handoff/2026-10-23-performance-cleanup-audit.md).

### Source and configuration map

- `server/` — FastAPI endpoints, Streamlit dashboard, live session, source picker,
  model switches, and telemetry presentation.
- `src/ingestion/` — camera/video decoding and frame delivery.
- `src/perception/` — people detection, tracking, model scheduling, and refiners.
- `src/analytics/` — zones, tripwires, queues, dwell, safety, staff, and product signals.
- `src/visualizer/` — person boxes, labels, foot points, and video overlays.
- `configs/` — shared camera and pipeline defaults.
- `local-runtime/` — local camera, pipeline, and model-switch settings for this machine.
- `compose.local-models.yaml` — local footage/model mounts and the two-service Docker profile.
- `docs/handoff/` — dated change notes, verification, schemas, and reviewer handoff.
- `../website/` — separate sibling Next.js portal repository; it is not inside EdgeSight.

---

## 📌 Executive Overview

Brick-and-mortar retailers maintain substantial surveillance infrastructure (Hikvision, Dahua, CP Plus, Uniview, Axis), but these cameras currently act as passive security archives without delivering operational business intelligence.

**AD Labs EdgeSight** transforms existing CCTV cameras into an intelligent, privacy-preserving store analytics platform using edge compute appliances (such as the **Apple Silicon Mac mini M2/M4**).

### Core Differentiators
1. **Zero Camera Replacement:** Ingests standard RTSP/ONVIF sub-streams directly from existing local NVRs or IP cameras.
2. **Edge Privacy by Design:** 100% of video decoding, person detection, and spatial tracking runs on-premise. **Zero raw video leaves the store.** Only lightweight, anonymous metric JSON rollups are synchronized to the cloud.
3. **No Expensive Dedicated 3D Sensors:** Replaces costly proprietary sensors ($1,500–$2,500/entrance from RetailNext or FootfallCam) with affordable edge computing.
4. **Resilient Local Buffering:** Continues logging footfall, dwell, and queue analytics to a local SQLite buffer during internet outages and auto-syncs when connectivity resumes.

---

## 🐳 Containerized Architecture (`docker-compose.yml`)

The development Compose file defines three modular services. The local pilot overlay
starts only the API/dashboard and edge worker; the RTSP simulator is optional and is
not needed when using the selected local video file. This avoids running a third
container at the pilot store:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DOCKER COMPOSE STACK                             │
│                                                                             │
│  ┌───────────────────────┐             ┌─────────────────────────────────┐  │
│  │    rtsp-simulator     │             │          edge-analyzer          │  │
│  │                       │             │                                 │  │
│  │  • MediaMTX Server    │  RTSP       │  • StreamReader (Multi-threaded)│  │
│  │  • FFmpeg Stream Loop │────────────►│  • YOLO26n Person Detector (CPU)│  │
│  │  • Feeds:             │  Port 8554  │  • ByteTrack Object Tracking    │  │
│  │    /entrance          │             │  • Bidirectional Tripwires      │  │
│  │    /checkout          │             │  • Dwell & Queue Analyzers      │  │
│  └───────────────────────┘             │  • Local SQLite Rollup Cache    │  │
│                                        └────────────────┬────────────────┘  │
│                                                         │ JSON Telemetry    │
│                                                         │ (Port 8000)       │
│                                                         ▼                   │
│                                        ┌─────────────────────────────────┐  │
│                                        │         cloud-dashboard         │  │
│                                        │                                 │  │
│                                        │  • FastAPI Telemetry Receiver   │  │
│                                        │  • Real-Time Spatial Analytics  │  │
│                                        │  • Streamlit Live Operations UI │  │
│                                        │  • Real-Time Queue Alert Engine │  │
│                                        └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Services Breakdown
1. **`rtsp-simulator` (Port 8554):**
   * Powered by MediaMTX and FFmpeg.
   * Broadcasts looping sample retail video streams over RTSP (`rtsp://rtsp-simulator:8554/entrance` and `rtsp://rtsp-simulator:8554/checkout`).
   * **Enables complete end-to-end development, testing, and demos without requiring live in-store CCTV IP addresses.**
2. **`edge-analyzer`:**
   * Ingests RTSP streams or local video files via threaded `StreamReader`.
   * The local Docker profile runs YOLO26n person detection on CPU with ByteTrack. Docker does not expose Apple Metal (MPS) in this setup; see the measured local rates above.
   * Tracks individual shoppers using IoU ByteTrack across frames.
   * Computes spatial retail telemetry: entrance/exit tripwires, polygonal dwell zones, and cashier queue wait-times.
   * Periodically saves 30-second metric rollups to local SQLite storage and flushes them to the cloud.
3. **`cloud-dashboard` (Ports 8000 & 8501):**
   * **FastAPI Backend (Port 8000):** Exposes `/api/v1/telemetry` and `/api/v1/live`.
   * **Streamlit UI (Port 8501):** Interactive dashboard featuring real-time visitor counters, store occupancy, average dwell times, and queue congestion alerts.
   * **Zero POS Integration Required:** The platform operates entirely on computer vision telemetry with zero external IT or billing system dependencies.

---

## 🚀 Quickstart & Execution

### 1. Running with Docker Compose (Recommended)
Make sure Docker Desktop or the Docker daemon is running, then run:

```bash
docker compose up --build
```

Once running:
* **Web Operations Dashboard:** Open [http://localhost:8501](http://localhost:8501)
* **Cloud Telemetry API Docs:** Open [http://localhost:8000/docs](http://localhost:8000/docs)
* **Simulated RTSP Streams:** Available at `rtsp://localhost:8554/entrance` and `rtsp://localhost:8554/checkout`

### 2. Switching to Physical In-Store CCTV Cameras
When deploying to a pilot retail store with live cameras:
1. Open `configs/cameras.yaml`.
2. Update the `source` fields with your in-store RTSP URLs:
   ```yaml
   cameras:
     - id: "cam_entrance_01"
       name: "Main Entrance"
       source: "rtsp://admin:password@192.168.1.100:554/Streaming/Channels/102"
     - id: "cam_checkout_01"
       name: "Cashier Counter"
       source: "rtsp://admin:password@192.168.1.101:554/Streaming/Channels/102"
   ```
3. Stop the `rtsp-simulator` container (`docker compose stop rtsp-simulator`)—zero code modifications required!

### 2b. Switching Sources & Calibrating from the Dashboard (no YAML editing)
Open the Streamlit dashboard ([http://localhost:8501](http://localhost:8501)) → **⚙️ Camera Setup** tab:
* **Video source:** pick any file in `data/sample_videos/` or paste an `rtsp://` URL and press *Apply source*. The
  edge analyzer notices the change within ~3 seconds and restarts that camera with a fresh tracker and counters
  (the interrupted interval is flushed first, so nothing is lost). Only the chosen camera is touched; its
  tripwires/zones and other cameras are preserved.
* **Tripwires & zones:** read pixel coordinates off the gridded live frame, then add an entry tripwire (drives real
  IN/OUT counts) and a **queue** zone (drives queue length/wait/alerts). Without a tripwire, "visitors" falls back to
  counting unique tracker IDs and exits stay 0; without a queue zone the queue columns stay 0.
* For click-to-draw calibration use the Calibration Studio linked in the sidebar (port 8000).

The sidebar also filters every metric by **camera** and **date range** (UTC); the *Historical* row shows peak hour,
average visitors/hour and totals for that slice. The dashboard container mounts `data/sample_videos` read-only so it can
list and validate video sources — after pulling this change, run `docker compose up -d --build` once.

### 2c. Iterating Without Rebuilding Images
`src/`, `configs/`, `scripts/`, `models/` and `data/sample_videos/` are bind-mounted into the edge container, and
`server/` into the dashboard container, so most changes need **no image build**:

| You changed | Run |
|---|---|
| `src/`, `configs/`, `scripts/` | `docker compose restart edge-analyzer` (Python re-imports on start) |
| Benchmark / any one-off script | `docker compose run --rm --no-deps edge-analyzer python scripts/benchmark/benchmark_tracking.py …` (`--no-deps` skips starting the other services) |
| `server/` API code | `docker compose restart cloud-dashboard` (Streamlit hot-reloads by itself; uvicorn doesn't) |
| `docker-compose.yml` | `docker compose up -d` (recreates only what changed) |
| `requirements-*.txt` or `docker/Dockerfile.*` | `docker compose build <service>` — the **only** case that needs a build |

Build-size notes: the edge image installs **CPU-only PyTorch** in its own cached layer (~2.8GB total instead of ~10GB;
the default Linux wheel bundles ~4GB of CUDA libraries that Docker Desktop and the Mac mini can't use), so editing
`requirements-edge.txt` no longer re-downloads torch. On an NVIDIA GPU host build with
`TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130 docker compose build edge-analyzer`. `.dockerignore` keeps
`data/` and `.git` out of the build context. YOLO weights are cached in `models/` (`perception.model_name:
models/yolo26s.pt`, the small model: as accurate as medium on our footage and 2.3x faster, see
`docs/models/model-benchmark.md`), so they download once rather than on every container start.

### 2d. Tracking & Queue Tuning (`configs/pipeline.yaml`)
- **`perception.confidence_threshold` / `tracking.track_thresh`** -- two-stage (ByteTrack-style)
  confidence matching. The detector is deliberately run at a *low* confidence floor
  (`confidence_threshold`); detections between that floor and `track_thresh` can extend a track
  that already exists (recovering partially-occluded people) but can never start a new one, so
  noisy low-confidence boxes can't spawn phantom identities. Raise `confidence_threshold` toward
  `track_thresh` to disable the low-confidence recovery entirely (the old single-threshold
  behaviour).
- **`tracking.stationary_policy`** -- `"tag"` (default) returns people standing still (e.g.
  queueing) with `is_stationary: true` so zones/queues count them; `"suppress"` drops them from
  every metric entirely, for a specific camera with a known cardboard-cutout/mannequin
  false-positive problem.
- **`analytics.zone_exit_grace_seconds`** -- how long a track can be briefly missing from a
  dwell/queue zone (a dropped detection, momentary occlusion) before it's actually counted as
  having left. Too low and a queue count flickers on every missed frame; too high and someone who
  actually left stays counted for a while.
- **`analytics.staff_min_seconds_in_zone`** -- how long someone must stand inside a **staff zone**
  (drawn with "Draw Staff Zone" in the Calibration Studio, e.g. behind the counter) before they're
  tagged staff and excluded from all customer metrics. The tag sticks to that track after they
  leave the zone. See `docs/product/metrics.md` §9 for exactly what's excluded and the limitations.
- **`analytics.heatmap_write_seconds`** -- how often the edge re-renders each camera's floor heatmap
  (where customers spend time; dashboard **Heatmap** tab). `scripts/dev-tools/render_heatmap.py` renders a
  whole-clip heatmap offline. See `docs/product/metrics.md` §10.

See `docs/performance/recorded-run-analysis.md` §10 for the evidence behind these defaults, and
`docs/models/id-switch-detector.md` for measuring tracking quality (suspected ID switches) on any clip.

### 2e. Securing the API (optional)
Every `/api/v1/*` endpoint is open by default -- fine for a closed/trusted network, not for a port
exposed to the internet. Set `EDGESIGHT_API_KEY` (same value on `edge-analyzer` and
`cloud-dashboard`, e.g. in a `.env` file next to `docker-compose.yml`) to require an `X-API-Key`
header on every **state-changing** call (telemetry ingestion, camera source/calibration writes,
metrics reset). Read endpoints (live counts, history, the video stream/snapshots) stay open,
matching the dashboard's own access -- this is a shared-secret barrier against unauthenticated
internet scanners hitting an exposed port, not a substitute for real per-user login. RTSP
credentials embedded in a camera's `source` are always masked in every API response regardless of
whether a key is set.

### 3. Running Natively (Without Docker)
```bash
# 1. Install dependencies
pip install -r requirements-edge.txt
pip install -r requirements-dashboard.txt

# 2. Run unit tests
python -m unittest discover tests

# 3. Start Cloud Receiver API & Dashboard
uvicorn server.app:app --port 8000 &
streamlit run server/dashboard.py --server.port 8501 &

# 4. Start Edge Analytics Engine
python scripts/run_edge.py
```

---

## 🎯 Key Retail Metrics & Algorithms

High-level summary below; **[docs/product/metrics.md](docs/product/metrics.md) is the exact, code-grounded
reference** for how each number is actually computed today (formulas, gotchas, and what resets
to zero when) — read that before trying to validate or debug a specific number.

| Metric | Computation Methodology | Business Impact |
|---|---|---|
| **Footfall (In / Out)** | Bidirectional vector tripwire intersection across a drawn line, with directional hysteresis and per-track lifetime deduping (each track can only cross a given tripwire once). | Accurate customer traffic counts; staffing scheduling. |
| **Store Occupancy** | With a tripwire configured: running total $\max(0, \sum \text{In} - \sum \text{Out})$ since the tripwire was last (re)calibrated. Without one: a raw live count of currently-active tracks. No decay of any kind. | Capacity safety compliance and shopper density analysis. |
| **Queue Length & Wait Time** | Tracks inside a `queue`-type polygon whose continuous dwell there is $\geq 5\text{s}$; rolling average of completed queue dwells as a fallback when the queue is momentarily empty. | Eliminates cart abandonment; triggers cashier reinforcement alerts. |
| **Zone Dwell & Heatmaps** | Point-in-polygon containment checks (foot position) logging entry/exit timestamps, with a short exit-grace period so one missed detection doesn't truncate a dwell. | Evaluates promotional display and endcap engagement. |
| **Store Flow & Turnover** | Net shopper retention $\frac{\text{Current Occupancy}}{\text{Total Entries}}$ and hourly flow velocity. | Optimizes store floor layout, merchandise placement, and staff rostering. |

---

## 🔒 Privacy & Regulatory Compliance (DPDP Act Ready)

* **No Biometrics:** No facial recognition, emotion tracking, or biometric embeddings.
* **Ephemeral In-Memory Frames:** Video frames exist exclusively in volatile memory during inference and are discarded immediately.
* **Zero Video Transmission:** Only numerical aggregate metrics (e.g. `{"visitors": 14, "occupancy": 8}`) leave the edge appliance.
* **Encrypted Communication:** TLS 1.3 encryption for cloud sync and local FileVault disk encryption.

---
