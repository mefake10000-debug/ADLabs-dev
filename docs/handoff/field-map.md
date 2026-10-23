# Dashboard Field Map — AD Labs EdgeSight

Verified against the running stack (native MPS edge + FastAPI :8000 + Next.js :3000) on 2026-10-23.
Rule of the contract: **every section renders real fields or an honest badge — never fabricated numbers.**

Status legend:
- **LIVE** — real data today from the named pipeline; renders actual values.
- **PARTIAL** — pipeline/model exists but output is suppressed (privacy threshold, enrichment config, calibration absence); UI shows the honest empty state.
- **FUTURE** — no producer deployed yet; the UI shows the agreed empty-state copy, zero fake rows.

## Full field map

| Section | Metric name | JSON path | Source model / pipeline | Update cadence | Status | Privacy note |
|---|---|---|---|---|---|---|
| Entrance | Live occupancy (on-floor customers) | `/api/v1/live: people_now` · `per_camera[].occupancy` | YOLO person boxes + session-scoped ByteTrack IDs (active customers) | frame-synced (~7 Hz JSON; MJPEG per decoded frame) | LIVE | Session-scoped integer track IDs; no identity ever. |
| Entrance | Glass-view annotated video | `/api/v1/stream/{camera_id}` | Annotated MJPEG (boxes, IDs, tripwires, zones, FEED/MODEL fps HUD) | per decoded frame (~13.9 / 11.4 fps seen on MPS) | LIVE | Optional YuNet face redaction; overlays show only counts/IDs. |
| Entrance | Footfall in/out (session) | `/api/v1/live: total_visitors / total_exits` · POST `/api/v1/telemetry: in_count/out_count` | Tripwire line crossings from calibrated camera config | event-driven; 10 s rollups | LIVE | Counts + wire IDs only. |
| Entrance | Footfall history (hourly) | `/api/v1/analytics/summary: hourly_breakdown[]` | Ingested `telemetry_rollups` (10 s rollups → hourly buckets) | 10 s rollups, hourly buckets | LIVE | Aggregate counts only; rows are dated (last 2026-10-23 05:42 era rows included). |
| Entrance | Stop-rate (dwell threshold in entrance zone) | — | Tracker computes stationary seconds; dashboard field not exposed yet | — | FUTURE | Will use zone-dwell aggregates, no identity. |
| Floor | Zone traction (occupancy + avg dwell per zone) | `/api/v1/live/snapshot: zones[] {occupancy, avg_dwell_seconds}` | Zone polygons + track foot-point membership; 10 s rollups | frame-synced snapshot + 10 s rollup | LIVE | Aggregates; no per-person paths persisted. |
| Floor | Traction heatmap | `/api/v1/heatmap/{camera_id}` | Cumulative bbox foot-point density render | periodic (`heatmap_write_seconds`) | LIVE | Pure aggregate pixels; no PII. |
| Floor | Movement routes (OD arcs) | — | No route model deployed | — | FUTURE | Would aggregate zone-to-zone counts only. |
| Floor / Display | Shelf + display category interest | `/api/v1/live: products_top` · `/api/v1/analytics/products: categories[]` | YOLO-World open-vocab boxes + dwell windows | slow-tier cadence (~every 16 processed frames, config) + 10 s rollup | LIVE | Open-vocab display categories, **not** SKUs; no revenue claims. |
| Queue | Queue length + average wait | `/api/v1/live: queue_length / avg_queue_wait_seconds` · `snapshot: queues[]` | Queue-zone occupancy + stationary dwell | frame-synced snapshot; 10 s rollup | LIVE | Aggregate only. |
| Queue | Congestion alert flag | `/api/v1/live: queue_alert_active` · `snapshot: queues[].alert_active` | Comfort threshold on length/wait (default max 4 / 120 s) | 10 s rollup | LIVE | Operational flag only. |
| Queue | Per-counter service timestamps | — | Not modeled | — | FUTURE | Needs counter-level calibration. |
| Alerts | Crossing event feed | `/api/v1/events: events[] {wire_id, track_id, direction, event_timestamp}` | Tripwire crossings persisted durably | event-driven | LIVE | Session-scoped `track_id`; no identity. |
| Alerts | Dwell-spike / lingering alerts | — | No alert rule deployed | — | FUTURE | Would use zone dwell aggregates only. |
| Alerts | Safety alerts (fall / crowd surge) | — | No safety model on node | — | FUTURE | Will never render fabricated alerts. |
| Staffing | Staff now (visible) | `/api/v1/live: staff_now` | Staff-zone geometry + sticky dwell tagging (10 s threshold verified default) | frame-synced snapshot | LIVE | Role-based geometric tag; no biometrics. |
| Store Intelligence | Store occupancy (active) | `/api/v1/live: net_occupancy` (`occupancy_mode: active_tracks`) | Sum of per-camera active customers | frame-synced snapshot; 10 s rollup | LIVE | Overlapping FOVs double-count until consensus ships (documented in `occupancy_note`). |
| Store Intelligence | Net footfall (tripwire net) | POST `/api/v1/telemetry: in_count − out_count` | Tripwire net | 10 s | LIVE | Kept separate from live occupancy by design (documented). |
| Store Intelligence | Multi-store comparison | — | Schema supports `store_id`; second store not deployed | — | FUTURE | Ingest keyed by store_id is ready. |
| Retail Intelligence | Demographic cohorts (age bands, gender split) | `/api/v1/analytics/demographics: demographics {sample_size, age_bands[], gender_split[], publishable}` | Redaction-only face boxes → INT8 age/gender ONNX → k≥10 gate | window-based rollups (10 s) | PARTIAL | k-anonymized; `publishable:false` suppresses display; face ID never stored. |
| Retail Intelligence | Attention (facing / engaged) | `/api/v1/analytics/engagement: avg_attention_score, facing_ratio, engaged_ratio` | Pose + head-pose enrichment | 10 s windows | PARTIAL | Enrichment currently config-off in fast mode; fields stay honest zeros. |
| Retail Intelligence | Groups (people-in-company) | `/api/v1/analytics/engagement: group_count, people_in_groups` | Proximity clustering on tracks | 10 s | PARTIAL | Aggregates only. |
| Retail Intelligence | Phone usage rate | `/api/v1/analytics/engagement: phone_usage_rate` | Pose + head-pose heuristics | 10 s | PARTIAL | Enrichment-gated. |
| Display Interest | Category viewers / detections / dwell | `/api/v1/analytics/products: categories[] {category, viewers, detections, total_dwell_seconds, avg_dwell_seconds}` | YOLO-World open-vocab + dwell windows | slow-tier + 10 s rollup | LIVE | Display interest only; never POS SKUs or revenue. |
| Display Interest | POS / SKU revenue attribution | — | No POS integration | — | FUTURE | Separate, consented integration; would never infer revenue from video. |

