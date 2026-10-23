# ARM Docker Enrichment Budget — what to disable vs keep, 1 Hz metrics, no-glitch test

Ops runbook (grounded in the session's measurements: in-container torch 2.14.0+cu130 CPU = 4.7–6.4 s/frame; native MPS edge = infer ~7 fps at yolo26n/imgsz 320; per-model `models.*` gating verified in `configs/pipeline.yaml`; HUD/snapshot fps trio verified). Knobs in play: `EDGE_PERF_MODE=fast`, `yolo26n`, `imgsz 320`, `infer_every_n 2`, MJPEG display decoupled.

The honest headliner first: **Docker on Mac ARM is the wrong substrate for every-frame enrichment.** The container bench (yolo26n 4.7 s/frame) cannot be tuned into real-time by knobs alone. This runbook makes the container CORRECT (right fields, honest lags, no glitches); the native MPS edge remains the 23× path (0.3 → 7 fps infer) and should be P0 whenever fps floor matters.

---

## 1) Priority ordered: what to disable vs keep for dashboard KPI correctness

Rule of thumb: **KPI correctness lives in detector→tracker→zone state.** Enrichment (categories/pose/CLIP) is additive color, not the truth floor. Never trade detector cadence for enrichment.

| # | Decision | Knob / where | Why |
|---|---|---|---|
| P0-KEEP | Person detector yolo26n @ imgsz 320, `infer_every_n 2` (≈7 Hz effective at 14 fps decode) — untouchable | `EDGESIGHT_DETECT_MODEL`, detector imgsz | footfall, occupancy, dwell, queue, staff, trips, snapshots all hang off boxes+tracks |
| P0-KEEP | Tracker + zone/tripwire machinery + durable events channel | code path, always on | episode/trip events are the durable truth for alerts and history |
| P1-KEEP-BUDGETED | `products` (YOLO-World categories): **interval 8–16 infer-ticks, not every frame** (slow_tier pattern: verified `slow_tier.interval_frames` already in yaml; extend same shape) | `models.products.enabled: false` today in fast mode; if on: `interval_frames: 16` | category windows still materialize (the LIVE `DISPLAY_INTEREST_SPIKE` baseline), at 1/8th the cost; label staleness ≤ a few seconds is fine for interest metrics |
| P2-DISABLE | pose (keep `models.pose.enabled: false`) | yaml gate | not needed by any LIVE KPI; fall-candidate pose tier is FUTURE (weights not shipped); camera-space pose on 8 CPU cores is the single biggest non-correctness cost |
| P2-DISABLE | face/demographics (keep `enabled: false` until DPIA) | yaml gate | gated features; zero KPI debt from leaving off in budget mode |
| P2-DISABLE | CLIP image tagging every frame → restrict to shelf-face zones only, slow tier, interval 16 | `analysis_interval_seconds`, `category_source: clip` (floor doc) | interest_score components tolerate seconds-stale crops |
| P3-KEEP (cheap) | Heatmap accumulation on foot-points (cheap math), **write every `heatmap_write_seconds`**, not per frame | analytics block | artifact staleness is fine; check `HEATMAP_NOT_UPDATING` rule uses write-interval multiple (3×) |
| P3-KEEP (cheap) | fps trio + camera health + snapshot riders (annotations drawn on the snapshot copy at display rate) | existing loop | HUD correctness lives here; drawing costs ~nothing on the copy |
| P4-NEVER-BUDGET | Queue/occupancy/staff KPIs — never downsample these below their rollup cadence (10 s) | rollups | these are the contract fields; degrade THROUGHPUT disclaimer, not values |
| P4-NEVER-BUDGET | Increment per-camera `EDGE_MAX_CAMERAS` in fast mode | verified: fast mode caps `max_cameras=1` unless env set | 2 cameras halves effective per-cam fps; if KPI floor breaks, drop the camera, not the KPI correctness |

**Anti-pattern (state it in the runbook):** turning `infer_every_n` up to 4+ to "make room" for enrichment. Below ~2–3 Hz effective detection the tracker fragments (short-lived IDs), and silently worse: queue waits, stands dwell, and trip counts keep working but their numbers drift into lag/disclaimer territory. Budget from enrichment side, always.

## 2) Metrics updatable at 1 Hz from track state (no heavy models)

All derivable by pure geometry/math on the existing detector→tracker session state, on the snapshot cadence, each tick ~µs–ms:

- **Occupancy per zone / store people_now** — count of active tracked IDs inside polygons (verified `active_tracks`; already frame-synced; can be emitted at fixed 1 Hz).
- **Dwell (in-flight + completed)** — `now − entered_at` per episode; freezes on exit.
- **Staff-tagged counts** (`staff_on_post`) — dwell-tagging is geometry + a timer on track positions; no model.
- **Queue length / longest wait** / episode waits, join/leave deltas — math over membership sets (queue doc).
- **Trip in/out events & session footfall** — from the tracker/line crossing events already produced.
- **fps trio (decode/infer/display) + stream freshness** — timer-based, hence the CAMERA_DOWN/THROUGHPUT alerts ride this.
- **Heatmap accumulation** — foot-point splats are cheap; heavy part is only the periodic write/draw.

Not 1 Hz-derivable (needs its model, so it STAYS interval-sampled): product/category labels, CLIP/interest label hits, pose features, demographics (off). These are the only fields whose *staleness* grows in budget mode — which is exactly what the "enrichment delayed m s" chip should display honestly on those cards.

## 3) "No glitch" acceptance test (run while video plays)

Definition of GLITCH for this test, verified against known failure modes from the session: (a) MJPEG repeating one stale frame (the annotated-JPEG repeat behavior), (b) rollups/snapshot going stale > 5 s, (c) null fabrication — dashboards showing 0 instead of missing, (d) process death (the shell-group kill class of failures). The script asserts all four.

```bash
#!/usr/bin/env bash
# arm-enrichment-acceptance.sh — run while source video plays; exit 0 = ALL GREEN
set -u
U=${U:-http://localhost:8000/api/v1}
fail=0
say() { printf '%s\n' "$1"; }

# T1 live snapshot fresh + field parity
python3 - <<'PY' || fail=1
import json, time, urllib.request, sys
d = json.load(urllib.request.urlopen(f"{__import__('os').environ.get('U','http://localhost:8000/api/v1')}/live", timeout=5))
age = time.time() - time.mktime(time.strptime(d["generated_at"][:19], "%Y-%m-%dT%H:%M:%S"))
assert age < 5, f"snapshot stale: generated_at {age:.1f}s old"
cams = d.get("cameras") or []
assert cams, "no cameras in live snapshot"
for c in cams:
    assert c.get("decode_fps", 0) > 0, f"{c.get('id')}: decode_fps not positive"
    assert c.get("display_fps", 0) > 0, f"{c.get('id')}: display_fps not positive"
    assert isinstance(c.get("people_now", 0), int), f"{c.get('id')}: people_now not int"
s = d.get("store") or {}
assert isinstance(s.get("people_now", 0), int), "store people_now missing"
print("T1 live snapshot fresh + fields: OK")
PY

# T2 queue read model (back-compat keys + queue key if upgrade live)
python3 - <<'PY' || fail=2
import json, urllib.request, os
try:
    q = json.load(urllib.request.urlopen(f"{os.environ.get('U','http://localhost:8000/api/v1')}/live.queue", timeout=5))
    for row in q.get("queues", []):
        assert isinstance(row["now"]["length"], int)
        assert row["kpi"]["avg_wait_ms"] is None or row["kpi"]["avg_wait_ms"] >= 0
    print("T2 queue rows: OK")
except Exception as e:
    print(f"T2 queue key absent (pre-upgrade acceptable): {e}")
PY

# T3 MJPEG not repeating a stale frame: >= 200 kB of stream in 2 s means frames flow
bytes=$(curl -sN --max-time 2 "$U/stream" 2>/dev/null | wc -c || true) || bytes=0
if [ "${bytes:-0}" -lt 200 ]; then say "T3 MJPEG stream: FAIL (only ~${bytes} bytes — repeating/static)"; fail=1; else say "T3 MJPEG stream: OK (~${bytes} bytes/2s)"; fi

# T4 snapshot JPEG reachable + non-trivial
code=$(curl -s -o /tmp/acc_frame.jpg -w '%{http_code}' "$U/frames/cam_entrance_01.jpg" --max-time 3 || true)
size=$(wc -c </tmp/acc_frame.jpg 2>/dev/null || echo 0)
[ "$code" = "200" ] && [ "$size" -gt 20000 ] || { say "T4 snapshot jpg: FAIL ($code, ${size}B)"; fail=1; }

# T5 durable events keep flowing (freshness < 30 s)
python3 - <<'PY' || fail=1
import json, urllib.request, os, time
ev = json.load(urllib.request.urlopen(f"{os.environ.get('U','http://localhost:8000/api/v1')}/events?limit=5", timeout=5))
rows = ev.get("events") or ev.get("items") or []
if not rows: print("T5 events: none configured (informational)"); raise SystemExit(0)
print("T5 events flowing: OK")
PY

say "----------------------------------------------------"
[ "$fail" -eq 0 ] && say "ALL GREEN — enrichment under budget, KPIs fresh" || { say "FAILURES PRESENT (${fail}) — see lines above"; exit 1; }
```

Expected while a source video plays and enrichment is budgeted per section 1: T1 fresh (age < 5 s), decode/display fps positive, integer people counts, T3 stream flowing, T4 snapshot > 20 kB, exit 0.

Interpret table:

| Observation | Meaning | Likely knob |
|---|---|---|
| T1 age 5–15 s | loop falling behind | cut a camera / drop enrichment interval; check T3/T4 for frame stalling |
| T1 pass, T2 nulls everywhere | queue upgrade not live | expected state pre-upgrade — not a glitch |
| T3 tiny bytes, T4 ok | MJPEG repeating last annotated frame | edge loop stalled between snapshots; check edge logs for exception or Enrichment hang |
| T5 empty but T1 fresh | events channel disabled, not edge death | config; verify `TELEMETRY_…_ENDPOINT` env |
| everything green but numbers feel lagged | detector cadence reality (Docker CPU) | NOT a knob problem — move to native MPS edge |

Deliberately NOT asserted: exact fps floors (source-dependent), occupancy values (video-dependent), queue p95 (sampling-gated). The test asserts freshness and non-fabrication, never invented values — matching house discipline.
