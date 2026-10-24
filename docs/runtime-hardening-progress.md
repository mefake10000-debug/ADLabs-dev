# Runtime hardening progress — 2026-10-25
Plan: docs/superpowers/plans/2026-10-25-runtime-hardening.md
Ruling: Work in existing non-main branches because user explicitly requested respective branches and current local runtime dependencies must be preserved.
Ruling: Execute inline under the user’s explicit implementation and push authorization; no additional plan approval requested.
Pre-flight: Task 1 record IDs feed receiver acknowledgements; Task 2 only prunes exported records; Task 3 portal forwards authenticated requests to the API.

Task 1: stable outbox identities, transactional receipts, partial acknowledgements, interruptible shutdown implemented; failure tests observed RED then GREEN.
Task 2: exported-only retention, WAL, read-only backlog and separate camera readiness implemented with stale/future/missing/low-disk coverage.
Task 3: API/portal administrator and viewer access, credential forwarding, CSRF checks, no embedded device key and operator change audit implemented.
Task 4: shadowed method removed; offline person-box evaluator and deployment/recovery guide added.
Independent review: identified camera/store readiness mismatch and direct-API CSRF; both reproduced with failing tests and fixed. Batch conflict rollback test passes.
Ruling: Metrics reset retains receipts deliberately to prevent old retries resurrecting reset counts; reimport needs an explicit migration. Cost if wrong: operators expecting replay after reset need that migration.
Ruling: Preserve API-key-only portal workflows using server-side proxy injection; direct API-origin Studio writes require operator credentials. Cost: legacy direct-origin users must configure login or use the portal.
Ruling: Keep essential inference scheduling and model defaults unchanged pending labeled field/hardware measurements. Cost: current CPU profile still cannot claim the requested inference rate.

Verification: final Python suite ran 262 tests, OK, 3 skipped. Portal suite 31/31 passed. Offline evaluator CLI produced a synthetic fixture report accepted by the dashboard reader. First portal production build passed; final build after readiness display refinement in progress.
Review: independent focused security/delivery review followed by author integration review. Staged-file scan: 58 EdgeSight and 17 portal files; no credential-token, private-key, database, model-weight or media matches. Unrelated local handoff documents and generated TypeScript cache excluded.
Deferred limitations: no field labels or hardware performance claim; HTTP Basic needs HTTPS and optional managed identity/rate limiting at the deployment gateway; legacy Streamlit must remain private; latest-camera readiness does not certify every camera; full pipeline decomposition remains incremental.
