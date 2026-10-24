# EdgeSight model-stack policy (2026-10-23)

Authoritative keep / pull / skip / license gates for AD Labs retail CCTV.
For the local review stack's scored model selection and active-path consolidation,
see [`model-stack-evaluation-2026-10-23.md`](../model-stack-evaluation-2026-10-23.md).
The compatibility catalog below includes alternatives; presence in the catalog or
on disk does not mean a model is loaded by the current live profile.
Companion survey: `docs/handoff/model-survey-retail-cv-2026-10.md`.
Pack downloader: `scripts/download/download_pack_models.py` (phase-1).
Phase-2 stubs (dry-run default): `scripts/download/download_pack_models_phase2.py`.
Machine-readable catalog: `src/perception/model_stack.py`.

Status vocabulary used in registry + API: **LIVE | PACKED | PARTIAL | GATED | FUTURE | SKIP**.

---

## Keep (zero-effort / already in stack)

| Model | Role | License | Notes |
|-------|------|---------|-------|
| **YOLO26** (selected checkpoint depends on performance profile) | Person detector | AGPL-3.0 | Current fast and quality backend default. Runtime checkpoint and actual loaded state come from the worker snapshot, not this catalog. |
| **RF-DETR-N/S** | Alternate person detector | Apache-2.0 | Optional `rfdetr` backend. Not the quality default and not loaded alongside YOLO in the primary count path. See `docs/models/rfdetr-integration.md`. |
| **YOLOE** (`yoloe-v8s-seg-pf`) | Open-vocab shelf / products | AGPL-3.0 | Prompt-free pack weights under `models/pack/06-shelf/`. |
| **OSNet** ReID | Session-scoped short-visit soft ID | MIT (code + weights) | Sampled ONNX SoftReID can run in fast mode when enabled by the model config and owner switch. No multi-day gallery. |
| **CLIP ViT-B/32** | Text / zero-shot shelf interest | MIT | Prod: `weights/clip/ViT-B-32.pt`; pack HF mirror under `05-open-vocab/`. |

---

## Best pulls for NEW capability (license-clean)

| Model | Role | License | Status | Gate |
|-------|------|---------|--------|------|
| **RTMPose-t/s ONNX** via **rtmlib** (no mmcv) | Ankle / foot pose → overlay + tripwire/dwell; fall-candidate | Apache-2.0 (HF `Tau-J/RTMPose`) | **LIVE** when ONNX on disk + edge load (`ENABLE_RTMPOSE=1`); else PARTIAL/PACKED | Phase-2 `--download --only rtmpose-t rtmpose-s`. See `docs/models/foot-tracking-retail-models.md`. Default overlay `OVERLAY_BOX_STYLE=foot`. |
| **MiVOLO v2** | Age/gender body-only OK when faces small | Apache-2.0 | **GATED** — default EMPTY/FUTURE until DPIA + k≥10 | `ENABLE_DEMOGRAPHICS=0` (default off). UI must **never** show raw age/gender as LIVE without aggregation gate. |
| **Moondream** | Lean VLM — nightly shelf-photo QA only | Apache-2.0 (HF card) | FUTURE / nightly shelf | Not every-frame; on-prem OK |
| **P2PNet** | Crush-density edge cases | **Academic-research-only** (Tencent LICENSE §1) | **SKIP** commercial; FUTURE research only | Prefer raising YOLO `max_det` first |
| **Shelf gap / OSA geometry** | Gap alerts from existing boxes | N/A (no new weights) | PARTIAL stub | Prefer over SKU-110K weights |

---

## Explicit SKIP / FUTURE (do not download)

| Item | Why |
|------|-----|
| **SKU-110K shelf weights** | Non-commercial dataset/weights — **SKIP**. Prefer Roboflow Universe CC BY 4.0 gap datasets **or** pure geometry from existing boxes. |
| **LocateAnything-3B** | NVIDIA non-commercial — **do not download**. Stay **FUTURE**. See `docs/models/locateanything-3b-integration.md`. |
| InsightFace `buffalo_l` | NON-COMMERCIAL research — omit `--include-research`. |
| P2PNet (commercial path) | Academic-only redistribution clause — stub only; do not vendor into pilot product. |

