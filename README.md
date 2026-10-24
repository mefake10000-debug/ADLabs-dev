# AD Labs EdgeSight

EdgeSight processes selected store-camera streams on the edge device and publishes aggregate analytics. Video processing is **OFF by default**. Starting Docker, opening a dashboard, restarting the machine, or receiving telemetry does not start a decoder or load model weights.

Start with [`product.md`](product.md) for the product idea and this README for safe operation. Detailed operator and reviewer guides are in [`docs/processing.md`](docs/processing.md), [`docs/docker-run.md`](docs/docker-run.md), and [`docs/repository-map.md`](docs/repository-map.md).

## What is in this repository

| Path | Purpose |
|---|---|
| `src/ingestion/` | Opens configured camera/video sources and bounds pending frames. |
| `src/perception/` | Person detection, tracking, model registry, and optional enrichment adapters. |
| `src/analytics/` | Converts tracked observations into tripwire, zone, queue, dwell, and aggregate signals. |
| `src/runtime/` | Model-free OFF-by-default process supervisor. |
| `server/` | FastAPI telemetry/config/control API and Streamlit operations UI. |
| `configs/` | Camera sources/zones and pipeline/model settings. |
| `docker/`, `docker-compose.yml` | Container startup, loopback ports, read-only mounts, and test profile. |
| `scripts/`, `tests/` | Explicit operator/benchmark tools and regression checks. |
| `docs/` | Architecture, model, performance, privacy, operating, and handoff notes. |
| `data/` | Local sample clips and runtime storage; do not commit customer footage or generated state. |

Business/product narrative stays in `product.md`. Model engineering and operations guidance stays in `docs/` and the corresponding source folders.

## Safe local setup

1. Copy `.env.example` to `.env` and replace both placeholders with different random secrets. Do not commit `.env`.
2. Start the local API, supervisor, and operations UI:

   ```sh
   docker compose up --build -d
   ```

   The dashboard/API ports bind to `127.0.0.1`. The private supervisor port is not published. The RTSP simulator is not started by default.
3. The supervisor reports **OFF** and does not load CV/model code. The model weights directory is mounted read-only; only the worker started by an authenticated request reads weights.
4. Use the local dashboard or the authenticated API to start one or more configured camera IDs. Read [`docs/processing.md`](docs/processing.md) for exact steps and CLI examples.
5. Stop processing explicitly when done. Stop preserves historical rollups and marks the current live snapshot **OFF/stale**.

For simulator-only testing, use `docker compose --profile simulator up --build -d`. Starting the simulator does not start inference.

## Processing states

- **OFF** — no worker, decoder, or loaded models.
- **STARTING** — configuration and resources are checked; the child loads required models.
- **RUNNING** — only selected configured cameras are processed. Status reports worker state and recent-frame freshness separately.
- **STOPPING** — new frames stop; the worker is terminated and its model memory is released.
- **ERROR** — startup/worker failure is visible with a reason; there is no aggressive automatic retry.

The native CLI also requires explicit camera scope:

```sh
python scripts/run_edge.py --camera-ids cam_entrance_01
```

## Models and measured data

The config currently requests a person detector and slow-tier pose, face, age/gender, product-interest, and OSNet ReID capabilities. CLIP and shelf YOLOE are disabled. OSNet has no inference consumer in the current pipeline. These flags do not prove that weights exist or a model is running. This checkout contains no model weights, so actual model loading and FPS are unverified; the required detector fails closed if missing. See [`docs/models-runtime.md`](docs/models-runtime.md) for artifact paths and use-case status.

Counts and analytics must come from worker observations. A missing source, model, or camera frame is unavailable/stale—not a measured zero. The existing website analytics are explicitly sample/demo data; starting a worker does not convert those charts into live readings.

## API and access boundary

Versioned EdgeSight API: `GET /api/v1/processing/status`, `POST /api/v1/processing/start`, and `POST /api/v1/processing/stop`. All processing-control calls require `X-API-Key`; the supervisor channel has a separate required key. Start accepts configured camera IDs only and does not accept commands or source URLs. No Docker socket is used.

The website’s processing proxy works only in local Next.js development and connects to a loopback EdgeSight API. A hosted website cannot control a store edge machine. The current application has no real user login or tenant authorization; do not expose client data or remote controls until server-enforced identity and store/device scope are implemented. See [`docs/data-security.md`](docs/data-security.md).

## Verification

- EdgeSight: `python3 -m unittest discover tests -v`
- Website: `npm test`, `npm run lint`, `npm run build`
- Docker configuration: `EDGESIGHT_API_KEY=test-owner PROCESSING_CONTROL_KEY=test-internal docker compose config --quiet`

A test result proves only what actually ran. Missing dependencies, Docker daemon, model weights, valid annotations, or suitable hardware must be reported as limitations rather than inferred as a pass.

## Website package

The Nuclear Quince Next.js app lives in [`website/`](website/README.md). Its App Router is `website/app/`; it does not load Python models or model weights. The dashboard communicates with EdgeSight through the versioned API. Local Start/Stop controls work only when the dashboard and EdgeSight run on the same computer; a hosted site cannot start a store edge machine.

Run the website separately from EdgeSight:

```sh
cd website
npm ci
npm run dev
```

Opening the website does not start video processing. Processing remains OFF until an authorized local Start request. Current demo analytics stay labeled as sample data. The telemetry database integration is not tenant-authorized; do not expose client data or use it as a production multi-tenant service. See [`docs/handoff/consolidation-manifest.md`](docs/handoff/consolidation-manifest.md) for source commits, migration scope, and validation limits.
