# AD Labs EdgeSight

> **On-Premise Retail Edge AI & Computer Vision Analytics Platform for Existing CCTV Infrastructure**

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

The platform is fully containerized into 3 modular services:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DOCKER COMPOSE STACK                             │
│                                                                             │
│  ┌───────────────────────┐             ┌─────────────────────────────────┐  │
│  │    rtsp-simulator     │             │          edge-analyzer          │  │
│  │                       │             │                                 │  │
│  │  • MediaMTX Server    │  RTSP       │  • StreamReader (Multi-threaded)│  │
│  │  • FFmpeg Stream Loop │────────────►│  • YOLO Person Detector (FP16)  │  │
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
   * Runs YOLOv8/v11 person detection (targeting class 0) with automatic hardware acceleration (Core ML / MPS on Apple Silicon, CUDA, or AVX CPU).
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
| Benchmark / any one-off script | `docker compose run --rm --no-deps edge-analyzer python scripts/benchmark_tracking.py …` (`--no-deps` skips starting the other services) |
| `server/` API code | `docker compose restart cloud-dashboard` (Streamlit hot-reloads by itself; uvicorn doesn't) |
| `docker-compose.yml` | `docker compose up -d` (recreates only what changed) |
| `requirements-*.txt` or `docker/Dockerfile.*` | `docker compose build <service>` — the **only** case that needs a build |

Build-size notes: the edge image installs **CPU-only PyTorch** in its own cached layer (~2.8GB total instead of ~10GB;
the default Linux wheel bundles ~4GB of CUDA libraries that Docker Desktop and the Mac mini can't use), so editing
`requirements-edge.txt` no longer re-downloads torch. On an NVIDIA GPU host build with
`TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130 docker compose build edge-analyzer`. `.dockerignore` keeps
`data/` and `.git` out of the build context. YOLO weights are cached in `models/` (`perception.model_name:
models/yolo26s.pt`, the small model: as accurate as medium on our footage and 2.3x faster, see
`docs/model-benchmark.md`), so they download once rather than on every container start.

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
  leave the zone. See `docs/metrics.md` §9 for exactly what's excluded and the limitations.
- **`analytics.heatmap_write_seconds`** -- how often the edge re-renders each camera's floor heatmap
  (where customers spend time; dashboard **Heatmap** tab). `scripts/render_heatmap.py` renders a
  whole-clip heatmap offline. See `docs/metrics.md` §10.

See `docs/recorded-run-analysis.md` §10 for the evidence behind these defaults, and
`docs/id-switch-detector.md` for measuring tracking quality (suspected ID switches) on any clip.

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

High-level summary below; **[docs/metrics.md](docs/metrics.md) is the exact, code-grounded
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

## 📂 Repository Structure

```
adlabs-edgesight/
├── docker-compose.yml              # 3-service orchestration (simulator, edge, dashboard)
├── configs/
│   ├── cameras.yaml               # Camera stream URLs, tripwires, queue polygons
│   └── pipeline.yaml              # Detection confidence, tracking params, rollup intervals
├── data/
│   ├── sample_videos/             # Sample retail test clips (entrance, checkout)
│   └── storage/                   # Persisted SQLite databases
├── docker/
│   ├── Dockerfile.edge            # Python 3.11 edge CV analyzer image
│   ├── Dockerfile.simulator       # MediaMTX + FFmpeg RTSP streaming image
│   ├── Dockerfile.dashboard       # FastAPI + Streamlit analytics dashboard image
│   └── simulator_entrypoint.sh    # Simulator stream broadcaster
├── src/                           # Edge Processing Engine
│   ├── main.py                    # Edge pipeline coordinator
│   ├── ingestion/
│   │   ├── stream_reader.py       # Threaded RTSP & video reader with reconnect logic
│   │   └── frame_buffer.py        # Thread-safe ring buffer with drop-oldest policy
│   ├── perception/
│   │   ├── detector.py            # YOLOv8/v11 person detector (MPS/CUDA/CPU)
│   │   └── tracker.py             # IoU ByteTrack multi-object tracking
│   ├── analytics/
│   │   ├── tripwire.py            # Bidirectional entrance/exit line counter
│   │   ├── zones.py               # Polygon dwell time & occupancy calculator
│   │   └── queue_analyzer.py      # Checkout queue wait-time & congestion alert engine
│   ├── storage/
│   │   ├── local_buffer.py        # Local SQLite database manager
│   │   └── schema.sql             # Edge telemetry schema
│   ├── telemetry/
│   │   ├── exporter.py            # Cloud telemetry syncer with retry buffer
│   │   └── health.py              # Uptime and resource health telemetry
│   └── visualizer/
│       └── debug_overlay.py       # OpenCV HUD for calibration and inspection
├── server/                        # Cloud Receiver & Dashboard Service
│   ├── app.py                     # FastAPI ingestion endpoint
│   └── dashboard.py               # Streamlit real-time operations dashboard
├── scripts/
│   ├── generate_sample_video.py   # Procedural retail video generator
│   ├── benchmark_performance.py   # Hardware inference benchmark tool
│   └── run_edge.py                # Standalone native runner
├── tests/
│   └── test_pipeline_core.py      # Automated unit tests
├── requirements-edge.txt          # Python dependencies for edge engine
├── requirements-dashboard.txt     # Python dependencies for dashboard service
├── product.md                     # Comprehensive market research & pilot strategy
└── README.md                      # Project documentation (this file)
```
