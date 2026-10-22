# Models pack — downloaded weights (segregated)

**Purpose:** On-disk weights for next EdgeSight integrates, kept **out of** the production `ADLabs-dev/models/*.pt` root until wired.  
**Docs index:** `../README.md` + Project store `docs/models-to-integrate-index.md`  
**Runtime mount:** `repos/ADLabs-dev/models/pack/` (mirrors this tree for Docker)

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

## Downloaded this pass

| File | Role | Status |
|------|------|--------|
| `01-detection/yolo26n/yolo26n.pt` | Doorway-only fast detector | **Present** (~5.3MB) |
| `03-reid/osnet-x0_25/osnet_x0_25_msmt17.pt` | Soft ReID backbone | **Present** (~2.9MB) |

Production EdgeSight weights (already in `ADLabs-dev/models/`): yolo26s, yolo26m-pose, yolov8s-worldv2, YuNet, age/gender ViT (+INT8), CLIP ViT-B-32 — run `python scripts/download_models.py` in ADLabs-dev if missing.

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
