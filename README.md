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

### 3. Running Natively (Without Docker)
```bash
# 1. Install dependencies
pip install -r requirements-edge.txt
pip install -r requirements-dashboard.txt

# 2. Run unit tests
python -m unittest tests/test_pipeline_core.py

# 3. Start Cloud Receiver API & Dashboard
uvicorn server.app:app --port 8000 &
streamlit run server/dashboard.py --server.port 8501 &

# 4. Start Edge Analytics Engine
python scripts/run_edge.py
```

---

## 🎯 Key Retail Metrics & Algorithms

| Metric | Computation Methodology | Business Impact |
|---|---|---|
| **Footfall (In / Out)** | Bidirectional vector tripwire intersection across door threshold with directional hysteresis. | Accurate customer traffic counts; staffing scheduling. |
| **Store Occupancy** | Running differential $\max(0, \sum \text{In} - \sum \text{Out})$ calibrated with periodic decay. | Capacity safety compliance and shopper density analysis. |
| **Queue Length & Wait Time** | Stationary person clustering inside cashier polygon $> 5\text{s}$; rolling average dwell. | Eliminates cart abandonment; triggers cashier reinforcement alerts. |
| **Zone Dwell & Heatmaps** | Point-in-polygon containment checks logging entry and exit timestamps. | Evaluates promotional display and endcap engagement. |
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
