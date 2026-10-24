# Troubleshooting

| What you see | What it means | Safe next step |
|---|---|---|
| Compose asks for `EDGESIGHT_API_KEY` or `PROCESSING_CONTROL_KEY` | Required control secrets are not configured. | Copy `.env.example` to `.env`, generate two separate random values, and restart Compose. Never commit `.env`. |
| Supervisor is OFF after Docker restart | Expected behavior; processing never auto-starts. | Select an enabled camera and press Start. |
| Start says camera is unknown/disabled | The ID is not enabled in `configs/cameras.yaml`. | Select an enabled camera from the local dashboard; do not pass a source URL through the control API. |
| Start reports a missing video file | Configured file path is absent inside the container. | Check the source path and read-only `data/sample_videos` mount. |
| State becomes ERROR during startup | Worker exited while loading configuration or models. | Read the worker logs and status error. Provide the required existing weights before retrying; there is no automatic retry loop. |
| State RUNNING but video freshness is false | Worker process started, but a recent frame has not reached the pipeline. | Check the camera source, decoder/codec, network reachability, and camera-side stream. |
| Site says controls are local-only or unavailable | Next.js is hosted/production, the API key is missing, or EdgeSight is not reachable at loopback. | Use the local Next.js development dashboard on the same computer as the local EdgeSight API. |
| Historical values remain after Stop | Expected; rollups are retained and the current live snapshot is marked stale. | Use timestamps/freshness before treating the last values as current. |

Do not “fix” missing source/model data by filling business metrics with zero or sample data.
