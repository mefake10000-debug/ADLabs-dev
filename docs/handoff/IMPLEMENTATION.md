# Helper handoff wiring — implementation status

**Edge tip:** `cursor/todos-closeout-0ad1` → FF `mefake/integration` (+ friend-review aliases)  
**Anti-hallucination:** null / omit / measured 0 + PARTIAL/FUTURE/EMPTY badges when not computed. No fake demographics, identity, multi-store, or stop-rate without glass ROI.

## Checklist

| Area | Status | Notes |
|------|--------|--------|
| Live API contract (`entrance`, `floor`, `staff`, `safety`, `alerts`, `queues[]`, `field_status`) | ✅ LIVE | Passthrough from edge snapshot |
| Glass stop-rate compute | ✅ LIVE when ROI; FUTURE null without | Mark glass: zone type `glass` or `glass_views[]` — see `calibration-entrance-glass-workflow.md` |
| Queue length / wait / episodes | ✅ LIVE | join/leave episodes with wait_ms |
| Queue abandon / service_rate | ✅ when `service_point`; else PARTIAL null | Measured 0 when calibrated but no settled outcomes |
| Queue p95 | ✅ when ≥20 settled; else EMPTY null | `p95_note` explains sample gate — never fake percentile |
| Staff presence zones | ✅ LIVE | Geometry sticky tag; no facial ID |
| Staff `response_time_to_queue` | ✅ when alert/join + linked staff zone settles; else null | Median of settled `queue_response[]` |
| Alerts catalog + QUEUE_LENGTH_OVER | ✅ LIVE | FUTURE catalog rows never fire |
| Floor paths / traction | ✅ LIVE / EMPTY | From track foot history |
| Display interest `products_top` | ✅ / PARTIAL | When model/history present |
| RF-DETR selectable path | ✅ code; weights OFF/PACKED | One-command: `python3 scripts/download_pack_models_phase2.py --download --only rfdetr-nano --min-free-gb 1` |
| Multi-cam frame-accurate sync / ReID fusion | FUTURE | Plan only; fast single-cam default |
| LocateAnything-3B | FUTURE | Docs only — do not download |
| Accounting CV↔POS join | FUTURE | Stub card |
| Moondream shelf QA | FUTURE | Nightly stub |
| Demographics / enrichment | GATED / PARTIAL | Fast mode off |
| Face ID / named roster | FUTURE | Never |

## LIVE now (this tip)

| Area | Fields / endpoints | Notes |
|------|-------------------|--------|
| API contract | `GET /api/v1/live` + snapshot | Honest badges via `field_status` |
| Queue episodes | `queues[].now`, `kpi`, `recent_episodes[]` | abandon null without `service_point` |
| Staff | `staff.zones[]`, `staff.response_time_to_queue`, `queue_response[]` | Null until linked zone + arrival |
| Glass | `entrance.stop_rate` | null FUTURE without ROI; 0 LIVE with ROI empty |
| Portal | Retail intelligence Entrance/Queue/Staff cards | Live hub stays light (video + In/Present/Out) |

## FUTURE (do not fake)

- LocateAnything-3B (NVIDIA non-commercial)
- Multi-store compare / multi-cam frame sync
- Pose-tier fall, weapons, age-restricted zones
- POS / SKU revenue join
- Cross-cam identity fusion / vest-color staff ID / named roster
- Moondream nightly shelf QA
- Demographics as LIVE (gated)

## Speed

- `EDGE_PERF_MODE=fast` unchanged; glass/floor/queue/staff math is lightweight.
- Heavy enrichment stays async / quality mode.

## Verify

```bash
curl -s http://localhost:8000/api/v1/live | jq '{stop_rate,entrance,field_status,staff:(.staff| {status,response_time_to_queue,zones:(.zones|length)}),queues:(.queues|length)}'
curl -s 'http://localhost:8000/api/v1/live/snapshot?camera_id=cam_entrance_01' | jq '{floor,staff,safety,entrance}'
curl -s http://localhost:8000/api/v1/alerts | jq '{active,partial_catalog:(.partial_catalog|length)}'
python3 scripts/download_pack_models_phase2.py --only rfdetr-nano   # dry-run
```
