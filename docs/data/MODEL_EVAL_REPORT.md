# Model evaluation report — ADLabs-dev

> **Provenance and use limit:** This is a historical report migrated from the Raj/EdgeSight source working tree, not a benchmark rerun on this consolidation branch. The source working tree contained local-only weights and footage that were deliberately not copied. The counts below are approximate count-checkpoint observations, not reviewed box labels and not precision/recall or model-accuracy scores. They do not establish current weight availability, current model load state, or current runtime performance. For the checked-in branch’s actual config/weight status, see [`../handoff/model-runtime-inventory.md`](../handoff/model-runtime-inventory.md).

**Branch:** `ml/dataset-research-train-eval` (created from `fps-optimization-enhance`)
**Date:** 2026-10-24
**Scope:** local repo only; no model weights downloaded, no package installed, no Docker image pulled, no raw private footage copied.

## Executive summary

The only defensible scored run was YOLO26s on two licensed mall count checkpoints, using the configured person filters and a 5 FPS processing cadence on CPU. It retained zero person boxes at both checkpoints: the model emitted 2 and 5 boxes at configured confidence, but the configured size filter rejected all of them. These are count-only checks, not precision/recall measurements. The evidence points to threshold/filter tuning and better box annotations before considering training; the available labels do not justify fine-tuning.

## Model audit

“Loaded” for live status means the saved `data/storage/state/live.json` snapshot from **2026-10-22 21:40:26**; it is stale and cannot verify what is running now. The benchmark-loaded row refers to the explicit local evaluation performed for this report. Pipeline wiring was audited in `configs/pipeline.yaml`, `src/main.py`, and `src/perception/registry.py`. License notes below are limited to local repo documentation; no internet lookup was performed.

| Model/capability | Configured weights and local availability | Enabled | Loaded evidence | Actually used for inference | Tier | License / notes |
|---|---|---:|---|---|---|---|
| YOLO26s person detector | `models/yolo26s.pt` — present (20.4 MB) | Yes; first configured candidate | Loaded in this report’s benchmark; current service state not verifiable | Yes, detector worker; selected candidate | Fast | Local model-specific license/provenance not recorded. Ultralytics asset; do not infer the checkpoint license from code license alone. |
| YOLO26n | `models/yolo26n.pt` — absent | No | No | No | — | Not locally documented. |
| RF-DETR | No configured path or local checkpoint found in checked paths | No | No | No | — | No local license evidence. |
| YOLO26m detector | `models/yolo26m.pt` — present (44.3 MB), not selected | No | No | No | — | Local model-specific license/provenance not recorded. |
| YOLO26m-Pose | `models/yolo26m-pose.pt` — present (49.0 MB) | Yes | Last saved live snapshot: loaded | Yes, when slow-tier work runs and tracks exist | Slow | Model-specific license not recorded locally. |
| YuNet face detector | `models/onnx/face_detection_yunet_2023mar.onnx` — present | Yes | Last saved live snapshot: loaded | Yes, full frame and selected person crops on slow tier | Slow | Apache-2.0 per `models/pack/04-face-attr/README.md`; used for face localization/landmarks, not identity. |
| Age/Gender | `models/onnx/age_gender_vit_int8.onnx` preferred; present (87.2 MB); FP32 also present | Yes | Last saved live snapshot: INT8 loaded | Yes, capped/rotated face crops; CPU ONNX | Slow | License not recorded in local notes. Results are k-anonymized aggregates; no meaningful score without suitable labels. |
| Head pose | No model weights; geometric `solvePnP` over YuNet’s five landmarks | Yes | Estimator object constructed when enabled; not in registry | Yes, when a face is detected | Slow | Code-based estimate, not a separate learned model. Facing/attention are proxies, not gaze ground truth. |
| YOLOv8s-Worldv2 | `models/yolov8s-worldv2.pt` — present (25.9 MB) | Yes | Last saved live snapshot: loaded | Yes, category prompts on slow-tier frames | Slow | AGPL-3.0 per `models/pack/05-open-vocab/README.md`; categories are not SKUs/sales. |
| OSNet ReID | Configured `.onnx` and `.pth` paths are both absent | Config says enabled | Not in stale snapshot; current load unknown | **No consumer**; status/load attempt only, no embeddings or cross-camera association | Slow/status-only | Local pack note lists MIT (`.pth`) and MIT for an unofficial ONNX export; neither configured file exists. Do not evaluate for retraining. |
| CLIP ViT-B/32 | `weights/clip/ViT-B-32.pt` — present (354.0 MB) | No | Not loaded | No separate CLIP call or consumer is wired | Slow/disabled | Local pack notes list MIT; exact checkpoint provenance is not fully documented. YOLO-World prompt handling is a separate path. |
| YOLOE shelf model | `models/pack/06-shelf/yoloe-v8s-seg-pf.pt` — absent | No | No | No shelf/planogram consumer is wired | Slow/disabled | AGPL-3.0 per local pack notes; unavailable locally. |

