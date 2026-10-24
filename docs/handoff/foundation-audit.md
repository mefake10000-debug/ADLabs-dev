# Foundation audit and release handoff

**Observed:** 2026-10-24, with branch state rechecked 2026-10-25. **Destination:** `mefake10000-debug/ADLabs-dev`. **Local review branch:** `consolidate/adlabs-final-review`. **Base:** `5de866f0e4adfb88472a0bf48bb8744722257b8f`, the verified `mefake/integration` baseline. The integration is committed locally; the remote branch is still absent because Git transport could not resolve `github.com`. No default-branch ref was changed.

## Integration overview

The candidate branch is based on the destination's `mefake/integration` commit, not on a Git merge from Raj's separate clone. Raj's source `main` is `3476e4465d48110d559e46bd765cb5f0505b0f51`; the inspected source branch was `ml/dataset-research-train-eval` at `20c0b66bba6ec58abdbfb6671801f7cfe5a38386`. No common ancestry or complete file-by-file code port from Raj `main` has been established. Key source files differ from the candidate. The text-only evaluation report and selected reviewed patterns are included, but this handoff must not be read as proof that all candidate EdgeSight code derives from Raj's foundation.

The website package is under `website/` with its App Router in `website/app/`. It uses versioned HTTP APIs and imports no Python model code or weights. Local processing control is only enabled for a same-origin development dashboard on loopback; hosted Vercel cannot control a store’s localhost.

Processing is OFF by default. Docker starts the EdgeSight API/dashboard and a small supervisor. The supervisor does not import CV code or load weights; an authenticated Start accepts only configured camera IDs and launches the worker. Model paths are mounted read-only. The worker reports RUNNING after its first decoded frame. Stop terminates the worker, keeps historical rollups, and labels current live state OFF/stale. No Docker socket or arbitrary command interface is used.

## Validation

Current exact results are maintained in [`final-consolidation-status.md`](final-consolidation-status.md). At last run, EdgeSight discovery passed 263 tests with 6 environment/optional-dependency skips; website Node tests passed 15/15, lint passed, and the Webpack production build passed. Compose syntax validation passed. Docker daemon access was denied, so no actual image, container, restart, idle CPU, live worker, model-load, or FPS result exists.

## Security and data limits

- The website telemetry route requires a server ingest key. Production live reads remain unavailable until user identity and tenant/store authorization are implemented.
- Existing EdgeSight telemetry/read APIs do not provide tenant isolation. Public customer data and remote device control are blocked until server-enforced access control exists.
- Model weights were not added or loaded in this review. Dataset labels were not independently reviewed. No training or accuracy score is claimed.
- The destination’s inherited history contains `data/sample_videos/entrance_sample.mp4` and historical frame derivatives. The branch tree excludes sample footage and the source manifest marks the unknown-origin clip excluded, but the whole reachable branch history is not media-free.
- The original source clones, dirty checkouts, recovery refs, source video, and Nuclear Quince feature worktree remain preserved. No Nuclear Quince branch deletion has occurred.

See [`consolidation-manifest.md`](consolidation-manifest.md) for source-to-destination scope and [`branch-inventory.md`](branch-inventory.md) for the 26-branch GitHub comparison and discussion inventory.
