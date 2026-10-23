# Open-Source CV Model Survey for Retail Intelligence — October 2026

Companion to `arm-enrichment-budget-runbook.md`. Scope: models with live GitHub/HF homes and real license documents (checked Oct 23, 2026 via live web search), mapped onto the verified EdgeSight pipeline slots (detector→tracker→zone registry, ONNX loader pattern, slow-tier cadence, native MPS edge). Sources listed at the end; every claim below traces to one of them or to a verified in-session measurement.

**Two license traps flagged up front:**
1. **Ultralytics stack is AGPL-3.0** (`ultralytics/ultralytics`, `THU-MIG/yoloe`). Already running in this repo. Fine for research/internal pilots; for a sold commercial dashboard, AGPL on the vendored inference stack forces open-sourcing of the served codebase or an Ultralytics Enterprise license. An Apache-2.0 alternative stack exists and is listed below.
2. **SKU-110K shelf weights are dataset-license-bound**: "provided solely for academic and non-commercial purposes" (dataset quote). Fine-tuned gap-detection weights trained on it cannot ship inside a commercial product. Use Roboflow Universe CC BY 4.0 gap datasets or label nothing/pure-geometry fallback.

---

## 1) TL;DR shortlist mapped to our slots

| Slot (existing) | Keep / adopt | License | Integration effort | Why |
|---|---|---|---|---|
| Detector (`yolo26n.pt`, imgsz 320) | **KEEP YOLO26n** (Jan 2026 release; edge-optimized: DFL removed, NMS-free optional, 38.9 ms CPU-ONNX vs YOLO11n 56.1 ms, 40.9 mAP50-95) | AGPL-3.0 | zero (already live) | best CPU/edge price-accuracy in family; MOT study: YOLO26 gives favorable quality/speed with ByteTrack/BoT-SORT |
| Detector, license-clean swap option | **RF-DETR-N/S** (roboflow, ICLR 2026; N = 48.4 AP50:95 COCO @ 2.3 ms T4; RF100-VL 85 AP) or **D-FINE-S/M** (50.6/55.0 AP), **LW-DETR-S** | Apache-2.0 | M — new head adapter in registry (RT-DETR-style outputs) | Apache path frees the AGPL question; RT-DETR family showed the **best HOTA across MOT17/20/SOMPT22** paired with our tracker class |
| Open-vocab labels (products/display) | **KEEP YOLOE** (`yoloe-v8s-seg-pf.pt`, loaded in 210 ms in our bench) **or YOLO-World v2** — both AGPL family | AGPL-3.0 | zero | Apache-licensed open-vocab is scarce; Moondream detect (below) is the license-clean fallback for slow-tier label passes |
| Open-vocab, license-clean, offline tier | **Moondream 2 / 3-preview** (detect/pointing native skills, 2B active params; 0.5B distill variant for extreme edge) | Apache-2.0 code; **Moondream Model License 1.0** on weights (free for on-prem/self-hosted + commercial apps; only hosted general-purpose model service is restricted — our store deployment is explicitly allowed) | M (offline/nightly shelf-photo QA, never in the fps loop) | grounded boxes on natural language; different repo than any current dep |
| Small VLM batch QA | **SmolVLM 256M/500M** (<1 GB GRAM for 256M; video-capable) | Apache-2.0 | L (batch caption/QA of shelf snapshots, opt-in tier) | richer "what changed on the end-cap" summaries; never on the inference loop |
| Pose tier (`models.pose` currently false) | **RTMPose-t/s/m ONNX via rtmlib** (no mmcv/mmpose deps; only onnxruntime+cv2 — mirrors our loader pattern; RTMPose-m 74.9–76.7 AP body7 @ 256×192) | rtmlib + mmpose: open-mmlab (verify LICENSE per repo before vendoring) | S | drop-in pose for SAFETY_FALL_CANDIDATE_POSE; plugs into the verified slow-tier slot without torch |
| ReID (session-scoped, cross-camera) | **KEEP OSNet** (`osnet_x1_0` ONNX contract verified: [16,3,256,128]→[16,512], 197 ms) + weights mirror `kaiyangzhou/osnet` | MIT (code and weights both confirmed) | zero | also `osnet_ain_x1_0` MSMT17 for an accuracy bump, same I/O contract |
| Demographics (DPIA-gated) | **KEEP FairFace** or adopt **MiVOLO v2** (dual face+body 384×384; age MAE 4.24 face+body / 6.87 body-only on IMDB-cleaned; gender 96–99% on source benches; works with no face visible) | Apache-2.0 (repo + HF model card) | M — new gated branch, same k≥10/bucket/cohort-rollup machinery | body-only mode fits CCTV where faces are small; still a SENSITIVE feature: all `demographics-cohorts-multi-store.md` safeguards transfer unchanged |
| Crowd counting (dense scatter) | **P2PNet** (official Tencent repo; license file present in repo — read before vendoring) — only needed beyond detector `max_det` cap in crush scenes | repo license file — verify | M — optional | honest alternative: benchmark `max_det` raise on YOLO26 first (shelf work shows default caps silently truncate dense scenes) |
| Shelf gap / OSA (new retail feature) | **Geometry-first: class-agnostic boxes + row clustering → gap rule (~80% of row median product width) → OSA = occupied width ratio** (open-source recipe, no special weights needed); optional fine-tune on **Roboflow Universe CC BY 4.0** gap datasets | CC BY 4.0 (dataset); recipe license-free | S→M | avoids SKU-110K non-commercial trap entirely; use RF-DETR fine-tune path if a trained head is later required (Apache end-to-end) |

