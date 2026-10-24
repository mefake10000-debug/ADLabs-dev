# EdgeSight runtime and dashboard integration map

This document describes the checked-out repository branch, not an aspirational integration. It separates EdgeSight implementation from the independent Next.js website.

## Current data/control path

```text
selected camera IDs
  → authenticated FastAPI /api/v1/processing/start
  → private model-free supervisor (src/runtime/supervisor.py)
  → child worker (src/main.py)
  → frame decoder → person detector/tracker → zone/queue/rollup analytics
  → local state and aggregate telemetry
  → versioned API response
  → independent website local-development control panel
```

Opening the website or starting Docker does not run the worker. The default supervisor state is OFF. The website has separate demo analytics; the new control panel reports processing state and camera freshness only. It does not bind demo charts to live measurements.

## Exact source locations

| Concern | Source of truth |
|---|---|
| Camera inputs, enabled state, zones/tripwires | `configs/cameras.yaml` |
| Detector/enrichment flags, weights paths, cadence | `configs/pipeline.yaml` |
| Worker lifecycle and internal authorization | `src/runtime/supervisor.py` |
| Pipeline/model initialization and analytics | `src/main.py`, `src/perception/`, `src/analytics/` |
| API control, telemetry, configuration | `server/app.py` |
| Docker service behavior and mounts | `docker-compose.yml`, `docker/Dockerfile.edge`, `docker/Dockerfile.dashboard`, `docker/Dockerfile.simulator` |
| Website control client and same-origin API | `src/lib/processing-control.ts`, `app/api/processing/`, `src/app/ProcessingControl.tsx` in the separate website repository |

## Data and freshness

The EdgeSight worker writes `data/storage/state/live.json` atomically. Camera frames are tagged with a last-frame time; runtime status becomes fresh only when selected cameras have recent frames. On Stop/restart, counts and rollups remain stored, but `processing.state` becomes OFF and the live snapshot is marked stale. Local annotated preview frames/heatmaps may exist under `data/storage`; raw-frame writing is disabled by default. Telemetry sent to cloud contains aggregate rollups/events, not video.

The website dashboard still contains sample data marked as preview/demo. Only processing status and configured camera names are read from EdgeSight through the versioned API. No model code, weights, or Docker control is imported by the website.

## Models and limitations

See [`models-runtime.md`](models-runtime.md). Configured model flags are not evidence of loaded weights or inference. This checkout has no model artifacts; actual model inference, FPS, CPU use, and accuracy are unverified. OSNet is registered without an active matching consumer; CLIP and shelf YOLOE are disabled. Ground-truth JSON files exist, but the three evaluation reports are missing.

## Security boundary

Processing control requires separate API and internal supervisor keys. Docker publishes the API/UI only on loopback and does not mount the Docker socket. EdgeSight relays fixed status/start/stop requests to its private supervisor service; it does not accept arbitrary commands. The website proxy is enabled only in local Next.js development and targets a loopback EdgeSight API; a hosted site cannot control an edge machine. Existing read APIs and telemetry storage do not provide real user identity or tenant isolation. Public customer data/remote control remains blocked until those server-enforced boundaries and cross-tenant tests exist.

## Verification limits

Unit tests cover lifecycle state transitions, camera allow-lists, secret checks, stale marking, and model-free supervisor imports. Docker daemon access was unavailable for container restart/idle CPU tests. Only the local test footage and available decoder metadata may be checked; public internet clips are neither saved nor required for this handoff.
