# Models pack — segregated next-integrate weights

| | |
|--|--|
| **Branch** | **`mefake/integration`** on mefake fork (from `id-switch-detector-staff-zones`) |
| **Purpose** | On-disk weights for next EdgeSight integrates — **not** mixed into production `models/*.pt` until wired |
| **Download** | `python scripts/download_pack_models.py` or `bash models/pack/download.sh` |
| **Docker** | `docker compose -f docker-compose.yml -f docker-compose.pack.yml up -d` → `/app/models/pack/` |
| **Docs** | Project store `docs/models-to-integrate-index.md` · `docs/website-integration.md` |

---

## Layout

```
pack/
  README.md                          ← you are here
  01-detection/yolo26n/              ← doorway fast-tier detector
  02-tracking/README.md              ← OC-SORT / BoT-SORT (code deps; no weight yet)
  03-reid/osnet-x0_25/               ← cross/intra soft ReID (privacy-gated)
  04-attributes/README.md            ← demographics already in ADLabs-dev/models/onnx/
  05-seg/README.md                   ← foot-mask salvage uses existing yolo26m-seg.pt
  download.sh                        ← re-fetch missing files
```

---

## Required pack weights (checklist)

| File | Role | Status | URL |
|------|------|--------|-----|
| `01-detection/yolo26n/yolo26n.pt` | Doorway-only fast detector | **Present** (~5.3MB) · not prod-wired | [ultralytics yolo26n](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt) |
| `03-reid/osnet-x0_25/osnet_x0_25_msmt17.pt` | Soft ReID backbone | **Present** (~2.9MB) · default-off | [HF osnet_x0_25](https://huggingface.co/paulosantiago/osnet_x0_25_msmt17/resolve/main/osnet_x0_25_msmt17.pt) |
| `02-tracking/` | OC-SORT / BoT-SORT | **Missing weight N/A** · code deps only | — |
| `04-attributes/` | Demographics pointer | Use `models/onnx/` (Live) | via `download_models.py` |
| `05-seg/` | Foot-mask salvage | Use prod `yolo26m-seg.pt` | [yolo26m-seg](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26m-seg.pt) |

Production EdgeSight weights (`models/` + `models/onnx/`): **yolo26s** (required), yolo26m-pose, yolov8s-worldv2, YuNet, age/gender ViT (+INT8), CLIP ViT-B-32 — `python scripts/download_models.py`.

---

## Honest notes

- Pack weights are **not** production-wired until config + code land (see to-integrate dossiers).  
- OSNet stays **default-off** (DPDP / no face ReID).  
- Marketing `/dashboard` remains simulated unless EdgeSight Docker is up and the site live-ops blend is used.

## Re-download

```bash
bash ~/Desktop/ad-labs-project/models/pack/download.sh
# or inside ADLabs-dev (mefake branch):
python scripts/download_pack_models.py
```

## Docker (this repo)

```bash
docker compose -f docker-compose.yml -f docker-compose.pack.yml up -d
python scripts/download_pack_models.py
```

Pack appears at `/app/models/pack/` inside `edge-analyzer`.
