# Website live-dashboard integration

> **Canonical review pair (only):** `mefake/integration` on both forks.  
> Sibling feature branches were absorbed into this tip — do not review them as current.  
> Never push `rajendrac3/ADLabs-dev` `main` or `NuclearQuince/adlabs` `main`.

| Repo | Canonical branch | Base | Tip |
|------|------------------|------|-----|
| ADLabs-dev (`mefake10000-debug`) | **`mefake/integration`** | `id-switch-detector-staff-zones` | see GitHub |
| Website adlabs (`mefake10000-debug`) | **`mefake/integration`** | website-final + full-models + calib/ops blend | see GitHub |

(`refs/heads/integration` on the ADLabs-dev fork may mirror the same tip as an alias — prefer **`mefake/integration`**.)

## What this enables

The Next.js site (`~/Desktop/ad-labs-project/repos/adlabs`, branch `mefake/integration`) blends the marketing dashboard at **http://localhost:3000/dashboard** with live EdgeSight:

| Surface | URL |
|---------|-----|
| **Portal (only user-facing)** | http://localhost:3000/dashboard |
| Calibration / Live ops | http://localhost:3000/dashboard/live |
| Live video + KPIs | http://localhost:3000/dashboard/live?panel=video |
| Calibration Studio (embedded) | http://localhost:3000/dashboard/live?panel=calib · rewrite `/dashboard/live/calibrate` → `:8000` |
| Streamlit ops (embedded) | http://localhost:3000/dashboard/live?panel=ops · Streamlit `baseUrlPath=/dashboard/live/ops` |
| Status proxy | http://localhost:3000/api/edgesight/status |
| EdgeSight API proxy | http://localhost:3000/api/v1/* · http://localhost:3000/docs |
| Docker backends (not primary UX) | `:8000` API/Calibration · `:8501` Streamlit |

The site polls `/api/edgesight/status`, which server-side fetches EdgeSight `/health`, `/api/v1/live`, analytics, and device health. CORS on this API also allows direct browser GETs from `:3000` when needed.

## Models pack (segregated, verified core)

Next-integrate weights live under **`models/pack/`** (gitignored binaries). Production `models/*.pt` paths are unchanged unless you explicitly swap config.

```bash
# Download verified core pack (~1GB; idempotent; no buffalo_l)
python3 scripts/download_pack_models.py
# or: bash models/pack/download.sh

# Optional Docker mount of pack inside edge-analyzer
docker compose -f docker-compose.yml -f docker-compose.pack.yml up -d
# → /app/models/pack/...
```

Verified layout: `01-detection/` · `02-tracking/` (algorithms only) · `03-reid/` · `04-face-attr/` · `05-open-vocab/` · `06-shelf/` — see `models/pack/README.md`.

Honest claims: YuNet = redaction/gating not ID; ReID = session-scoped soft body embeddings (default-off); shelf = YOLO-World / YOLOE prompts, not POS SKUs.

## CLIP weights mount (YOLO-World text encoder)

Host path `weights/clip/ViT-B-32.pt` (gitignored; ~350MB) is mounted into the edge container:

| Host | Container | Compose |
|------|-----------|---------|
| `./weights` | `/app/weights:ro` | `docker-compose.yml` → `edge-analyzer` |
| env | `CLIP_WEIGHTS_PATH` (default `/app/weights/clip/ViT-B-32.pt`) | same service |

If `weights/` is missing on disk, create it and place `ViT-B-32.pt` before expecting in-container CLIP / YOLO-World class encoding. Pack overlay (`docker-compose.pack.yml`) is separate and optional.

## Run together

```bash
# Terminal A — EdgeSight (this repo)
cd ~/Desktop/ad-labs-project/repos/ADLabs-dev
git checkout mefake/integration
docker compose up -d
# optional: docker compose -f docker-compose.yml -f docker-compose.pack.yml up -d

# Terminal B — website
cd ~/Desktop/ad-labs-project/repos/adlabs
git checkout mefake/integration
npm install && npm run dev   # http://localhost:3000
```

Open `/dashboard` → chip **EdgeSight live** when Docker is healthy. Sidebar is **segregated** (same DashboardPage chrome — extend, don’t redesign):

1. **Calibration / Live ops** → EdgeSight live (calib + Streamlit embeds)  
2. **Model-backed intel** → Models & EdgeSight (best models from plans + pack weights)  
3. Existing Live now / Intelligence / Performance screens — layout unchanged  

Best-model names come from Desktop `models/` pack + Project store `docs/models-to-integrate-*` + **`docs/full-scope-implementation-checklist.md`**. Pack downloads: yolo26n + OSNet-x0.25; production stack via `python scripts/download_models.py` (includes **yolo26s** + enrichment). Enrichment tier (pose / YuNet / age-gender / YOLO-World / groups) is on **`mefake/integration`**. Multi-cam ReID remains Future — see `docs/multicam-realtime-sync-plan.md` in the Project store.

Calibration Studio (`:8000`) exposes multi-cam strip, tripwire/dwell/queue/staff draw, live queue KPIs, and a model-status HUD with Live / Partial / Future badges (no fake ReID numbers).

## Git rules

- Review **`mefake/integration`** on **`mefake10000-debug/ADLabs-dev`** only (base: `id-switch-detector-staff-zones`).
- Do **not** push or merge to `rajendrac3/ADLabs-dev` `main` or `NuclearQuince/adlabs` `main`.
- Pushes: **`mefake10000-debug` only**.
