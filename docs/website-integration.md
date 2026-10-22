# Website live-dashboard integration

**Friend review branches (mefake fork only — never push `rajendrac3` main):**

| Repo | Branch names (same tip) | Base |
|------|-------------------------|------|
| ADLabs-dev | **`integration`** · **`mefake/integration`** | `id-switch-detector-staff-zones` |
| Website (adlabs) | **`mefake/integration`** | live EdgeSight + models + calib blend |

## What this enables

The Next.js site (`~/Desktop/ad-labs-project/repos/adlabs`, branch `mefake/integration`) blends the marketing dashboard at **http://localhost:3000/dashboard** with live EdgeSight:

| Surface | URL |
|---------|-----|
| Site dashboard | http://localhost:3000/dashboard |
| Models & EdgeSight | http://localhost:3000/dashboard → sidebar **Models & EdgeSight** |
| Calibration / Live ops | http://localhost:3000/dashboard/live |
| EdgeSight API / Calibration Studio | http://localhost:8000 |
| Streamlit ops UI | http://localhost:8501 |
| Site proxy (preferred) | http://localhost:3000/api/edgesight/status |
| Health proxy | http://localhost:3000/api/edgesight/health |

The site polls `/api/edgesight/status`, which server-side fetches EdgeSight `/health`, `/api/v1/live`, analytics, and device health. CORS on this API also allows direct browser GETs from `:3000` when needed.

## Models pack (segregated)

Next-integrate weights live under **`models/pack/`** (gitignored `.pt` files). Production `models/*.pt` paths are unchanged.

```bash
# Download pack weights (idempotent)
python scripts/download_pack_models.py
# or: bash models/pack/download.sh

# Optional Docker mount of pack inside edge-analyzer
docker compose -f docker-compose.yml -f docker-compose.pack.yml up -d
# → /app/models/pack/...
```

Folder layout: `01-detection/` · `02-tracking/` · `03-reid/` · `04-attributes/` · `05-seg/` — see `models/pack/README.md`.

## Run together

```bash
# Terminal A — EdgeSight (this repo)
cd ~/Desktop/ad-labs-project/repos/ADLabs-dev
git checkout integration   # or mefake/integration
docker compose up -d
# optional: docker compose -f docker-compose.yml -f docker-compose.pack.yml up -d

# Terminal B — website
cd ~/Desktop/ad-labs-project/repos/adlabs
git checkout mefake/integration
npm install && npm run dev   # http://localhost:3000
```

Open `/dashboard` → chip **EdgeSight live** when Docker is healthy. Sidebar: **EdgeSight live** (calib/ops iframes) · **Models & EdgeSight** (pack + honesty).

## Git rules

- Review on **`mefake10000-debug/ADLabs-dev`** only (`integration` / `mefake/integration`).
- Do **not** push or merge to `rajendrac3/ADLabs-dev` `main`.