**Deliberately NOT adopted:** SAM 3 (Meta — requires access approval on Hugging Face, not freely pullable), insightface/buffalo_l pack (already skipped: research-license), PaliGemma family (Google Gemma terms are restrictive for automated retail analytics at scale), weapon/age-decisioning models (policy-excluded per `safety-analytics-retail-floor.md` section 6 and the demographics DPIA — regardless of availability).

## 2) Detector tier — the actual trade table (from live benchmarks, October 2026)

| Model | COCO AP50:95 | RF100-VL AP50 | Latency (T4 TRT) | Params | License | Notes |
|---|---|---|---|---|---|---|
| YOLO26n | 40.9 | 76.7 | 1.7 ms | 2.4 M | AGPL-3.0 | 38.9 ms CPU-ONNX; DFL removed for export simplicity |
| YOLO26s | 48.6 | 82.7 | 2.6 ms | 9.4 M | AGPL-3.0 | our observed in-bench edge pick |
| RF-DETR-N | 48.4 | 85.0 | 2.3 ms | 30.5 M | Apache-2.0 | XL/2XL variants are PML 1.0 (not free) |
| RF-DETR-S | 53.0 | 86.7 | 3.5 ms | 32.1 M | Apache-2.0 | |
| D-FINE-S | 50.6 | 85.3 | 3.5 ms | 10.2 M | Apache-2.0 | D-FINE-seg S beats YOLO26-M on Cityscapes F1 |
| LW-DETR-S | 48.0 | 85.0 | 2.6 ms | 14.6 M | Apache-2.0 | |
| RT-DETR-L/X | 55+/57+ class | — | heavy | 32–66 M | Apache-2.0 (upstream) | best HOTA in MOT study; server-tier, not edge |

MOT context (arXiv 2610.19369): RT-DETR-X + ByteTrack hit the highest HOTA on MOT17 (39.20) / SOMPT22 / MOT20 in that study; YOLO26-L with NMS was the favorable speed/quality pick — i.e., for OUR floor-tracking use-case, detector choice matters more than tracker choice, and switching detector is a registry-head change, not a pipeline rewrite.

## 3) Capability → model → integration map (into our verified code)

- **Footfall/occupancy/queues/staff/safety**: unchanged — detector+tracker+zones. If AGPL becomes unworkable: implement `kind="detector"` RT-DETR-style head in `src/perception/registry.py` (same ONNX fixed-batch contract pattern the OSNet loader already validates), keep the tracker untouched.
- **Display interest / categories**: keep YOLOE + CLIP ViT-B-32 slow-tier as verified; add Moondream-detect as an OPTIONAL offline pass (nightly shelf-photo QA that returns boxes for operator labels) — the benefit: it shares the same operator-label vocabulary as the shelf-face zone config, so no invented SKUs.
- **Pose (fall candidates)**: pull `rtmpose-m_simcc-body7 ... 256x192` ONNX from the rtmlib zoo (URL pattern visible in rtmlib README / HF mirror `Tau-J/RTMPose`), load with the existing ORT loader, feed from confirmed person boxes at slow-tier cadence; wire into `SAFETY_FALL_CANDIDATE_POSE` (FUTURE→PARTIAL becomes possible honestly).
- **ReID**: zero work (already MIT-clean + verified). Ordering: leave the OSNet ONNX contract as the reference implementation.
- **Demographics**: gate MiVOLO behind the SAME `models.demographics` yaml + DPIA row + k≥10 + `cohort_rollups` (aggregate-only). Body-only inference is a real new capability (no face needed) — mention in the DPIA data-categories update.
- **Shelf gap/OSA**: the geometry recipe (row clustering + median-width gap rule + OSA score) runs on current class-agnostic boxes — zero new weights, license-free logic. Publish as PARTIAL until measured on-site; the gap alerts surface naturally on the shelf-face zones we already calibrate in the studio.

## 4) Integration order (three phases, each verifiable)

