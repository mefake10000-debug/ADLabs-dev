# Runtime hardening and pilot acceptance

This change strengthens the existing edge + API + portal deployment. It does not establish field accuracy, an inference-FPS guarantee, or unattended multi-store readiness.

## Delivery contract

New edge records receive a persistent random `record_id` at creation. Existing rows receive IDs during database migration. IDs survive process restarts and distinguish separate events even when their timestamps and counts match.

The receiver deduplicates by store, device, channel and record ID. A metric insert and its receipt commit in the same transaction. Repeating an accepted record acknowledges it without inserting it again; reusing its identity with different content returns 409 and rolls back the whole batch. Responses acknowledge `accepted_record_ids`. The exporter marks only acknowledged records exported. A new edge refuses to discard durable records when talking to an old receiver without acknowledgements: upgrade the receiver first. Legacy records without IDs remain accepted, but cannot guarantee deduplication.

Configured cloud and local endpoints are **ordered fallback destinations**: the first receiver acknowledging delivery owns that record. They are not replicated destinations. If both need independent copies, use separate outbox delivery states per destination before enabling that topology.

Metrics reset deliberately clears visible rollups/events, while keeping receipts. Old retries therefore cannot repopulate reset metrics. Recovery/reimport after an intentional reset requires an explicit administrative migration; do not delete receipts casually. Product history has its existing separate lifecycle.

## Access configuration

For a deployment accessible beyond a trusted local machine, set these environment variables in both the API and portal, using a secret manager or ignored environment files:

- `EDGESIGHT_SECURE_MODE=1`
- `EDGESIGHT_OPERATOR_USER` and `EDGESIGHT_OPERATOR_PASSWORD`: administrator login.
- `EDGESIGHT_API_KEY`: device ingestion secret, also set on the edge worker.
- Optional `EDGESIGHT_VIEWER_USER` and `EDGESIGHT_VIEWER_PASSWORD`: read-only login, distinct from the administrator.

Serve the portal and any directly reachable API over HTTPS. Secure mode fails closed if required settings are missing. `/health` remains an unauthenticated minimal liveness check; other routes require operator credentials. Device POST routes for telemetry and registration accept the device key. A device key does not grant operator control when operator login is enabled. Successful operator changes record actor, method, path, status and time in `operator_audit`; request bodies and passwords are excluded.

HTTP Basic is a small-install access mechanism. It has no per-person account lifecycle, MFA, password recovery or brute-force rate limiting. Use an identity-aware reverse proxy for those requirements; do not expose unprotected alternate origins. Leave the direct Streamlit port private or disabled: it is a legacy operations surface and is not covered by the FastAPI or Next.js middleware. Bind Docker API/Streamlit host ports to loopback or enforce equivalent network controls before deployment. Environment changes require rebuilding/restarting the applicable service; this work does not change running services or create passwords for you.

The browser no longer receives the device secret in HTML. For older API-key-only configurations, use the portal's same-origin calibration/API routes, which add the key server-side. Direct API-origin Calibration Studio writes require operator credentials; configure them before relying on that workflow. Legacy trusted-local mode without credentials remains available for development.

The portal authenticates incoming requests and forwards operator identity to FastAPI server-side. The `/api/v1/*` streaming proxy preserves Basic login for video and snapshots. Both services reject foreign-origin browser mutations. Keep configured CORS origins limited to trusted portal origins.

## Storage and health

The edge outbox uses WAL with a 10-second SQLite busy timeout. Export-loop maintenance runs at most once per hour and removes only acknowledged records older than seven days, plus old camera-health history. Pending telemetry is never automatically discarded. Monitor disk capacity: long outages can still fill storage. `LocalBuffer.backlog_stats()` reports pending count and oldest timestamp; maintenance does not promise to shrink the allocated SQLite file immediately. Back up SQLite using its backup API, or stop writers before copying; a live WAL database cannot be backed up safely by copying only its main file.

`/health` means the API responds. `/ready` evaluates the newest camera snapshot, not the store summary: frame age at most 15 seconds, a positive reported inference rate, writable API database, and at least 256 MiB free disk. This is readiness of the latest active camera; it does not certify all configured cameras or model accuracy. Missing, stale or invalid timestamps never become a measured zero. The portal Model Health page displays these reasons independently of API connectivity.

## Evaluation

Keep reviewed person-box annotations and detector predictions outside Git. Both JSON files use:

```json
{"frames": [{"frame_id": "001", "boxes": [[10, 20, 80, 160]]}, {"frame_id": "002", "boxes": []}]}
```

Both files must cover exactly the same frames, including empty ones. Run from the EdgeSight repository:

```sh
python -m src.evaluation --labels /private/path/labels.json \
  --predictions /private/path/predictions.json --model YOLO26n \
  --clip entrance-v1 --config-id pilot-v1 --dataset entrance-reviewed-v1 \
  --output data/storage/model-evaluation.json
```

Point `MODEL_EVALUATION_PATH` on the API at the generated report (using the matching in-container path). This calculates precision, recall, F1 and per-frame person-count MAE with one-to-one box matching at IoU 0.5. It records source-file hashes and provenance. It does not measure tripwire errors, track switches, queue wait accuracy or real-world population bias; evaluate those separately. A detector confidence score is not an accuracy measurement.

Sample bright/dim scenes, busy/empty entrances, occlusion, groups, staff movement and people turning around. Keep a held-out set. Agree acceptance thresholds from the store's business needs before tuning. Reports expire under the existing seven-day freshness rule.

## Performance and recovery acceptance

1. Establish a one-camera detection/tracking baseline with optional enrichment disabled. Record device, backend, model and configuration hashes, input FPS/resolution, inference FPS, frame age, dropped frames, CPU/memory and count errors.
2. Add each enrichment individually on the same footage/device. Protect detection/tracking first. Never treat interpolated display frames as inference. Keep the current fixed inference cadence until labeled crossing/queue tests justify a different scheduler.
3. Compare native accelerator and container CPU runs using identical footage and accuracy checks. Select hardware only after the required camera count meets the agreed accuracy/latency budget under sustained load.
4. Disconnect delivery, generate events, restart the worker, restore delivery and verify totals against the edge records. Simulate a lost receiver response and verify retries do not increase totals twice.
5. Disconnect/reconnect a camera, restart the API, and use a disposable test volume to simulate low disk. Check readiness transitions, pending-record preservation and recovery. Do not fill a production device to test this.
6. Preserve database/config backups and the prior software revision before upgrades. Rolling upgrades are receiver first, edge second, then portal. Downgrades must be evaluated against migrated databases.

Further work requiring field inputs: human ground truth, inference hardware selection, sustained all-camera benchmarks, long-duration disk/outage tests, and independent validation of queue/staff/product signals. The large pipeline remains an incremental refactoring target; this pass removes a shadowed method without a broad behavior-changing rewrite.