**Runtime caveat:** system `python3` lacked Ultralytics. The repo’s existing `.venv` contained Ultralytics 8.4.155, PyTorch 2.14.0, OpenCV 5.0.0, and ONNX Runtime 1.31.0. PyTorch reported MPS unavailable and CUDA unavailable, so this evaluation used CPU. Docker access was denied by the local Docker socket; no Docker service was started.

## Data discovery and curation

At the time of the source audit, the originating checkout contained 18 source MP4s and 10 short ID-switch candidate clips (28 MP4s, about 700.4 MB and 73.7 minutes combined). This inventory is historical: the media files are excluded from this review branch. Source metadata was probed locally with OpenCV; no additional frames were extracted during that discovery pass.

| Source group | Files and metadata | Use decision |
|---|---|---|
| Licensed mall footage | `mall_entrance_topdown_01.mp4` 1280×720, 25 FPS, 40.16s; `mall_promenade_01.mp4` 1280×720, 29.97 FPS, 72.41s; `mall_concourse_01.mp4` 1280×720, 23.98 FPS, 86.21s; `mall_crowd_dense_01.mp4` 1280×720, 30.52 FPS, 31.26s | Pexels license is documented in `data/sample_videos/SOURCES.md`. Two clips have one approximate count checkpoint each; those two exact frames form the initial eval-only set. |
| Other public/synthetic samples | `store_entrance_near_01.mp4` 1280×720, 29.97 FPS, 19.75s; `test_footage1.mp4` 1920×1080, 30 FPS, 11.37s; `checkout_sample.mp4` 1280×720, 15 FPS, 20s | Pexels provenance is documented for the first two; no independent labels. Checkout is synthetic and excluded from real-scene scores. |
| Unknown-origin shop clip | `entrance_sample.mp4` 1270×720, 13.09 FPS, 111.05s | Five approximate count checkpoints exist, but provenance/license is unknown. Excluded pending provenance resolution. |
| Private garage footage | `garage_part00`–`03`, `garage_part04_0`, `garage_part04_1`, `garage_part05`; each 1280×720 at 20 FPS, about 4.94–10.01 min | Internal owner consent is documented. The 10 count-sheet entries are all null. Prep report says 66.6 usable minutes and lists `garage_part06`; present clips total about 60 minutes with different split names. Excluded from scoring until reconciled and annotated. No private clips or frames copied. |
| Private restaurant footage | Three `restaurant_ch17` clips, 1280×720 at 25 FPS, 170.56s, 129.20s, and 94.04s | Internal owner consent is documented; no independent labels. Kept out of scored data. Existing camera calibrations cover selected restaurant clips, but configured zones are not ground truth. |
| ID-switch candidate run | Ten event clips from `store_entrance_near_01`, 1280×720, about 3 FPS and 2.34–4.00s each | Existing run summary reports 10 suspected candidates (5 each of two candidate types), not verified identities. `tracks.jsonl` is model output, not ground truth. Candidate mining only. |

The originating checkout's local SQLite cache had 1,854 rollups, 824 crossing events, and 9,751 product-interest rows for one camera; its cloud-metrics SQLite mirror had similar totals. These were pipeline outputs, not independent truth, so none were used as labels. `camera_health` was empty. Existing `frames/` and `heatmaps/` images were generated artifacts, not ground truth. The databases and images were not migrated into this review branch. Database inspection was limited to schema and aggregate counts; no event-level rows or identifiers were emitted.

