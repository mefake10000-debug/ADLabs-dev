# Website live-dashboard integration

Branch: **`mefake/integration`** (based on `id-switch-detector-staff-zones`).

## What this enables

The Next.js site (`~/Desktop/ad-labs-project/repos/adlabs`, branch `mefake/integration`) blends the marketing dashboard at **http://localhost:3000/dashboard** with live EdgeSight:

| Surface | URL |
|---------|-----|
| Site dashboard | http://localhost:3000/dashboard |
| EdgeSight API / Calibration Studio | http://localhost:8000 |
| Streamlit ops UI | http://localhost:8501 |
| Site proxy (preferred) | http://localhost:3000/api/edgesight/status |

The site polls `/api/edgesight/status`, which server-side fetches EdgeSight `/health`, `/api/v1/live`, analytics, and device health. CORS on this API also allows direct browser GETs from `:3000` when needed.

## Run together

```bash
# Terminal A — EdgeSight (this repo)
cd ~/Desktop/ad-labs-project/repos/ADLabs-dev
docker compose up -d

# Terminal B — website
cd ~/Desktop/ad-labs-project/repos/adlabs
git checkout mefake/integration
npm run dev   # http://localhost:3000
```

Open `/dashboard` → chip should read **EdgeSight live** when Docker is healthy. **Models & EdgeSight** nav links to ops (:8501) and API docs (:8000).

## Git rules

- Review branch only: `mefake/integration` on the **mefake10000-debug** fork.
- Do **not** push or merge to `rajendrac3/ADLabs-dev` `main`.
