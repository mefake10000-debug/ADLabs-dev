# EdgeSight model-stack policy (2026-10-23)

Authoritative keep / pull / skip / license gates for AD Labs retail CCTV.
Companion survey: `docs/handoff/model-survey-retail-cv-2026-10.md`.
Pack downloader: `scripts/download/download_pack_models.py` (phase-1).
Phase-2 stubs (dry-run default): `scripts/download/download_pack_models_phase2.py`.
Machine-readable catalog: `src/perception/model_stack.py`.

Status vocabulary used in registry + API: **LIVE | PACKED | PARTIAL | GATED | FUTURE | SKIP**.

---

## Keep (zero-effort / already in stack)

| Model | Role | License | Notes |
|-------|------|---------|-------|
| **YOLO26n** | Person detector (fast / edge) | AGPL-3.0 | Jan 2026 edge-optimized; ~**38.9 ms CPU-ONNX**. **Default fast path** (`DETECTOR_BACKEND=yolo26`). |
| **RF-DETR-N/S** | Person detector (SOTA / Apache) | Apache-2.0 | Roboflow SOTA via `rfdetr`. Selectable; **quality mode default**. See `docs/models/rfdetr-integration.md`. |
| **YOLOE** (`yoloe-v8s-seg-pf`) | Open-vocab shelf / products | AGPL-3.0 | Prompt-free pack weights under `models/pack/06-shelf/`. |
| **OSNet** ReID | Session-scoped cross-cam soft ID | MIT (code + weights) | ONNX SoftReID in quality mode. No multi-day gallery. |
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
- Commercial path needs **Ultralytics Enterprise** OR the **Apache detector path**: **RF-DETR-N/S** (wired; prefer over D-FINE / LW-DETR unless re-bench says otherwise).
- **Fast default:** YOLO26n. **SOTA/alternate:** `DETECTOR_BACKEND=rfdetr` (also the `EDGE_PERF_MODE=quality` default).

### Apache SOTA path — RF-DETR (selectable)

| Environment | Reference baseline (YOLO26n) | RF-DETR note |
|-------------|------------------------------|--------------|
| Docker (Mac ARM CPU, Compose edge) | **4.7–6.4 s/frame** | Prefer YOLO for demos; RF-DETR is heavier on CPU |
| Native Apple MPS | **~7 fps** YOLO26n | Prefer native MPS for RF-DETR quality runs |

Protocol when comparing:

1. Fixed footage + identical ByteTrack / zone config; boxes stay **xyxy**.
2. Report decode_fps, infer_fps, people_now parity vs YOLO26n tip.
3. `GET /api/v1/models/stack` must show `rfdetr` as LIVE only when selected+loaded.

### 2. Demographics / MiVOLO — DPIA gate

- MiVOLO v2 (and existing age/gender ONNX) stay behind **DPIA + k≥10 cohort aggregation**.
- Env: **`ENABLE_DEMOGRAPHICS=0`** default. Set `=1` only after DPIA row + cohort rollup wiring.
- Dashboard: show **EMPTY / FUTURE / GATED** — never invent live age/gender numbers.

---

## Registry status map (summary)

| Key | Status | Env / notes |
|-----|--------|-------------|
| `yolo26n` | LIVE | `EDGE_PERF_MODE=fast` + `DETECTOR_BACKEND=yolo26` default |
| `rfdetr` | LIVE / PACKED / OFF | LIVE when `DETECTOR_BACKEND=rfdetr` + loaded; else PACKED/OFF |
| `yoloe` / YOLO-World | LIVE / PACKED | products path |
| `osnet_reid` | LIVE (quality) / PACKED | session-scoped |
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
