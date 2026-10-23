# Industry use-case modes (EdgeSight + Live hub)

Honest vertical modes on the Live hub. Selector switches KPI grids — **never invents sample data**.

## Endpoints

| Method | Path | Role |
|--------|------|------|
| `POST` | `/api/v1/nfc/tap` | Fashion NFC reader webhook (`product_id`, optional `zone` / `zone_id` / `camera_id` / `tapped_at`) |
| `GET` | `/api/v1/nfc/taps` | Recent taps this session (empty until a real POST) |
| `GET` | `/api/v1/live` | Includes `nfc` + `industry` status map + `zones` / `staff_zones` when snapshot-fresh |

No synthetic taps. Defect % never fabricated.

## Industry → field map

| Industry | KPI | JSON path | Maturity |
|----------|-----|-----------|----------|
| Fashion | NFC taps (session) | `nfc.tap_count_session` | **NEEDS-HARDWARE** until first POST → **LIVE** |
| Fashion | Last product / zone / time | `nfc.recent_taps[0].*` | same |
| Restaurant | Tables occupied | `zones[]` type=dwell · occupancy>0 | **LIVE** with polygons; else **EMPTY** |
| Restaurant | Staff on floor | `staff_now` · `staff_zones[]` | **LIVE** / **EMPTY** |
| Restaurant | Service wait | `avg_queue_wait_seconds` · `queues[]` | **PARTIAL** |
| Restaurant | Food served | — | **FUTURE** (POS) |
| Manufacturing | Line activity | `zones[]` occupancy | **LIVE** / **EMPTY** |
| Manufacturing | Boxes / objects | `products_top[]` · `models.products` | **LIVE** / **PARTIAL** / **EMPTY** |
| Manufacturing | Defects | — | **FUTURE** (no fake rates) |
| Jewelry | Top interaction zone | `zones[]` ranked occupancy·dwell | **LIVE** / **EMPTY** |
| Jewelry | Touch proxy | zone revisits / pose hand-near | **PARTIAL** / **FUTURE** |

`industry` on `/api/v1/live` mirrors these statuses for the portal.

## Connect NFC

```bash
curl -s -X POST http://localhost:8000/api/v1/nfc/tap \
  -H 'Content-Type: application/json' \
  -d '{"product_id":"SKU-RED-TEE-42","zone":"fitting_wall_a","zone_id":"z_fit_a"}'
```

Then open Live → Fashion; taps appear under `nfc.recent_taps`.

## Portal URLs

- http://localhost:3000/dashboard/live
- http://localhost:3000/dashboard/live?industry=fashion
- http://localhost:3000/dashboard/live?industry=restaurant
- http://localhost:3000/dashboard/live?industry=manufacturing
- http://localhost:3000/dashboard/live?industry=jewelry

Persistence: `localStorage` key `adlabs.live.industry` + `?industry=` query.
