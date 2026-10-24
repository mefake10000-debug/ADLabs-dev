# Helper AI handoff — dashboard field contracts

Drop consumed by the EdgeSight + portal wiring agent. **Rule:** real fields or honest LIVE / PARTIAL / FUTURE badges — never fabricated age/gender/identity/multi-store/stop-rate.

## Files

| File | Purpose |
|------|---------|
| `field-map.md` | Verified section → JSON path → status |
| `live.schema.json` | Payload schemas for live / snapshot / telemetry |
| `privacy-badge-matrix.md` | Per-section badge copy |
| `calibration-entrance.md` | Entrance camera tripwire / zones |
| `calibration-entrance-glass-workflow.md` | Glass ROI + stop-rate design |
| `calibration-floor-queue-staff.md` | Floor / queue / staff zone guide |
| `floor-analytics-upgrade.md` | Paths, zone sequences, traction |
| `queue-analytics-upgrade.md` | join_ts / leave_ts / wait_ms / p95 |
| `alerts-catalog-retail-grocery.json` | Alert catalog (LIVE gated) |
| `alerts-catalog-retail-grocery.csv` | Same catalog CSV |
| `alerts-retail.json` | Retail intel + alerts contract notes |
| `staff-presence-no-facial-id.md` | Staff MVP without FR |
| `safety-analytics-retail-floor.md` | Safety operational aids |
| `demographics-cohorts-multi-store.md` | k-anon PARTIAL / multi-store FUTURE |
| `competitor-parity-field-stubs.md` | Portal card → live keys |
| `arm-enrichment-budget-runbook.md` | Fast vs quality enrichment budget |
| `IMPLEMENTATION.md` | What this tip wired LIVE vs still FUTURE |
| `consolidation-manifest.md` | Source commits, migration paths, and exclusions |
| `branch-inventory.md` | Reviewed branch locations and preservation status |
| `foundation-audit.md` | Validation results, security limits, and blockers |
| `model-runtime-inventory.md` | Configured vs loaded/inferred model status |
| `final-consolidation-status.md` | DONE/PARTIAL/BLOCKED checklist for delivery |

## Local URLs

- Portal: http://localhost:3000/dashboard · http://localhost:3000/dashboard/live
- Live JSON: http://localhost:8000/api/v1/live
- Snapshot: http://localhost:8000/api/v1/live/snapshot?camera_id=cam_entrance_01
- Alerts: http://localhost:8000/api/v1/alerts
- Floor: http://localhost:8000/api/v1/analytics/floor