1. **Phase 1 (this week, S):** pull RTMPose ONNX via a short script into `models/pose/`, register under `kind="pose"` with the slow-tier interval (16 unchanged), run the flat onnxruntime load-bench (target: pose-on ≲ 12 ms/box on MPS), flip only `SAFETY_FALL_CANDIDATE_POSE` from FUTURE→PARTIAL with the candidate-only disclaimer retained.
2. **Phase 2 (planning, M):** Apache detector adapter `kind="detector"` for RF-DETR-N/S or D-FINE-S + MOT re-bench on our footage replicating the published HOTA methodology; decide AGPL-vs-Enterprise on real numbers (same container/native bench protocol: 4.7–6.4 s/frame Docker baseline, ~7 fps native MPS YOLO26n as reference).
3. **Phase 3 (opt-in, M/L):** Moondream/SmolVLM offline QA tier for shelf photos + MiVOLO behind the DPIA gate; P2PNet only if store-peak density ever exceeds detector count ceilings.

Validation checklist per model (mechanical, reuses in-session patterns): load-time, ORT input/output shape contract assert, fixed-batch pad path, slow-tier cadence smoke, KPI-parity run (queue/occupancy fields identical with enrichment on/off), and the `arm-enrichment-acceptance.sh` all-green after each flip.

## 5) Sources (live-checked Oct 23, 2026)

- Ultralytics model docs & YOLO26 comparisons: docs.ultralytics.com/models, docs.ultralytics.com/compare/yolo11-vs-yolo26 (YOLO26 released Jan 2026; 38.9 ms CPU-ONNX YOLO26n; DFL removal rationale), docs.ultralytics.com/compare/yolov10-vs-rtdetr, docs.ultralytics.com/compare/yolo26-vs-rtdetr, docs.ultralytics.com/compare/yolo26-vs-rtdetrv2 — YOLO26 is AGPL-3.0 per the RF-DETR benchmark table.
- RF-DETR: github.com/roboflow/rf-detr (ICLR 2026; Apache 2.0 base models / PML 1.0 Plus; 48.4 AP50:95 RF-DETR-N) and rfdetr.roboflow.com/latest; pypi rfdetr 1.11.2.
- D-FINE: pypi dfine-seg (Apache-2.0; Cityscapes/VisDrone fine-tune wins vs YOLO26).
- RT-DETR upstream: github.com/lyuwenyu/RT-DETR (Apache).
- MOT study: arxiv.org/html/2610.19369v1 (YOLO11/RT-DETR/YOLO26 families × ByteTrack/BoT-SORT, HOTA numbers).
- YOLOE: github.com/THU-MIG/yoloe (ICCV 2025, AGPL-3.0; RepRTA/SAVPE/LRPC overview) and arxiv.org/html/2503.07465 (CC BY paper).
- Pose: github.com/open-mmlab/mmpose/projects/rtmpose; pypi rtmlib + github.com/Tau-J/rtmlib (no-mmcv ONNX zoo; RTMPose-t/s/m APs; wholebody RTMW; HF mirror Tau-J/RTMPose).
- ReID: github.com/KaiyangZhou/deep-person-reid (MIT LICENSE file) + huggingface.co/kaiyangzhou/osnet (license: mit; osnet/OSNet-AIN MSMT17 weights).
- Crowd counting: github.com/TencentYoutuResearch/CrowdCounting-P2PNet (ICCV 2021 oral; NWPU MAE 77.44; license file present) + arxiv 2107.12746.
- Shelf: github.com/rickhaile/retail-shelf-monitor (SKU-110K YOLO11n recipe; gap rule ~80% row-median width; OSA definition; 12.3% counting error disclosed), SKU-110K academic/non-commercial clause via the CVPR-2020 challenge write-up, Roboflow Universe gap dataset CC BY 4.0 (universe.roboflow.com/srm-university-52jqz/retail-shelf-availability), HF akul-29/Retail-Shelf-Gap-Detection_Model (YOLOv8 fine-tune; no usable license/terms stated — treat as unlicensed until verified).
- VLMs: github.com/m87-labs/moondream (Apache-2.0 code) + moondream.ai/licenses/model/1.0 (Moondream Model License 1.0 — hosted-service restriction only) + moondream.ai/models (M3-preview: 2B active params, 0.5B distill target, native detect/point skills); github.com/huggingface/smollm (Apache-2.0; SmolVLM 256M < 1 GB GRAM) + SmolVLM paper arxiv 2504.05299.
- MiVOLO: github.com/WildChlamydia/MiVOLO (Apache-2.0; age MAE 4.24 face+body / 6.87 body; gender 96–99%) + huggingface.co/iitolstykh/mivolo_v2 (license apache-2.0; 384×384 dual-stream; "trained on proprietary and open-source datasets" — retained in DPIA sourcing note).

House discipline note: this survey only names what was live-checked; anything unverified (weight licenses, sub-100-star repos) inherits the standing "verify LICENSE before vendoring" rule, and sensitive-category models (MiVOLO) stay behind the DPIA gate exactly as designed — availability never lowers that bar.
