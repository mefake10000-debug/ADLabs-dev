# Website integration helpers

This folder contains typed API boundary and data helpers for the Next.js website. The processing-control helper calls only versioned EdgeSight HTTP endpoints from local Next.js development; it contains no Python/CV/model imports, model weights, or Docker client.

- `processing-control.ts` validates local-only requests, camera IDs, state labels, and the fixed API paths. Its server-side forwarder reads `EDGESIGHT_API_URL` and `EDGESIGHT_API_KEY` from server environment only.
- Read: same-origin browser requests and server-only local API settings. Write: HTTP requests to loopback EdgeSight and JSON status responses, never the secret.
- Test: `npm test`.
- Common errors: production mode is deliberately disabled; absent key/API or unavailable EdgeSight returns an explicit error instead of fabricated OFF/zero data.
