# Starting and stopping processing

## Default state: OFF

`docker compose up` starts a small supervisor and the telemetry/dashboard service. It does not start the RTSP simulator, open a camera/video source, import CV model code in the supervisor, or load weights. A health check reads status only. Restarting Docker or the machine returns the worker to OFF.

The local dashboard exposes **Start processing**, **Stop processing**, and **Refresh status**. Start validates the selected enabled camera IDs, source configuration, and existence of at least one required person-detector weight before starting one worker process. It does not reserve or benchmark CPU/RAM before startup. Model loading and decoding occur only in that child process. Status distinguishes OFF, STARTING, RUNNING, STOPPING, ERROR, and current-frame freshness. Stop closes the worker process, which releases model memory, and marks the current live snapshot OFF/stale while retaining database rollups.

There is currently no startup/readiness deadline. If model loading or source initialization hangs, status may remain STARTING; use **Stop processing** to terminate the worker and return to OFF, then inspect the worker logs before retrying. Automatic retry is disabled. A measured readiness budget and timeout recovery test remain future work.

## Local Docker setup

1. Copy `.env.example` to `.env` and replace both placeholders with different random values. `EDGESIGHT_API_KEY` protects the public-facing local control API; `PROCESSING_CONTROL_KEY` protects the private supervisor channel. Keep `.env` out of Git.
2. Start the stack with `docker compose up --build -d`. Ports 8000 and 8501 bind to loopback only. The supervisor listens on the private Compose network at port 8001 and is not published to the host.
3. For the Next.js local dashboard, run it in development mode with a local-only `.env.local` containing `EDGESIGHT_API_URL=http://127.0.0.1:8000` and the same `EDGESIGHT_API_KEY`. The UI routes are development-only and use the local EdgeSight API; hosted production sites cannot control a remote edge device.
4. Select one or more configured cameras and press **Start processing**. A worker start does not imply the camera is producing frames; wait for the freshness field to confirm recent frames.
5. Press **Stop processing** when the session ends. The UI reports OFF only after the child exits; prior counts remain visible as stale context.

The RTSP simulator is optional and is available only with the Compose `simulator` profile. Enabling the simulator does not start inference by itself.

## CLI fallback

With the local API running and `EDGESIGHT_API_KEY` available in the shell, an operator may use:

```sh
curl -H "X-API-Key: ${EDGESIGHT_API_KEY:?set EDGESIGHT_API_KEY}" http://127.0.0.1:8000/api/v1/processing/status
curl -X POST -H "X-API-Key: ${EDGESIGHT_API_KEY:?set EDGESIGHT_API_KEY}" -H 'Content-Type: application/json' \
  -d '{"camera_ids":["cam_entrance_01"]}' http://127.0.0.1:8000/api/v1/processing/start
curl -X POST -H "X-API-Key: ${EDGESIGHT_API_KEY:?set EDGESIGHT_API_KEY}" http://127.0.0.1:8000/api/v1/processing/stop
```

The native worker CLI also requires explicit scope: `python scripts/run_edge.py --camera-ids cam_entrance_01`. Never pass credentials in a shared terminal transcript.

## Limits

This is local single-store control, not multi-user or tenant authorization. Do not expose ports 8000/8501 or the supervisor port to the internet. A hosted website cannot reach a store’s loopback interface, and the website intentionally disables these routes outside local development.
