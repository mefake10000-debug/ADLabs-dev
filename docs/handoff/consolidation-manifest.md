# ADLabs-dev migration manifest

## Destination and current review state

Destination: `https://github.com/mefake10000-debug/ADLabs-dev`. The local remote-tracking refs for `mefake/integration` and `mefake/friend-review-v1` point to `5de866f0e4adfb88472a0bf48bb8744722257b8f`; GitHub metadata confirms `mefake/integration` is the default. The active local candidate is `consolidate/adlabs-final-review`, based directly on that commit. Its reviewed migration is committed locally but has not been pushed. A fresh `git ls-remote` check could not resolve GitHub, so current remote tip equality was not refreshed in this session.

The candidate is based on the destination’s shared history. The owner selected this delivery path knowing that the existing ancestor history contains `data/sample_videos/entrance_sample.mp4`. The current branch tree removes the sample footage; this does **not** make its complete reachable history media-free. No default or remote history was rewritten.

## Source-to-destination map

| Source | Branch/commit at inspection | Selected destination paths | Included work and evidence | Exclusions / preservation |
|---|---|---|---|---|
| Raj EdgeSight clone (`rajendrac3/ADLabs-dev`) | `ml/dataset-research-train-eval` at `20c0b66`; Raj `main` at `3476e4465d48110d559e46bd765cb5f0505b0f51`; dirty source checkout | `src/`, `server/`, `configs/`, `docker/`, `scripts/`, `tests/`, `docs/` | The source tree and its model/data audit were inspected. The candidate includes selected text-only evaluation records and reviewed runtime concepts, but exact code provenance for the candidate's larger runtime/API/model changes is not established as a port from Raj `main`; key tracked files differ by content. No history merge or shared ancestry is claimed. | No `.git`, full dirty checkout, local datasets, local model files, or unrelated pending work copied. Source clone is intact. Treat complete Raj-foundation integration as PARTIAL pending a file-level port map. |
| EdgeSight checkout (`mefake10000-debug/ADLabs-dev`) | `fps-optimization-enhance` at `5ee76eb6a76e5b8ee8dc54c42b99e06dbc135b97`; dirty with 58 status paths | Selected `src/`, `server/`, `configs/`, `docker/`, `scripts/`, `tests/`, `docs/` | Verified recent detector/tracker/overlay/runtime work and matching tests were selectively ported. The local supervisor, explicit camera scope, `FrameScheduler`, API relay, and regression fixes are verified by the candidate tests listed in [`final-consolidation-status.md`](final-consolidation-status.md). | Source working changes, local footage and generated `data/storage/live/` state remain in the original checkout. Host-specific untracked `local-runtime` profiles and a launcher with personal paths were excluded. |
| Nuclear Quince website clone (`mefake10000-debug/adlabs`) | `main` at `353663e3b43c76180fce4151a4ef2c3d686dbc87`; dirty with 12 status paths | `website/` | Website App Router, dashboard screens, static assets, typed processing client/routes, tests, and selected database/API support are kept as an independent Next.js package. The website is separate from Python/model code. | No nested `.git`, secrets, node modules, Next output, build caches, or unrelated pending files copied. Original clone and `main` remain intact. |
| Nuclear Quince feature worktree | `product/dashboard-foundation` at `67c948232747aeaa2153d40077631415169a69d8`; clean at inspection | `website/app/api/processing/`, `website/src/lib/`, `website/src/app/`, `website/tests/`, `website/docs/` | All 32 paths in its diff from Nuclear Quince `main` are present under `website/`; 29 match the source branch byte-for-byte and 3 are intentional adaptations (README, package.json, and demo-label regression test). Integrated website tests/lint/build pass. | Feature branch and worktree are preserved until the destination delivery is pushed and verified. |
| Earlier local consolidation worktree | `consolidate/adlabs-dev-review` at `a9323ca4f37dd5e2905e1c03b1df6b46b70499f7`; dirty | Reviewed text/config/source portions only | Used as a source snapshot and comparison point. | Worktree, dirty changes, and local recovery refs remain untouched. It is not the destination delivery branch. |

## Website/API contract

- Next.js package: `website/`; App Router: `website/app/`; presentation code: `website/src/app/`; API client: `website/src/lib/processing-control.ts`.
- Dashboard routes (`website/app/api/processing/`) are enabled only in local Next.js development. They accept a same-origin loopback dashboard request and a server-only `EDGESIGHT_API_KEY`; Vercel or another hosted site cannot reach the store computer’s loopback address.
- The EdgeSight API exposes fixed `GET /api/v1/processing/status`, `POST /api/v1/processing/start`, and `POST /api/v1/processing/stop` routes. It forwards fixed shapes to the private supervisor using `PROCESSING_CONTROL_KEY`; arbitrary command execution and Docker socket access are not used.
- EdgeSight API control requires configured API and supervisor keys. The Docker supervisor port is private to the Compose network; API and dashboard ports bind to loopback.
- Website telemetry ingestion requires `EDGE_INGEST_KEY`. Live telemetry reads remain unavailable in production until tenant authentication and store authorization exist. EdgeSight’s older read/ingest APIs are not a multi-tenant boundary. Public customer-data use is blocked.

## Media and local data exclusions

- All eight tracked sample MP4s in the destination working tree are removed from this candidate. `entrance_sample.mp4` has unknown provenance/license and is explicitly marked excluded in `data/sample_videos/SOURCES.md`.
- No video or image/frame derivative is included in the candidate tree. `entrance_sample.mp4` and its unknown-origin count annotation are excluded. Two approximate count-only JSON records for the documented Pexels clips remain under `scripts/benchmark/benchmark_ground_truth/`; they do not establish detection accuracy. The preserved source video and source checkouts have not been altered.
- Because the destination baseline already contains the clip and historical frame derivatives, they remain reachable through ancestors of the review branch. The final branch tree is checked separately; this is not a history-removal claim.
- No model weights, customer databases, `.env` secrets, generated `.next/` output, `node_modules`, or local live JSON state are intended for delivery. Local `data/storage/live/` files in the candidate remain untracked and are excluded from staging.
- Data/model reports are documentation only. Annotation labels were not independently reviewed and no accuracy/training score is asserted.

## Excluded machine-specific work

The source checkout contains host-specific `local-runtime/` configs that point at a personal Desktop path and private footage, plus experimental model state. Those files and their source tests were not carried over. A `scripts/run_native_live.py` launcher depended on that absent profile and did not pass the now-required explicit camera selection, so it was excluded from the candidate; the original source file remains untouched.
