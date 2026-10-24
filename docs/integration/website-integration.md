# Website and EdgeSight boundary

The Next.js application is in `website/`. EdgeSight remains the Python service in `src/` and `server/`. The two parts communicate through HTTP JSON APIs; the website does not import Python code or load model weights.

## Local routes and controls

| Purpose | Website route | EdgeSight route |
|---|---|---|
| List configured cameras | `/api/processing/cameras` | `GET /api/v1/config/cameras` |
| Read processing status | `/api/processing/status` | `GET /api/v1/processing/status` |
| Start selected cameras | `/api/processing/start` | `POST /api/v1/processing/start` |
| Stop processing | `/api/processing/stop` | `POST /api/v1/processing/stop` |
| Receive aggregate telemetry | `/api/v1/telemetry` | `POST /api/v1/telemetry` |

The processing controls are available only in local Next.js development. The proxy requires a same-origin loopback request, server-side `EDGESIGHT_API_KEY`, and a loopback EdgeSight API URL. It forwards only the fixed Start/Stop/Status payloads. EdgeSight validates camera IDs and forwards to the private supervisor using `PROCESSING_CONTROL_KEY`. The browser never receives that internal key.

Hosted Vercel cannot connect to a store computer’s `localhost`; these routes deliberately do not operate from production. Remote control requires a separate authenticated outbound device design and tenant/store authorization.

## Run locally

1. Copy `.env.example` to `.env`, replace both values with separate random keys, and keep the file untracked.
2. Validate and start the local EdgeSight API, dashboard, and OFF supervisor with `docker compose up --build -d`.
3. In `website/.env.local`, set `EDGESIGHT_API_URL=http://127.0.0.1:8000` and `EDGESIGHT_API_KEY` to the API key. Do not add the internal supervisor key to the website environment.
4. Start the local website from `website/` with `npm run dev -- --hostname 127.0.0.1`.
5. Select an enabled configured camera, then use Start. The page distinguishes service state from recent-frame freshness. Stop returns processing to OFF/stale while retaining historical rollups.

See [`docs/processing.md`](../processing.md), [`docs/docker-run.md`](../docker-run.md), and [`website/README.md`](../../website/README.md) for exact setup and recovery steps.

## Data and UI behavior

- The dashboard’s demo-marked charts remain sample illustrations. Starting EdgeSight does not silently convert them to live measurements.
- Missing values remain unavailable/null; a measured zero remains zero.
- The website telemetry ingest requires `EDGE_INGEST_KEY`. Production live reads remain disabled until tenant authorization is implemented.
- EdgeSight legacy telemetry reads do not provide tenant isolation. Do not expose client data publicly based on API keys alone.
- The website UI build and tests do not start Docker, decode video, or load a model.