## Verified example payloads (from live probes, 2026-10-23)

### GET /api/v1/live (store-level, snapshot-fresh merge)

```json
{
  "store_id": "store_mumbai_001",
  "camera_id": null,
  "total_visitors": 2,
  "total_exits": 2,
  "net_occupancy": 3,
  "people_now": 3,
  "staff_now": 1,
  "avg_dwell_seconds": 25.5,
  "queue_length": 1,
  "avg_queue_wait_seconds": 18.8,
  "queue_alert_active": false,
  "last_updated": "2026-10-23 11:13:33",
  "occupancy_mode": "active_tracks",
  "occupancy_note": "people_now = active customer tracks (matches YOLO overlay). Tripwire IN/OUT are cumulative. Multi-cam still sums cameras.",
  "decode_fps": 13.9,
  "infer_fps": 7.0,
  "display_fps": 13.9,
  "perf_mode": "fast",
  "source": "live_snapshot",
  "models": {
    "person_detector": "yolo26n", "imgsz": 320, "tracker": "bytetrack",
    "infer_every_n": 2, "enrichment": false, "pose": false, "face_boxes": false,
    "products": true, "face_identity": false
  },
  "engagement": { "avg_attention_score": 0.0, "facing_ratio": 0.0, "engaged_ratio": 0.0, "group_count": 0 },
  "cameras": ["cam_entrance_01", "cam_checkout_01"],
  "per_camera": [
    {
      "camera_id": "cam_entrance_01", "occupancy": 3, "queue_length": 1,
      "avg_dwell_seconds": 25.5, "in_count": 2, "out_count": 2,
      "last_rollup_at": "2026-10-23 11:13:31", "infer_fps": 7.0, "source": "live_snapshot"
    }
  ]
}
```

