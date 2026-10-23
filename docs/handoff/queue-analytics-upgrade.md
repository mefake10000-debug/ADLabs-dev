# Queue Analytics Upgrade — Retail Checkout / Service Lines

Design contract (extends `field-map.md`, `live.schema.json`, `floor-analytics-upgrade.md`; same Save → ~3 s hot-reload flow, verified).
Status labels: **LIVE after implementation** where the verified `QueueAnalyzer` mechanics already exist (queue_length, avg_wait_seconds, alert_active with defaults max_comfortable_queue=4, congestion_threshold_seconds=120, zone_exit_grace_seconds=3.0); **PARTIAL** where evidence-based judgment is required (abandon, service rate); **FUTURE** where the field is new.

Session-scoped track IDs only. No facial recognition. No invented accuracy claims — unknowns are `null` + honest copy, never fabricated numbers.

---

## 1) Per-person queue events

Terms (foot-point mechanics, verified):
- **join_ts** — the timestamp the track's foot-point first sits inside the queue polygon (confirmed track; same membership machinery that already drives zones).
- **leave_ts** — when the foot-point stays outside the polygon beyond `zone_exit_grace_seconds` (3.0 s verified default). A blip outside ≤ grace does NOT end the episode (prevents flicker spikes).
- **wait_ms** = (leave_ts or "now") − join_ts, per episode. In-flight wait keeps growing until exit; completed waits freeze at exit.
- **abandon** — boolean, meaningful ONLY with calibrated service evidence (see below). Without it: `null` and the UI badge says so.

Evidence plan (choose at calibration):
- **service_point calibrated**: an episode counts as **served** if the track came within `service_radius_frac` of the service point during its episode, or exited the polygon *toward/through* the service point side; otherwise the completed episode ends `abandon: true` on both.
- **no service point**: abandoning can't be distinguished from walking up without being served. Both leads end as `abandon: null` with PARTIAL reason "service_point_missing".

Events ride the verified durable channel (`POST /api/v1/telemetry/events`, additive `event` enum — already extended once for glass/stop events):

```json
{
  "store_id": "store_mumbai_001", "device_id": "edge_node_macmini_01",
  "camera_id": "cam_entrance_01", "event": "queue_join",
  "queue_id": "queue_zone_1790217226558", "track_id": 1099,
  "join_ts": "2026-10-23T12:01:33.214Z",
  "queue_length_at_join": 4
}
{
  "store_id": "…", "device_id": "…", "camera_id": "…",
  "event": "queue_leave",
  "queue_id": "queue_zone_1790217226558", "track_id": 1099,
  "join_ts": "2026-10-23T12:01:33.214Z",
  "leave_ts": "2026-10-23T12:07:45.930Z",
  "wait_ms": 372716,
  "outcome": "served",            // served | abandoned | unknown
  "abandon": false,               // null when outcome unknown (no service evidence)
  "service_evidence": "service_point" | "head_exit" | null
}
```

Transient, non-durable companion (same pattern as `glass_stop_reached`): `event: "queue_wait_ms_reached"` fired in-memory the moment an in-flight episode crosses the alert threshold — used for the live "customer waiting too long" badge; not persisted (the durable `queue_leave` carries the truth).

**Episode algorithm (pseudocode)** — hook beside the existing `q.update(customers, frame_time)` call:

```
for each queue q:
    tids_now = {foot_point inside q.polygon}
    for tid newly in tids_now:  emit queue_join(join_ts=now, length_at_join=len(tids_now))
        episodes[tid] = {join_ts: now}
    for tid gone from tids_now beyond grace:
        ep = episodes.pop(tid)
        waited = now - ep.join_ts
        outcome = unknown
        if q.service_point is calibrated:
            came_to_service = any(p close to service_point within radius)  # ep.path points
            exited_via_head   = exit_foot_point closer to service point than to entry centroid
            outcome = served if (came_to_service or exited_via_head) else abandoned
        emit queue_leave(...)
```

Multiple visits merge: re-entry within `revisit_merge_seconds` continues the same episode (one join, one leave) — same rule as zones.

## 2) Aggregate KPIs (per queue, rolling window W default 900 s)

