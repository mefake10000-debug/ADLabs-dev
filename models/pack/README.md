# Models pack — verified EdgeSight core weights

| | |
|--|--|
| **Branch** | **`mefake/integration`** on mefake fork only |
| **Download** | `python3 scripts/download_pack_models.py` (default dest = this folder) |
| **Docker** | `docker compose -f docker-compose.yml -f docker-compose.pack.yml up -d` → `/app/models/pack/` |
| **Research** | Do **not** pass `--include-research` (buffalo_l NON-COMMERCIAL) unless gated license is documented |

---

## Verified core layout (primary)

```
pack/
  01-detection/     yolo11n / yolo11s / yolo11m / yolo11n-pose
  02-tracking/      algorithms only (ByteTrack / OC-SORT / BoT-SORT) — no fake binaries
  03-reid/          OSNet x0.25 + x1.0 (.pth), OSNet ONNX P2, YouTu ReID ONNX P2
  04-face-attr/     YuNet (redaction / gating — NOT identity), expression + SFace P2
  05-open-vocab/    yolov8s/l-worldv2 + CLIP ViT-B/32 (HF)
  06-shelf/         yoloe-v8s-seg-pf (prompt/taxonomy shelf — no POS SKUs)
```

Legacy nested folders (`01-detection/yolo26n/`, `03-reid/osnet-x0_25/`, `05-seg/`, `07-openvocab/`) may still exist from earlier passes; SoftReId / products path resolution falls back to them when present.

---

## Wiring status (honest)

| Weight | Wired into live pipeline? |
|--------|---------------------------|
| Production `models/yolo26s.pt` | **Yes** — person detect (default) |
| Pack `01-detection/yolo11n.pt` | **Documented switch** — `perception.model_name` or `EDGESIGHT_DETECT_MODEL=models/pack/01-detection/yolo11n.pt` |
| Pack `yolo11s/m` + `yolo11n-pose` | **On disk** — soak before swapping pose (`models/yolo26m-pose.pt` stays default) |
| OSNet x0.25 `.pth` | **Path wired** — used when `torchreid` installed |
| OSNet ONNX / YouTu | **Yes** — torch-free SoftReID backend (Docker default) |
| Soft ReID flag | **`models.reid.enabled: true`** (session-scoped gallery; set `false` to disable) |
| YuNet (prod onnx + pack mirror) | **Yes** — face boxes for redaction / attribute gating |
| Expression / SFace | **Not hooked** — expression = Future aggregate-only; SFace = consented staff only (never shopper face-ID) |
| `yolov8s-worldv2` (prod + pack) | **Yes** — `models.products.backend: world` (default) |
| `yoloe-v8s-seg-pf` | **Yes** — set `models.products.backend: yoloe` (prompt-free name filter; no POS SKUs) |
| CLIP HF pack | **On disk** — live YOLO-World text encoder is `weights/clip/ViT-B-32.pt` (`CLIP_WEIGHTS_PATH`) |

### Soft ReID (privacy)

- Body crops only → session gallery (TTL `gallery_ttl_seconds`, default 1h)
- **No** face embeddings, **no** multi-day persistence, **no** CRM identity
- `cross_cam_fusion` / `global_person_id` remain **Future** (NTP + overlap + fusion)

### YOLO11 detect switch

```yaml
# configs/pipeline.yaml
perception:
  model_name: "models/pack/01-detection/yolo11n.pt"  # preferred pack A/B default
```

```bash
# Docker / host env override (does not rewrite yaml)
EDGESIGHT_DETECT_MODEL=models/pack/01-detection/yolo11n.pt
```

Keep `yolo26s` until a local soak compares FPS / recall.

### Shelf / products LIVE

- Live badge reads `products_top` on `/api/v1/live/snapshot`
- 24h rollup remains `/api/v1/analytics/products`
- Categories = open-vocab prompts, **not** POS SKUs

## Mac ARM notes

- Default Docker torch index is **CPU**. Enrichment on MPS is unsafe with dual-thread detect+enrich — config pins enrichment to CPU when fast tier owns MPS.
- CLIP HF `pytorch_model.bin` (~605MB) is heavy on disk; prefer existing OpenAI CLIP `weights/clip/` for YOLO-World text encoder in Docker.

## Re-download

```bash
python3 scripts/download_pack_models.py
# or: bash models/pack/download.sh
```
