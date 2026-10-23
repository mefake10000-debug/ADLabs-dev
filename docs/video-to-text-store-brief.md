# Video → text: store brief + journey layout health

Convert CV footage + `/api/v1/live` metrics into **plain text a store owner understands** — no fake ledgers, no invented visits.

## Live store brief (portal)

Template bullets (3–6) from real live fields only:

| Bullet | Source |
|--------|--------|
| In / present / out | `total_visitors` · `people_now` · `total_exits` |
| Queue | `queue_length` · `queue_alert_active` · `avg_queue_wait_seconds` |
| Journey gaps | `journey.summary.missing` · `journey.summary.dead_zone` · stage labels |
| Dwell / engagement | `avg_dwell_seconds` · `engagement.engaged_ratio` (omit if null) |
| Offline | connectivity — never invent “demo store” copy |

Portal: `LiveStoreBrief` on `/dashboard/live` (video panel).

## Service journey (buffet → retail path)

Configurable labels: `configs/journey_stages.json`.

| Stage id | Buffet label | Retail map |
|----------|--------------|------------|
| `welcome_drink` | Welcome drink | Entrance welcome |
| `starter` | Starter | Front aisle |
| `appetizer` | Appetizer | Mid-floor browse |
| `main` | Main | Hero / focal |
| `dessert` | Dessert | Impulse / near checkout |
| `fruit` | Fruit | Exit / farewell |

### Field map — `GET /api/v1/live.journey`

```json
{
  "metaphor": "buffet",
  "stages": [
    {
      "id": "welcome_drink",
      "label": "Welcome drink",
      "retail_label": "Entrance welcome",
      "calibrated": false,
      "status": "missing|dead_zone|live",
      "dead_zone": false,
      "visits": 0,
      "occupancy": 0,
      "avg_dwell_seconds": 0.0,
      "traction_score": 0.0,
      "zone_ids": [],
      "zone_names": [],
      "how_to_implement": "…",
      "setup_href": "/dashboard/live?panel=calib"
    }
  ],
  "summary": { "stage_count": 6, "calibrated": 0, "missing": 6, "dead_zone": 0, "live": 0 }
}
```

| Status | Meaning |
|--------|---------|
| **missing** | No zone name/tag matched this stage |
| **dead_zone** | Zone marked but cold (occupancy/visits/dwell ≤ thresholds, default 0) |
| **live** | Marked with visits, dwell, or occupancy |

Matching: zone `name` / `id` contains a stage tag (case-insensitive), or `journey_stage` / `stage_tag` on `cameras.yaml` dwell zones.

## Accounting complete view (FUTURE)

Portal card only — describes the **intended** CV ↔ accounting join (sales vs layout spread / missing journey stages). Integration stub interface:

| Stub | Purpose |
|------|---------|
| `POST /api/v1/accounting/link` (FUTURE) | Bind POS/daybook export id → store_id |
| `GET /api/v1/accounting/spread` (FUTURE) | Compare SKU/category sales vs journey stage traction |
| Join key | Time window + category/zone tag — **not** face ID |

No fake ledgers ship today. Badge: **FUTURE**.

## URLs

| | |
|--|--|
| Live hub | http://localhost:3000/dashboard/live |
| Set up zones | http://localhost:3000/dashboard/live?panel=calib |
| Edge live JSON | http://localhost:8000/api/v1/live |
| Stage config | `configs/journey_stages.json` |

## Sample brief lines (when EdgeSight is live)

- `In 12 · present 3 · out 9 this session.`
- `Queue 2 · no congestion alert.`
- `Journey: 4 stages missing · 1 dead zone (Welcome drink).`
- `Avg dwell 18s · engaged ratio 0.42.`

(When offline: only connectivity lines — never demo KPIs.)