The source evaluation checkout's `ml_dataset/` had two checkpoint frames from the two mall clips, with counts consolidated in `ground_truth/point_counts.json`. Neither the frames nor videos are included in this review branch. The text-only `docs/data/eval_only.json` records why no train/validation/test split is justified. No box, pose, face, product, or identity labels exist.

## Detection evaluation

Existing harness: `scripts/benchmark/benchmark_tracking.py`, configured person thresholds/filters, YOLO26s explicitly selected, `--process-fps 5` behavior, no saved annotated output. The model ran in the repo `.venv` on CPU. Checkpoint counts are approximate; ratio below is a **count coverage proxy**, not recall.

| Clip / checkpoint | Hand count | YOLO person boxes at configured confidence | Rejected by size | Rejected by aspect | Kept detections | Tracker output | Count coverage proxy after filters |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mall top-down, frame 500 | 9 (approx.; distant figures omitted) | 2 | 2 | 0 | 0 | 0 | 0/9 = 0% |
| Mall promenade, frame 900 | 4 (approx.; reflections excluded) | 5 | 5 | 0 | 0 | 0 | 0/4 = 0% |

Combined, the model retained **0** boxes against approximate expected counts totaling **13**. This cannot be called 0% recall: count labels do not identify which boxes match which people, and a count discrepancy does not distinguish misses from false positives. In both cases all model boxes at configured confidence were rejected by the current size filter (`min_height: 95`, `min_area: 3000`); the top-down model proposed only two boxes for a frame with at least nine clearly counted people.

| Metric | Result | Reason unavailable / caveat |
|---|---:|---|
| Precision, recall, F1, TP/FP/FN | null | No person bounding-box annotations. |
| mAP@0.5, mAP@0.5:0.95 | null | No box annotations. |
| IDF1, MOTA, MOTP, true ID switches | null | No consistent ground-truth identities across frames. |
| Tripwire/queue/dwell accuracy | null | No independent event-level truth for these selected clips. |
| Pose, face/demographics, product scores | null | No corresponding labels; scoring would be guesswork. |

## Failure analysis and tune-vs-train

1. **Current geometry filter discards every proposal in both tested frames.** A threshold/size-filter ablation is the first tuning experiment to run once person boxes are annotated.
2. **The top-down frame has a detector-recall limitation as well as a filter limitation.** Only two proposals appeared at the configured confidence for a count of at least nine, so filter relaxation alone cannot solve that scene. A higher image size or another camera-appropriate configuration could be tested, but there is no box-level truth yet to choose safely.
3. **The promenade frame has five proposals for four approximate counted people, all rejected by size.** Lowering `min_height`/`min_area` may recover boxes, but could also add false positives; count-only truth cannot resolve that tradeoff.
4. **Tracking cannot be judged from these still checkpoints.** The zero tracker output follows from the empty post-filter detections; it says nothing about ID continuity.
5. **Garage preparation provenance is inconsistent.** The missing segment and null labels make it unsuitable for a reproducible evaluation until repaired.

**Recommendation:** `TUNE FIRST; DO NOT FINE-TUNE YET.` The immediate evidence is a configured geometry filter rejecting all proposals. But the two-frame dataset cannot validate a threshold change or prevent false positives. The next high-value work is a modest, independently reviewed person-box annotation set spanning small distant people, occlusion, groups, and clear backgrounds, plus a short sequence with anonymous consistent track IDs for tracking metrics. Resolve the garage manifest before sampling that footage. Do not use face crops or appearance embeddings for re-identification.

## Reproduction and change log

- Model files were already present; no download or new weight file was added.
- First attempt with system Python stopped safely because Ultralytics was absent. The existing repo `.venv` was used instead; no packages were installed.
- Benchmark outputs were collected in-memory; no annotated checkpoint images were saved.
- Dataset frames are excluded from Git; private footage was not copied.
- No tests were needed for these report/data-only changes. No commit or push was made.