---

## License traps

### 1. Ultralytics + YOLOE = AGPL-3.0

- **OK for pilot.**
- Commercial licensing needs review for the selected detector and deployment. RF-DETR's Apache license is a licensing attribute, not evidence of accuracy, speed, or commercial fitness for this product.
- **Default backend:** YOLO26 in both fast and quality presets. **Alternate:** explicitly select `DETECTOR_BACKEND=rfdetr`; it remains off unless that backend is selected and loaded.

### Apache SOTA path — RF-DETR (selectable)

| Environment | Reference baseline (YOLO26n) | RF-DETR note |
|-------------|------------------------------|--------------|
| Docker (Mac ARM CPU, Compose edge) | No comparable RF-DETR measurement is recorded for this pilot. | Do not infer pilot performance from another machine. |
| Native Apple MPS | No comparable RF-DETR evaluation is recorded for this pilot. | Measure on the target host before making a speed claim. |

Protocol when comparing:

1. Use the same labeled clips, camera resolution, zone/tripwire config, tracker settings, and target Mac for both backends; boxes stay **xyxy**.
2. Record labeled person precision/recall/F1, count MAE, small/distant-person recall, false positives, ID stability, tripwire IN/OUT precision and recall, feed FPS, model-inference FPS, displayed FPS, CPU, and p95 processing latency.
3. Record exact model/package versions, weight file checksum, source/license, config, and clip/dataset label provenance. A valid result needs non-zero labeled frames and people.
4. Repeat the test at the intended camera count and load. No default change until the result shows an acceptable accuracy/latency tradeoff on this hardware.
5. `GET /api/v1/models/stack` must show `rfdetr` as LIVE only when selected and loaded. Accuracy appears in the dashboard only from a fresh labeled report; otherwise it says “Not measured.”

### 2. Demographics / MiVOLO — DPIA gate

- MiVOLO v2 (and existing age/gender ONNX) stay behind **DPIA + k≥10 cohort aggregation**.
- Env: **`ENABLE_DEMOGRAPHICS=0`** default. Set `=1` only after DPIA row + cohort rollup wiring.
- Dashboard: show **EMPTY / FUTURE / GATED** — never invent live age/gender numbers.

---

## Registry status map (summary)

| Key | Status | Env / notes |
|-----|--------|-------------|
| `yolo26n` | PACKED / LIVE | Live only when selected checkpoint and fresh worker snapshot confirm it |
| `rfdetr` | PACKED / LIVE / OFF | Live only when `DETECTOR_BACKEND=rfdetr` and loaded; otherwise alternate is idle |
| `yoloe` / YOLO-World | LIVE / PACKED | products path |
| `osnet_reid` | LIVE when a fresh snapshot confirms activity; otherwise PACKED/OFF | session-scoped |
| `clip_vit_b32` | LIVE / PACKED | |
| `rtmpose` | PACKED→PARTIAL | fall-candidate pose tier |
| `shelf_gap_geometry` | PARTIAL | zero new weights |
| `mivolo_v2` | GATED | `ENABLE_DEMOGRAPHICS` + DPIA |
| `moondream` | FUTURE | nightly shelf QA |
| `p2pnet` | SKIP (commercial) | academic license |
| `sku110k` | SKIP | non-commercial |
| `locateanything_3b` | FUTURE | NVIDIA NC — no download |

---

## Commands

```bash
# Phase-1 core pack (already verified)
python3 scripts/download/download_pack_models.py

# Phase-2 candidates — dry-run lists URLs/licenses; does not fetch
python3 scripts/download/download_pack_models_phase2.py

# Explicit fetch only after dry-run review + disk OK
python3 scripts/download/download_pack_models_phase2.py --download --only rtmpose-t
```

API: `GET /api/v1/models/stack` returns the catalog with honest statuses.