- **avg_wait** — mean of completed episode wait_ms in W. In-flight waits excluded (they are not history yet); displayed separately as "now waiting: n / longest X ms".
- **p95_wait** — 95th percentile of the same completed sample set. Guard: p95 requires ≥ `min_samples_p95` (default 20) completed episodes; otherwise `p95_wait_ms: null` + UI copy "p95 unlocks after 20 settled waits" (k-threshold discipline, no fake percentile).
- **queue_length time series (1 s buckets)** — edge keeps an in-memory ring of the last 300 s: every ~1 s tick writes `{t, length: |tids_now|}`. Served to the dashboard as `series` (max 300 rows); rollups keep 10 s downsample only. Buckets during a camera outage are absent rows (`length` never fabricated for dead time).
- **service rate** — `served / (served + abandoned_true)` over completed outcomes in W, plus `served_per_minute = served_count / (W/60)`. Basis-dependent: with no service_point or zero settled episodes → `service_rate: null` + PARTIAL copy ("abandon not distinguishable without a service point").
- **abandon rate** — `abandoned_true / completed`, same null-rule.

Rollup cadence: stays 10 s, reusing the verified queue columns (`queue_length`, `avg_queue_wait_seconds`, `queue_alert_active`) so history/charts keep working; durable per-episode events feed any later re-aggregation. New durable history table (enabled with this feature):

```sql
CREATE TABLE IF NOT EXISTS queue_rollups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  store_id TEXT NOT NULL, device_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  queue_id TEXT NOT NULL,
  window_seconds INTEGER NOT NULL,
  avg_wait_ms INTEGER, p95_wait_ms INTEGER,   -- NULL when below sample threshold
  completed INTEGER, served INTEGER, abandoned INTEGER,
  service_rate REAL,
  series_300s_json TEXT,                       -- downsampled 1s series tail at flush time
  computed_at TEXT NOT NULL
);
```

## 3) Alert rules (evaluated in-loop, per queue)

| Rule | Condition (verified knobs unless marked NEW) | Fires | Persists until |
|---|---|---|---|
| Wait too long | longest in-flight wait_ms > `alert_wait_ms` (NEW; falls back to verified `congestion_threshold_seconds × 1000` = 120 s) | one dispatch episode at crossing (+ `queue_wait_ms_reached`) | wait clears below threshold − 15 s hysteresis |
| Length too high | `length > alert_length` (NEW; falls back to verified `max_comfortable_queue` = 4) held ≥ `alert_min_length_seconds` (NEW, default 10 s) | dispatch at threshold | length ≤ threshold for 10 s |
| No staff on cue | linked `staff_zone_id` (NEW field) has 0 tagged tracks **and** (wait OR length rule active) held ≥ `no_staff_grace_seconds` (NEW, default 30 s) | escalate to "no staff in linked zone" | staff tagged ≥1 or rule clears |
| Alert resolved | all conditions clear | `queue_alert_cleared` event | — |

Alert events (additive enum): `queue_alert_raised {rule, value, threshold, since_ts}` / `queue_alert_cleared {rule, after_ms}`. Deduped — no re-fire while active; every dispatch writes the durable event so the Alerts feed shows the incident exactly once.

## 4) Exact JSON — `/api/v1/live.queue` + dashboard columns

New read model key (existing top-level `queue_length` / `avg_queue_wait_seconds` / `queue_alert_active` fields stay untouched for back-compat):

```json
{
  "store_id": "store_mumbai_001",
  "generated_at": "2026-10-23T12:10:00Z",
  "window_seconds": 900,
  "queues": [
    {
      "id": "queue_zone_1790217226558",
      "name": "Checkout Queue",
      "camera_id": "cam_entrance_01",
      "now": {
        "length": 3,
        "min_wait_ms": 8120,
        "max_wait_ms": 41230,
        "staff_on_post": 1,
        "staff_zone_id": "staff_zone_1790733394769"
      },
      "kpi": {
        "completed": 13, "served": 12, "abandoned": 1, "unknown_outcome": 0,
        "avg_wait_ms": 96540,
        "p95_wait_ms": 148700, "p95_available": true, "p95_sample_count": 13,
        "service_rate": 0.92, "service_rate_basis": "service_point",
        "waiting_now": 3
      },
      "series": [
        { "t": "2026-10-23T12:05:01Z", "length": 2 },
        { "t": "2026-10-23T12:05:02Z", "length": 3 }
      ],
      "alerts": [
        { "rule": "wait_over", "active": true, "since_ts": "2026-10-23T12:06:11Z",
          "value_ms": 41230, "threshold_ms": 300000, "staff_zone_id": null }
      ],
      "recent_episodes": [
        { "track_id": 1099, "join_ts": "2026-10-23T12:01:33Z", "leave_ts": "2026-10-23T12:07:45Z",
          "wait_ms": 372716, "outcome": "served", "abandon": false }
      ]
    }
  ]
}
```

