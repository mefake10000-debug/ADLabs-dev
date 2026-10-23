# Cohorts, 3-Month Patterns, Multi-Store Compare, Display Interest

Design contract (siblings: `field-map.md`, `floor-analytics-upgrade.md`, `staff-presence-no-facial-id.md`).
Hard lines: **no facial recognition, no persistent identity** — demographics stay session-scoped, aggregate-only, and are stored ONLY as bucketed cohort counts (never per-person rows). Soft demographic attributes are sensitive: they ship ONLY behind the specific model documented below, with confidence marking, a k-anonymity gate, and a DPIA row. 3-month patterns come from stored rollups, never from live frame guesses.

Status vocabulary (this doc splits it the way the brief asks):
- **LIVE-now** — fires today on verified models/fields.
- **NEEDS-HISTORY** — implementable now, but values are `null`/empty until stored rollups accrue (or calibration lands). Charts show "building history: N of M days", not zeros.
- **PRIVACY-BLOCKED** — technically imaginable but excluded by the privacy line; listed so nobody "discovers" them later.

---

## 1) Metric split

| Metric | Basis | Status | Why as stated |
|---|---|---|---|
| Footfall sessions, entry/exit counts | verified tripwire + active tracks | **LIVE-now** | verified counters with durable wiring |
| Zone dwell, occupancy, queue KPIs, staff presence | verified machinery + in-flight upgrades per their docs | **LIVE-now / PARTIAL** per those docs | each metric carries its own doc's status |
| Category detections (products/labels) | YOLO-World set + CLIP ViT-B-32 (weights verified in pack and used by edge) | **LIVE-now** | categories verified in the running loop |
| Display interest components (dwell, approaches, episodes per shelf face) | verified zone membership; needs shelf-face zone config | **NEEDS-HISTORY** (config-gated) | formula in section 2 |
| Age/gender/cohort mix | **specific model: FairFace ONNX** (present in the verified pack; `models.demographics.enabled: false` today) | **NEEDS-HISTORY** (model gate + k ≥ 10 + rollup accrual) | see DPIA row; estimates only, coarse buckets, confidence marked; empty states in section 4 |
| 3-month patterns (footfall, cohorts, interest, queue service) | daily materialization over stored rollups (`telemetry_rollups` verified accruing; cohort/interest tables NEW) | **NEEDS-HISTORY** | `retention_days: 90`, building-History copy |
| Multi-store side-by-side | cloud compare API over per-store rollups | **NEEDS-HISTORY** (contract in section 3; empty-state-first) | one store on-site today |
| Per-person demographic timeline/journey | — | **PRIVACY-BLOCKED** | would become persistent person profiles |
| Cross-day cohort tracking / identity linkage | — | **PRIVACY-BLOCKED** | cross-day identity is forbidden by design |
| Per-person exports, demographics joined to staff, loyalty/CRM matching | — | **PRIVACY-BLOCKED** | identity by any other name |
| Fine-grained minors analytics | — | **PRIVACY-BLOCKED** | cohorts publish only ≥ 20-merged buckets (default policy below) |
| Demographics for staffing/security decisioning | — | **PRIVACY-BLOCKED** | aggregate shopper insight only |

### DPIA row for soft demographics (required by policy before enabling)

```json
{
  "processing_purpose": "aggregate shopper-cohort insight on the retail floor",
  "data_categories": [
    "face-region crops (in-memory only, never stored)",
    "estimated age bucket, estimated gender presentation, mean estimator confidence"
  ],
  "never_stored": [
    "per-person demographic rows",
    "face images/embeddings",
    "names or identity keys of any kind"
  ],
  "safeguards": [
    "k >= 10 settled views per cohort-cell before any value is published",
    "coarse merged buckets only (config below); fine buckets never published",
    "on-store signage + DPIA sign-off required before models.demographics.enabled flips true",
    "rollups keep bucket COUNTS and sample sizes only"
  ],
  "retention_days": 90,
  "recipients": ["store manager dashboard (aggregate)", "optional head-office compare (aggregate)"],
  "lawful_basis_note": "legitimate-interest with signage and completed DPIA; do-not-locate requests cannot be honored per-person because no person is identified — an optical zone-based pause can stop collection per camera instead"
}
```

