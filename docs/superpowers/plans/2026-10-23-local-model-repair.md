# Local model repair implementation plan

Goal: Run the installed models locally and correct stale foot tracking without fabricated model status.
Architecture: Preserve the active Cursor source baseline in an isolated branch; use a local Compose override to point services at repaired source and existing video/weights. Keep person inference separate from enrichment.
Tech stack: Python, PyTorch, ONNX Runtime, Docker, Next.js.
Spec: User request in this chat, 2026-10-23.

Constraints: Friend mains untouched. Preserve client zones. Do not claim loaded models are executing without runtime evidence. No invented privacy approval flags.

Review focus: Moving ankles between pose passes; missing pose; small/occluded people; CPU contention; missing checkpoints.

- [x] Add failing movement regression in tests/test_overlay_foot_tracking.py; translate cached pose geometry on Track.update in src/perception/tracker.py; run targeted and full tests.
- [x] Inspect installed weights and runtime imports; configure concurrent installed enrichment plus RTMPose using local overrides; report missing MiVOLO/RF-DETR separately.
- [x] Run local services with preserved footage and zones; verify model load, ongoing inference, camera counts, detector throughput, and overlay frames.

Ruling: Execute inline under the user's explicit instruction to solve on localhost; no additional plan approval needed.

Execution: Native GPU runtime uses Apple MPS for YOLO and a CPU enrichment lane to avoid unsafe concurrent Metal access. Pose, face, product/CLIP, demographics, and ReID inference are grouped into concurrent independent jobs; RF-DETR runs beside the main pipeline as a secondary audit and does not affect visitor totals. MiVOLO is loaded from the verified local checkpoint with k-anonymous aggregates. The detector now admits smaller, partially occluded people, cached feet follow their tracks, and the default local overlay uses clipped person boxes instead of red dots. Live checks show 9–12 people at roughly 1.4–2.7 FPS on the 8 GB host. Shelf gap remains PARTIAL until the operator calibrates shelf faces. See docs/local-model-runtime.md.