Staff zone badge gate (per privacy doc, no identity):

| Column | Source | null-friendly |
|---|---|---|
| `wait_ms` | episode complete | in-flight shows `now - join` + "settling" chip |
| `abandon` | service evidence | `null` → "—" for `unknown` |
| `p95_wait_ms` | ≥ min_samples | `null` → "p95 unlocks after 20 settled waits" |
| `service_rate` | base evidence | `null` → "—" |
| `staff_on_post` | presence count inside the linked staff zone (geometry tagging) | — |

Old data without episodes still renders (history shows table rows using rollup columns only, marked "rollup-only"); gaps render blank first (no fabricated zeros).

Dashboard table columns (Queue panel):

| Column | JSON path | Notes |
|---|---|---|
| Time | `series[last].t` (or `generated_at`) | — |
| Camera | `queues[].camera_id` | — |
| Queue | `queues[].name` | — |
| Length now | `queues[].now.length` | badge "►" red/amber/green from `alert_length` |
| Now waiting | `queues[].now.length` marker + `kpi.waiting_now` | same number, different label |
| Longest wait now | `queues[].now.max_wait_ms` (+ `min_wait_ms` tooltip) | — |
| Avg wait (W) | `queues[].kpi.avg_wait_ms` | window shown in header |
| p95 wait (W) | `queues[].kpi.p95_wait_ms` | `null` → "settling" chip per threshold |
| Served (W) | `queues[].kpi.served` | — |
| Abandoned (W) | `queues[].kpi.abandoned` | — |
| Abandon rate | `abandoned / completed` (client-side) | hidden when `service_rate_basis: null` |
| Service rate | `queues[].kpi.service_rate` | hidden when `null` |
| Active alert | `queues[].alerts[].rule` pill | active rules listed |
| Staff on post | `queues[].now.staff_on_post` | — |

## 5) Calibration fields (studio + yaml)

```yaml
cameras:
  - id: cam_entrance_01
    normalized: true
    zones:
      - id: queue_zone_1790217226558
        name: Checkout Queue
        type: queue
        polygon: [[0.15, 0.31], [0.34, 0.38], [0.32, 0.55], [0.14, 0.49]]   # existing semantics
        # NEW — service-line upgrades:
        service_point: [0.30, 0.56]      # normalized; click at the checkout head/counter; optional
        service_radius_frac: 0.05        # evidence radius around service_point (default 0.05)
        alert_wait_ms: 300000            # wait rule (falls back congestion_threshold_seconds)
        alert_length: 6                  # length rule (falls back max_comfortable_queue)
        alert_min_length_seconds: 10
        staff_zone_id: staff_zone_1790733394769
        no_staff_grace_seconds: 30
        expected_wait_seconds: 240       # sanity target, shown as gray goal line on the chart (optional)
```

`analytics` block additions:

```yaml
analytics:
  queue:
    min_samples_p95: 20
    alert_hysteresis_seconds: 15
    revisit_merge_seconds: 1.5
```

Studio steps (same Save → hot reload, verified):
1. Camera → Queue zone polygon (≥3 points, tight over the actual standing line, not aisle traffic — same guidance as `calibration-floor-queue-staff.md`).
2. Service point (optional): click the checkout head; radius slider previews the evidence circle. Omitted → abandon/service stay `null` and cards auto-hide (PARTIAL, no fake split).
3. Link staff zone: dropdown from the camera's existing `type: staff` zones; require non-overlap with the queue polygon (a browsable overlap zone would mis-tag shoppers as staff).
4. Thresholds: `alert_wait_ms`, `alert_length`, `alert_min_length_seconds`, `no_staff_grace_seconds`; `expected_wait_seconds` optional goal line.
5. Live verify: walk the line 30 s with staff on post → expect a `served` episode; walk past the queue without joining (exit within/after grace) → expect join/leave handling per the service-point rule; check `/api/v1/live.queue` → `recent_episodes`, then Save.

Validation rules: simple non-self-intersecting polygons only; `0.02 ≤ service_radius_frac ≤ 0.2`; `expected_wait_seconds ≤ alert_wait_ms/1000` triggers a yellow "goal never alerts" note; normalized coords only — pixel-only cameras refuse these keys.

Reasonable defaults are derived from verified knobs, nothing else; store owners tune per lane.
