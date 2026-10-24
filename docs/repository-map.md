# Repository map for a reviewer

Keep business/product language and technical implementation in separate areas. The product overview belongs in `product.md`; runtime setup and operator steps belong in `README.md` and `docs/`. Model behavior belongs in `src/perception/` and `docs/models-runtime.md`; pipeline orchestration in `src/main.py`; lifecycle in `src/runtime/`; HTTP and telemetry in `server/`; camera and model settings in `configs/`; tests in `tests/`; container definitions in `docker/` and `docker-compose.yml`.

| Path | Role | Review entry point |
|---|---|---|
| `src/ingestion/` | Opens configured sources and buffers the newest frames. | `stream_reader.py` |
| `src/perception/` | Detector, tracker, model registry, and enrichment adapters. | `detector.py`, `tracker.py`, `registry.py` |
| `src/analytics/` | Tripwire, zone, queue, dwell, attention, and product aggregate calculations. | `src/main.py` calls these consumers. |
| `src/runtime/` | OFF-by-default supervisor; process lifecycle only. | `supervisor.py`, folder README |
| `server/` | FastAPI telemetry/config/control API and Streamlit operations page. | `app.py`, `dashboard.py` |
| `configs/` | Camera sources/zones and pipeline/model policy. | `cameras.yaml`, `pipeline.yaml` |
| `docker/`, root Compose file | Container startup, ports, mounts, and profiles. | `docker-compose.yml` |
| `scripts/`, `tests/` | Operator/benchmark utilities and regression checks. | Inspect individual script purpose before running it on real footage. |
| `docs/` | Architecture, performance, model, data/security, and handoff guides. | This map and `agentic-store-os.md`. |

This map describes the committed source tree. Local model weights, client videos, and persistent data are not part of Git.
