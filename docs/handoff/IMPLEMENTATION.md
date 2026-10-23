# Helper handoff wiring — implementation status

**Edge tip:** `3a75b22` (+ journey-import fix commit) on `cursor/helper-handoff-wire-ec43-v2` / `mefake/integration`  
**Site tip:** `dfa5269` on matching branches  
**Anti-hallucination:** null / omit + PARTIAL/FUTURE badges when not computed. No fake demographics, identity, multi-store, or stop-rate without glass ROI.

**Branch tip:** `cursor/helper-handoff-wire-ec43-v2` → FF `mefake/integration` (EdgeSight). Portal on matching site branch.  
**Anti-hallucination:** null / omit + PARTIAL/FUTURE badges when not computed. No fake demographics, identity, multi-store, or stop-rate without glass ROI.

## LIVE now (this tip)

| Area | Fields / endpoints | Notes |
|------|-------------------|--------|
| API contract | `GET /api/v1/live` + snapshot carry `entrance`, `stop_rate`, `floor`, `staff`, `safety`, `alerts`, `field_status`, enriched `queues[]` | Passthrough from edge snapshot |
| Queue episodes | `queues[].now`, `kpi` (avg/p95), `recent_episodes[]` with `join_ts`/`leave_ts`/`wait_ms` | `abandon` null without `service_point` |
| Floor | `floor.paths_active`, `zone_traction` (U×D×R), `top_routes` | From track foot history + zone membership; empty routes OK |
| Staff | `staff.zones[]` with `staff_present`, `state` | UNCALIBRATED when `expected_on_post` unset — never invent understaffed |
| Safety | `safety.active[]` for density / restricted / exit_corridor / fall-bbox candidate | Only when zone types/caps calibrated; human-review disclaimer |
| Alerts | Catalog loaded; `QUEUE_LENGTH_OVER` fires when deps exist; `GET /api/v1/alerts` | FUTURE catalog rows never fire |
| Display interest | `products_top` unchanged | LIVE when model/history present else PARTIAL |
| ZoneConfig | Accepts `glass`, `exit_corridor`, `restricted`, `aisle` + staff still valid | Staff POST remains 200 |
| Portal | Queue episode table, glass stop-rate card, staff occupancy MVP, catalog alert actions | Honest badges via `data-freshness` |

## PARTIAL

| Area | Why |
|------|-----|
| Stop-rate / glass | No `glass_views` in default cameras.yaml → `entrance.status=FUTURE`, `stop_rate=null` until ROI drawn |
| Queue abandon / service_rate | Needs calibrated `service_point` |
| p95 wait | Needs ≥20 settled episodes |
| Staff `response_time_to_queue` | Empty until durable queue_alert pairing settles |
| Engagement / demographics | Enrichment / k-anon gates unchanged |
| Alerts PARTIAL catalog rows | Shown as pending chips; not fired |

## FUTURE (do not fake)

- LocateAnything-3B (NVIDIA non-commercial) — docs only
- Multi-store compare
- Pose-tier fall, weapons, age-restricted zones
- POS / SKU revenue
- Cross-cam identity fusion
- Vest-color staff ID / named roster

## Speed

- `EDGE_PERF_MODE=fast` path unchanged; glass/floor/queue episode math is lightweight track-state rollups (~1 Hz series, snapshot cadence).
- Heavy enrichment stays async / quality mode.

## Verify

```bash
curl -s http://localhost:8000/api/v1/live | jq '{stop_rate,entrance,field_status,queues:(.queues|length),alerts}'
curl -s 'http://localhost:8000/api/v1/live/snapshot?camera_id=cam_entrance_01' | jq '{floor,staff,safety}'
curl -s http://localhost:8000/api/v1/alerts | jq '{active,partial_catalog:(.partial_catalog|length)}'
# Staff zone POST still 200:
curl -s -X POST http://localhost:8000/api/v1/config/cameras/cam_entrance_01/calibration \
  -H 'Content-Type: application/json' \
  -d '{"zones":[{"id":"staff_zone_1790733394769","name":"Staff Area","type":"staff","polygon":[[126,600],[277,539],[110,179],[3,222],[124,597]]}]}'
```