### Demographics YAML (gate + buckets)

```yaml
models:
  demographics:
    enabled: false            # flips ONLY after DPIA sign-off; verified config surface
    model: fairface_onnx      # the specific named model
    min_views_per_cohort: 10  # k-anonymity gate (verified discipline)
    publish_buckets:
      age: ["20-34", "35-54", "55+"]   # merged from the model's fine buckets; under-20 never published
      gender: ["women_presenting", "men_presenting", "undetermined"]
    confidence_floor: 0.55    # windows below this mean confidence contribute nothing
analytics:
  demographics_retention_days: 90
```

### Cohort rollup DDL (aggregate-only)

```sql
CREATE TABLE IF NOT EXISTS cohort_rollups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  bucket_start TEXT NOT NULL,                     -- ISO ts, 60-min buckets
  age_bucket TEXT NOT NULL, gender_bucket TEXT NOT NULL,
  settled_views INTEGER NOT NULL,                 -- k >= min_views_per_cohort else row NOT written
  mean_confidence REAL NOT NULL,
  dwell_ms_sum INTEGER,
  computed_at TEXT NOT NULL
);
-- privacy property: no track_id, no person id, no camera-level per-person anything
```

## 2) Display interest: shelf polygon → interest_score (no invented SKUs)

Verified inputs: foot-point zone membership (verified), YOLO-World category machinery + CLIP ViT-B-32 weights (both verified in the running edge), products-window history (verified). SKU recognition is OUT: shelves are labeled with **operator prompts**, and no SKU numbers, prices, or revenue can ever appear from the video side (that joins only via a shelf-plan file or POS later — FUTURE, separate consented intake).

```yaml
cameras:
  - id: cam_entrance_01
    normalized: true
    zones:
      - id: shelf_face_1790733394769
        name: Featured end-cap
        type: shelf_face
        front_line: [[0.10, 0.11], [0.45, 0.09]]         # facing line
        depth_polygon: [[0.10, 0.11], [0.45, 0.09], [0.45, 0.40], [0.10, 0.40]]
        category_source: yolo_world        # or clip
        labels: ["bottles of shampoo", "packaged snacks", "juice cartons"]  # operator words, NOT SKUs
        clip_threshold: 0.22
        analysis_interval_seconds: 10
```

Score pipeline (all components from verified machinery):

```
approaches   = episode count entering depth_polygon                      (verified zones)
dwell_ms     = sum of per-episode front_line presence                    (verified dwell)
label_hits   = frames where YOLO-World label above threshold while a track is inside, OR
               CLIP crop(top-shelf ROI) x label text similarity >= clip_threshold
interest_score_0_100 = round(100 * (0.5 * norm(dwell_ms) + 0.3 * norm(approaches) + 0.2 * mean(label_hits)))
norm(x) = x / rolling 7-day max for this zone     -- relative to itself, never an absolute "truth"
```

- Output JSON is always `{zone_id, labels: [...], interest_score, components: {dwell_ms, approaches, label_hit_rate}, n_sessions, confidence_note}`. `interest_score` prints with `n_sessions`; below `min` sessions (default 10) it stays `null` with "settling" copy — no fabricated percentile.
- Historical spike detection (`DISPLAY_INTEREST_SPIKE` in the alert catalog) stays LIVE on category windows; `interest_score` history accrues into shelf rollups (NEEDS-HISTORY).
- Hard line: a label is a sprayed word, not an SKU. The UI must never show "interest in SKU 88291" — "browsing interest in the shampoo end-cap (operator label)".

