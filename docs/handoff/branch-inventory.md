# GitHub branch and discussion inventory

**Checked:** 2026-10-24 using GitHub's branch list and compare API. Destination default is `mefake/integration` at `5de866f0e4adfb88472a0bf48bb8744722257b8f`. All 26 remote branch refs were compared with the default in this session: every non-default topic has `ahead_by=0` and is already reachable from the default; behind counts and tips are listed below. Git shell transport could not resolve GitHub, so pushing from this environment is still unavailable.

All 26 remote branches were compared with the default branch. Each topic ref has `ahead_by=0`; its tip is already reachable from the default history. They are historical snapshots that can be left untouched. No branch was deleted or changed. The separate review branch `consolidate/adlabs-final-review` is local and is not in the remote inventory.

| Remote branch | Tip | Scope suggested by branch name | Compared with default |
|---|---|---|---|
| `cursor/client-owns-zones-364e` | `693b33d4e9` | Client-owned zones | Behind 9; no unique commits |
| `cursor/competitor-parity-9574` | `a5febd1c0b` | Competitor parity research | Behind 34; no unique commits |
| `cursor/detect-balanced-18e5` | `7f261331eb` | Balanced detection preset | Behind 14; no unique commits |
| `cursor/foot-tracking-retail-b7ac` | `c62ac16ca7` | Foot tracking and retail overlay | Behind 10; no unique commits |
| `cursor/helper-handoff-wire-ec43-v2` | `490778c1c2` | Helper/API handoff | Behind 22; no unique commits |
| `cursor/industry-modes-8a18` | `033580145f` | Earlier industry-mode UI | Behind 27; no unique commits |
| `cursor/live-empty-fix-5266` | `ab1be5aaab` | Empty live-state fix | Behind 16; no unique commits |
| `cursor/live-fps-fast-tier-7625` | `035b1f1fc6` | Live FPS fast tier | Behind 43; no unique commits |
| `cursor/live-reflection-qa-cab0` | `4afca54b6e` | Live metric reflection QA | Behind 5; no unique commits |
| `cursor/live-ux-honesty-38da` | `ed3ce29b65` | Live-state honesty and UX | Behind 15; no unique commits |
| `cursor/locateanything-3b-ec43` | `98f76511cc` | LocateAnything research | Behind 46; no unique commits |
| `cursor/model-stack-policy-b03f` | `9958a5775c` | Model-stack policy | Behind 31; no unique commits |
| `cursor/nvidia-ultralytics-overlay-9121` | `12b767f9e0` | NVIDIA/Ultralytics overlay | Behind 12; no unique commits |
| `cursor/overlay-parallel-boxes-e7a7` | `239f05a5a0` | Parallel-box overlay experiment | Behind 30; no unique commits |
| `cursor/person-object-segregation-3ab3` | `47f0e40502` | Person/object separation | Behind 1; no unique commits |
| `cursor/reconcile-track-nvidia-foot-7d62` | `35f7846cdb` | Tracking and foot overlay reconciliation | Behind 6; no unique commits |
| `cursor/retail-sector-intelligence-d840` | `583f776122` | Retail intelligence UI | Behind 21; no unique commits |
| `cursor/rfdetr-sota-ec43` | `29cfa128ad` | RF-DETR research/integration | Behind 29; no unique commits |
| `cursor/todos-closeout-0ad1` | `a950bfef3b` | Review TODO closeout | Behind 18; no unique commits |
| `cursor/track-tripwire-regression-c3fe` | `844b894700` | Track/tripwire regression work | Behind 13; no unique commits |
| `cursor/trial-video-bakeoff-8d9a` | `d881c693b9` | Detection video bakeoff | Behind 4; no unique commits |
| `cursor/video-to-text-journey-3c8b` | `2802a98ce7` | Video-to-text journey | Behind 25; no unique commits |
| `integration` | `57fea1cc28` | Older integration snapshot | Behind 47; no unique commits |
| `mefake/friend-review-v1` | `5de866f0e4` | Friend review alias | Identical to default |
| `mefake/integration` | `5de866f0e4` | Default branch | Default |
| `mefake/models-docker-integration-v1` | `8279baaa0d` | Model/Docker integration snapshot | Behind 58; no unique commits |

## GitHub discussions

The current GitHub API search returned zero pull requests and zero open or closed issues. Earlier issue and inline PR-comment checks returned no comments; there are no PR reviews to summarize. The earlier report of “80+ comments” could not be reconciled to those discussion sources; repository commit-comment enumeration was not available through the connected read-only API. No comments were edited, posted, or deleted.

## Local source preservation

The Raj source clone, EdgeSight source checkout, Nuclear Quince clone, `product/dashboard-foundation` worktree, earlier consolidation worktree, and their pending files remain separate from this candidate. See [`consolidation-manifest.md`](consolidation-manifest.md) for their branches, commit IDs, and migration scope. No Nuclear Quince branch or checkout has been retired.