### GET /api/v1/live/snapshot?camera_id=cam_entrance_01

```json
{
  "store_id": "store_mumbai_001",
  "device_id": "edge_node_macmini_01",
  "camera_id": "cam_entrance_01",
  "camera_name": "Main Store Floor & Entrance",
  "timestamp": "2026-10-23 11:13:33",
  "frame_time": 1792734213.31,
  "people_now": 3,
  "staff_now": 1,
  "unique_tracks_today": 26,
  "total_visitors": 2,
  "total_exits": 2,
  "net_occupancy": 3,
  "avg_dwell_seconds": 25.5,
  "queue_length": 1,
  "avg_queue_wait_seconds": 18.8,
  "queue_alert_active": false,
  "decode_fps": 13.9, "display_fps": 13.9, "infer_fps": 7.0, "perf_mode": "fast",
  "engagement": { "avg_attention_score": 0.0, "facing_ratio": 0.0, "engaged_ratio": 0.0, "group_count": 0 },
  "models": { "person_detector": "yolo26n", "tracker": "bytetrack", "enrichment": false }
}
```

### POST /api/v1/telemetry (edge → cloud rollup; written every 10 s)

```json
{
  "store_id": "store_mumbai_001",
  "device_id": "edge_node_macmini_01",
  "camera_id": "cam_entrance_01",
  "timestamp_start": "2026-10-23 11:12:20",
  "timestamp_end": "2026-10-23 11:12:30",
  "in_count": 0,
  "out_count": 0,
  "current_occupancy": 3,
  "avg_dwell_seconds": 17.3,
  "queue_length": 0,
  "avg_queue_wait_seconds": 0.0,
  "queue_alert_active": 0,
  "avg_attention_score": 0.0,
  "facing_ratio": 0.0,
  "phone_usage_rate": 0.0,
  "engaged_ratio": 0.0,
  "group_count": 0,
  "people_in_groups": 0,
  "demographics_json": "{\"sample_size\":0,\"k_anonymity\":10,\"age_bands\":[],\"gender_split\":[]}"
}
```

### POST /api/v1/telemetry/products (edge → cloud display interest; window based)

```json
{
  "store_id": "store_mumbai_001",
  "device_id": "edge_node_macmini_01",
  "camera_id": "cam_entrance_01",
  "windows": [
    { "category": "handbag", "viewers": 47, "detections": 187, "total_dwell_seconds": 766.1, "avg_dwell_seconds": 16.3 }
  ]
}
```

### POST /api/v1/telemetry/events (edge → cloud crossing event) and GET /api/v1/events item shape

```json
{
  "store_id": "store_mumbai_001",
  "device_id": "edge_node_macmini_01",
  "camera_id": "cam_entrance_01",
  "wire_id": "tripwire_1790217578233",
  "track_id": 35,
  "direction": "out",
  "event_timestamp": "2026-10-23 05:41:10",
  "received_at": "2026-10-23 05:41:15",
  "id": 1236
}
```
(`id` and `received_at` are added by the server on read; the POST body omits them.)

## Notes for integrators
- `people_now` / `net_occupancy` = active customer tracks on the floor today (matches the YOLO overlay); tripwire IN/OUT are cumulative session counters. Rollup occupancy for tripwire cameras was fixed this session to use active tracks, so DB → cloud → dashboard now match the HUD.
- `FEED fps` (in the HUD) = `display_fps`, the annotated-JPEG refresh rate users actually see. `MODEL fps` = `infer_fps`, the detection cadence. `decode_fps` is the raw decode rate.
- Historical rows in summary/history/products endpoints are real (collected 2026-10-22 → 05:42 era); today's accrual continues in the same tables.
- Full JSON schemas live in `live.schema.json` next to this file.
