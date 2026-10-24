# Docker services and safe startup

| Service | Default startup | Purpose |
|---|---|---|
| `cloud-dashboard` | Starts by default; host ports bind to `127.0.0.1` | FastAPI telemetry/control API and Streamlit operations UI; does not load CV models. |
| `edge-analyzer` | Starts by default as a model-free supervisor | Reports lifecycle state and starts one worker only after an authenticated Start request. Weights and source code are mounted read-only. |
| `rtsp-simulator` | Disabled unless `--profile simulator` is selected | Optional synthetic RTSP fixture; does not start inference. |

The dashboard API and operations UI publish only on loopback. The supervisor listens on the private Compose network at port 8001; it is not published to the host. The stack does not mount `/var/run/docker.sock` or auto-start a worker. `edge-analyzer` restarts the supervisor after machine restart; supervisor initialization marks prior live state stale and stays OFF. A Stop sends SIGTERM to the child and waits up to the configured timeout before a forced kill. Historical SQLite rollups are never removed by lifecycle control.

Both `EDGESIGHT_API_KEY` and `PROCESSING_CONTROL_KEY` are required by Compose. The first protects processing-control requests to the local API; the second protects the private supervisor channel. The website never receives the internal supervisor key.

Docker uses the CPU-only PyTorch wheel by default. Docker Desktop on macOS does not expose MPS/Metal/Neural Engine to a Linux container; no GPU acceleration is claimed. The daemon was unavailable during this handoff, so image build, actual container restart, and idle CPU could not be measured here.

Weights are excluded from Docker build context and Git, then mounted read-only. The supervisor does not read model contents; the worker process opens weights only after Start.