## 3) Multi-store sync page: API contract + empty states

Push-based (edge→cloud telemetry already verified); the cloud serves a compare view. Single store on-site today, so the page is **empty-state-first** — no fabricated comparisons.

```
GET /api/v1/multi-store/overview?store_ids=a,b,c&window_seconds=604800
```

```json
{
  "generated_at": "2026-10-23T12:10:00Z",
  "window_seconds": 604800,
  "kpi_keys": ["footfall", "conversion_entry_to_queue", "avg_queue_wait", "abandon_rate",
               "peak_hour_occ", "staff_response_p50", "category_top5"],
  "stores": [
    { "store_id": "store_mumbai_001", "available": true,
      "kpis": {
        "footfall": {"value": 214, "n": null, "note": null},
        "conversion_entry_to_queue": {"value": 0.41, "n": 214, "note": null},
        "avg_queue_wait": {"value_ms": 48210, "n": 96, "note": null},
        "peak_hour_occ": {"value": 27, "occ_basis": "sum_of_cameras", "note": "overlap-FOV double counting documented"},
        "category_top5": {"value": ["packaged snacks", "dairy drinks", "juice cartons"], "note": "operator labels only — no SKUs"}
      },
      "coverage": {"days_with_data": 3, "window_days": 7, "retention_days": 90}},
    { "store_id": "store_delhi_002", "available": false,
      "kpis": null,
      "empty_state": {"reason": "no_device_reported", "copy": "No EdgeSight device has reported for this store yet."},
      "onboarding": ["flash EDGE_CONFIG with store_id=store_delhi_002", "point TELEMETRY_CLOUD_ENDPOINT at this cloud", "confirm camera calibration"]},
    { "store_id": "store_new_003", "available": false,
      "kpis": null,
      "empty_state": {"reason": "insufficient_history", "since_ts": "2026-10-22",
                      "copy": "Store connected — building history. Comparisons appear after 7 full days of rollups."}}
  ]
}
```

Rules: `kpi_keys` is served so the grid renders a fixed column set; every missing value is `null` + a reason — the UI must render "—" / reason copy, never 0. Side-by-side ordering is alphabetical until rankings exist (visual-only ranking is a FUTURE toggle after ethics review of store-comparison optics). Contracts respect each metric's front-doc status (queue metrics PARTIAL until their upgrade ships; demographics only if every store's DPIA+gate is on).

## 4) Dashboard copy — never fake gender/age when the model is offline

Exact strings for the four demographics card states:

- **ONLINE (k satisfied):**
  Title: "Estimated age & gender mix — last 15 min"
  Body: "Women-presenting 58% · Men-presenting 42% (n=57 views, mean conf 0.71)"
  Footnote: "Model estimates on anonymous visits — not facial recognition, not identification. Published only for groups with ≥ 10 settled views."
- **MODEL OFFLINE (`models.demographics.enabled: false` or model load failed):**
  Body: "Age & gender estimates are switched off."
  Sub: "Counts, queues, and safety analytics continue unaffected. No estimates are shown when the estimator is off — we never substitute guessed values."
  (The area shows the honest neutral placeholder, NOT a frozen last age mix.)
- **BELOW-K / insufficient confidence:**
  Body: "Not enough visitors for a publishable estimate yet (needs ≥ 10 settled views at adequate confidence)."
  Sub: "Lower-traffic windows stay blank on purpose. This is a privacy floor, not missing data."
- **WINDOW PARTIAL (camera gap inside the window):**
  Body: "Estimates cover 41 of 60 min in this window (camera gap)."
  Footnote: "Gap periods are excluded rather than back-filled — no patched-up mixes."

Trend charts (3-month): fully empty early days render as gaps with the standing caption "Building history: 3 of 90 days collected. Patterns unlock as rollups accrue — nothing is back-filled." Respect the standing style: honest nulls, never zeros.
