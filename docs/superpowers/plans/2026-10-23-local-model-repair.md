# Local model repair implementation plan

Goal: Run the installed models locally and correct stale foot tracking without fabricated model status.
Architecture: Preserve the active Cursor source baseline in an isolated branch; use a local Compose override to point services at repaired source and existing video/weights. Keep person inference separate from enrichment.
Tech stack: Python, PyTorch, ONNX Runtime, Docker, Next.js.
Spec: User request in this chat, 2026-10-23.

Constraints: Friend mains untouched. Preserve client zones. Do not claim loaded models are executing without runtime evidence. No invented privacy approval flags.

Review focus: Moving ankles between pose passes; missing pose; small/occluded people; CPU contention; missing checkpoints.

- [x] Add failing movement regression in tests/test_overlay_foot_tracking.py; translate cached pose geometry on Track.update in src/perception/tracker.py; run targeted and full tests.
- [x] Inspect installed weights and runtime imports; configure concurrent installed enrichment plus RTMPose using local overrides; report missing MiVOLO/RF-DETR separately.
- [ ] Run local services with preserved footage and zones; verify detector throughput, actual model errors and overlay frames.

Ruling: Execute inline under the user's explicit instruction to solve on localhost; no additional plan approval needed.

Execution: Native GPU runtime selected after confirming MPS is available outside the sandbox. MiVOLO implemented and verified with actual weights; RF-DETR active as a secondary detector audit. Shelf gaps wired to measured products. Full accuracy/performance acceptance remains open on the 8 GB host. See docs/local-model-runtime.md.
