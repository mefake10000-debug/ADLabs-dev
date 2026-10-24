# Data, privacy, and access boundary

- Camera sources and inference run on the local EdgeSight node after explicit Start. Docker and the site do not automatically open video.
- The EdgeSight worker can persist aggregate rollups in local SQLite and uploads aggregate telemetry. Configured raw frame output is off; the local dashboard may store annotated preview frames and heatmaps under `data/storage/`. Those files stay on the local volume unless an operator separately copies them.
- The website database routes accept aggregate telemetry; this implementation adds no video upload or cloud video job. Do not send public test clips to a cloud model, and do not save public clips or derived frames.
- Processing control requires `EDGESIGHT_API_KEY`; the internal supervisor channel separately requires `PROCESSING_CONTROL_KEY`. Compose publishes the API/UI on loopback and keeps supervisor port 8001 private. No Docker socket is mounted.
- Existing non-control GET endpoints remain open to local callers, and the system has no real user login, organization/store authorization, or multi-tenant boundary. A shared API key is not a tenant security system. Public customer data or remote controls are a release blocker until identity and server-enforced tenant/device scope are implemented and tested.
- The Next.js control proxy is available only in local development and targets a loopback EdgeSight API. A hosted website cannot start a store edge process.
