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
| Production `models/yolo26s.pt` | **Yes** — person detect (unchanged) |
| Pack `01-detection/yolo11*.pt` | **On disk only** — swap `perception.model_name` after soak |
| Pack `yolo11n-pose.pt` | **On disk only** — prod pose stays `yolo26m-pose.pt` |
| OSNet x0.25 verified `.pth` | **Path wired**, `models.reid.enabled: false` (session-scoped soft ReID) |
| OSNet ONNX / YouTu | **Not hooked** — torch-free fallback TBD |
| YuNet (prod onnx + pack mirror) | **Yes** — face boxes for redaction / attribute gating |
| Expression / SFace | **Not hooked** — SFace only for consented staff if ever enabled |
| `yolov8s-worldv2` (prod + pack) | **Yes** — category interest via prompts (not POS SKUs) |
| `yolov8l-worldv2` / CLIP HF pack | **On disk** — prod CLIP still `weights/clip/ViT-B-32.pt` |
| `yoloe-v8s-seg-pf` | **Not hooked** — shelf masks via YOLOE prompts future |

## Mac ARM notes

- Default Docker torch index is **CPU**. Enrichment on MPS is unsafe with dual-thread detect+enrich — config pins enrichment to CPU when fast tier owns MPS.
- CLIP HF `pytorch_model.bin` (~605MB) is heavy on disk; prefer existing OpenAI CLIP `weights/clip/` for YOLO-World text encoder in Docker.

## Re-download

```bash
python3 scripts/download_pack_models.py
# or: bash models/pack/download.sh
```
