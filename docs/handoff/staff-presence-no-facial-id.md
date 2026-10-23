# Staff Presence without Facial Recognition

Design contract (extends `field-map.md`, `alerts-catalog-retail-grocery.csv`, `queue-analytics-upgrade.md`).
Status labels: **LIVE** (verified mechanics already in the deployed edge loop) / **PARTIAL** (fires after the named in-flight upgrade ships) / **FUTURE** (never fireable from EdgeSight data). Session-scoped track IDs only, per the privacy badge matrix; the whole point of this doc is to design presence WITHOUT identity.

---

## 0) Honest evaluation of the three options

| Option | What it really uses | Strengths | Failure modes (stated plainly) | Verdict |
|---|---|---|---|---|
| **A — Staff-zone occupancy** | Dwell-based tagging: a track still inside a `type: staff` zone after `staff_min_seconds_in_zone` (verified default 10 s) becomes a sticky session `staff` tag. This machinery is already in the running edge loop. | No new model, no color assumptions, works on the verified tagging path, degrades gracefully (zone empty = nobody on post). | A shopper who lingers 10 s+ inside a badly-placed staff zone gets mis-tagged for that session; loop-footage reclassify quirks are a known test case; counts people, not roles. | **MVP. Sources of mis-tag are configuration problems (zone placement), fixable in calibration; no identity needed.** |
| **B — Wearable/vest color heuristic** | Extra detector head or color-predicted "vest" class over detections. | Interesting when uniforms are truly distinctive. | Custom clothing classes need a real trained head on honest footage — this system ships no such weights today; color/shirt-prediction is unreliable under CCTV lighting and drifts; shoppers wearing similar colors get mis-tagged; invites "AI spotted the red vest" nonsense claims. | **Optional assist ONLY, default OFF** (`analytics.staff.vest_hint.enabled: false`). When enabled, a vest-prediction can *hint* the chip outline ("vest-hint") but may never, by itself, drive `staff_present`, any KPI, or any alert — A remains the sole decision path. Status: FUTURE (needs a trained head we do not ship). |
| **C — Manual roster pin / operator marks** | Operator clicks a track on the overlay during the session and pins it as staff. | Recovers from zone mis-tags instantly; useful the day calibration is wrong. | Two variants: (C1) session-only "pin this track as staff" with NO roster, NO name — safe, adds operator trust; (C2) a real named staff roster mapped to detections — that is named-employee matching, i.e., identity — **forbidden** under the privacy line regardless of option. | **C1 as an operator escape hatch (PARTIAL, session-only, expires with the session).** C2 is out of scope by design (see section 6). |

Decision: **A is the MVP**, C1 is a session-scoped operator override tool, B stays off unless a real, honestly-trained vest head ever exists — and even then it is advisory-only.

---

## 1) MVP (A): zone schema

Existing verified base: `type: staff` zones with `staff_min_seconds_in_zone: 10.0` and sticky session tagging. The upgrade adds coverage targets and reverse links, all normalized coords like the rest of the handoff schemas:

```yaml
cameras:
  - id: cam_entrance_01
    normalized: true
    zones:
      - id: staff_zone_1790733394769        # existing verified id
        name: Checkout back area
        type: staff
        polygon: [[0.58, 0.44], [0.84, 0.44], [0.84, 0.62], [0.58, 0.55]]
        min_dwell_seconds_to_staff: 10      # existing verified knob (staff_min_seconds_in_zone)
        # NEW:
        expected_on_post: 2                 # coverage target for this zone (see understaffed)
        linked_queue_ids: [queue_zone_1790217226558]   # reverse link so queue rows know which staff zone covers them
        # (mirror: queue zone may already carry staff_zone_id from the queue doc; the link may be declared on
        #  either side — studio renders both and refuses a one-sided orphan.)

analytics:
  staff:
    understaffed_grace_seconds: 600        # below-target for this long => understaffed (default 10 min)
    vest_hint:                             # option B — OFF by default, never authoritative
      enabled: false
      # if ever enabled with a real trained class head: outline-only chip, advisory-only, 0 decision weight

crowd_calibration:                         # NEW optional calendar (drives understaffed; absent = understaffed never fires)
  hours: "09:00-21:30"
  windows:
    - { from: "09:00", to: "12:00", expected_on_post: 1 }
    - { from: "12:00", to: "16:00", expected_on_post: 2 }
    - { from: "16:00", to: "21:30", expected_on_post: 1 }
```

Placement rules (fixes A's main failure mode): staff zones go BEHIND tills or in back-of-house pockets where customers do not linger ≥ 10 s; if a queue corridor must overlap a staff zone, shrink the staff zone behind the counter line; studio shows a yellow "overlaprisk" warning when a staff polygon intersects a queue/customer zone. Studio steps: draw zone → set `expected_on_post` → link queues → Save (verified ~3 s hot reload) → self-test by standing in it 10 s.

---

## 2) Dashboard fields: `staff_present`, `understaffed`, `response_time_to_queue`

New read model key (same pattern as `/api/v1/live.queue`; existing `staff_now` in the store row stays for back-compat):

```json
{
  "generated_at": "2026-10-23T12:10:00Z",
  "zones": [
    {
      "id": "staff_zone_1790733394769",
      "name": "Checkout back area",
      "camera_id": "cam_entrance_01",
      "staff_present": 2,
      "expected_on_post": 2,
      "state": "COVERED",                     // COVERED | UNDERSTAFFED | NOT_EXPECTED (outside calendar) | UNCALIBRATED
      "understaffed_since": null,             // ISO ts when below-target streak began
      "linked_queue_ids": ["queue_zone_1790217226558"]
    }
  ],
  "queue_response": [
    {
      "queue_id": "queue_zone_1790217226558",
      "staff_zone_id": "staff_zone_1790733394769",
      "alert_ts": "2026-10-23T12:06:11Z",     // queue_alert_raised (waits/length/announcements per queue doc)
      "first_staff_seen_ts": "2026-10-23T12:06:47Z",
      "response_time_s": 36,
      "basis": "session_track_arrival"        // always "session_track_arrival"; never a name (see section 6)
    },
    {
      "queue_id": "queue_zone_1790217226558",
      "alert_ts": "2026-10-23T11:58:02Z",
      "first_staff_seen_ts": null,
      "response_time_s": null,
      "basis": "no_staff_arrived_in_window"   // honest null: nobody tagged in within the observation window
    }
  ]
}
```

Derivation rules (all session-scoped, all from existing event/rollup plumbing):

- **staff_present** — current tagged-track count in the zone (verified mechanics). 10 s rollup keeps history in a new `staff_on_post` column (rollup pattern already proven).
- **understaffed** — during calendar windows only: `staff_present < expected_on_post` sustained ≥ `understaffed_grace_seconds` → `state: "UNDERSTAFFED"` with `understaffed_since` set; recovers below target − 1 for 2 min. No calendar on file → state `UNCALIBRATED` and the field NEVER evaluates (no invented target). Feeds the alert-catalog rows `STAFF_ABSENT_ZONE_BUSY` / `QUEUE_NO_STAFF` through the same dedupe/hysteresis discipline.
- **response_time_to_queue** — for each queue alert episode: `first staff-seen event in the linked zone afterwards` − `alert_ts`. Computed from durable events (queue_alert_raised/cleared + zone enter events) so it survives restarts; settles once a staff tag appears or after a fixed observation window (`response_timeout_seconds`, default 600) → then `null` with honest basis `no_staff_arrived_in_window` (this is a finding, not missing data).
  Needs: the queue alert machinery from `queue-analytics-upgrade.md` (in flight) + verified zone tagging → status PARTIAL until that ships.

Dashboard table columns (Staff panel):

| Column | Field | null-friendly display |
|---|---|---|
| Zone / Camera | `zones[].id/name/camera_id` | — |
| On post now | `zones[].staff_present` | chip green at ≥ expected |
| Target | `zones[].expected_on_post` | `null` → "not set" (UNCALIBRATED) |
| State | `zones[].state` | UNDERSTAFFED tinted amber with `understaffed_since` as "low for 12 min" |
| Queue alerts (W) | count via linked queues | — |
| Median response | median of settled `queue_response[].response_time_s` in window W | `null` → "no settled responses yet" (never a fake 0 s) |
| Open unanswered | queued alerts with `first_staff_seen_ts: null` and window elapsed | — |

## 3) Overlay: how staff look vs customer tracks

Reuse of the verified overlay layers (zone outlines, per-track chips with tracker IDs, legend entries):

- **Customer tracks (default):** the existing neutral track chip with the session numeric ID, e.g. `ID 1099` — thin outline, cool gray.
- **Staff-tagged tracks:** solid **amber** chip labeled `STAFF`, drawn with a heavier border and slightly raised z-order. The numeric session ID is deliberately **suppressed on staff chips** — displaying a persistent number attached to a person the operator can recognize invites "that is Rajesh" inference, which is exactly the identity claim we do not make. Staff chips show `STAFF` only (C1 operator-pin adds the same chip plus a small pin glyph until session end).
- **Zone outlines:** staff zones keep their distinct zone color from the verified `zone_color` legend; the legend entry reads "Staff zone (presence tagging — not identity)".
- **Vest hint (only if ever enabled):** dashed outline marker on the chip, labeled `vest-hint`, explicitly advisory; it may never replace or recolor the amber chip, and the tooltip says so.
- **NO identifiers beyond the chip:** no faces, crops, names, roster text, or cross-camera "same person" ribbons; across cameras a staff-tagged track starts fresh rather than being unified (session-scoped, per camera).
- Escape hatch: an operator role can toggle a session track's chip between CUSTOMER and STAFF (C1) — change is logged in a session events stream with `{camera_id, track_id, from, to, ts}` and dies with the session. No persistence, no roster, no name fields — the UI must not have fields for them.

## 4) What we must NOT claim (hard lines)

- **No facial recognition, ever** — no face embedding, no face crop storage, no gallery from the Re-ID research models; OSNet, if one day wired, stays session-scoped cross-CAMERA only and never person-identity.
- **No named-employee matching.** The system measures presence, not people. Roster names, shift attendance, "Rajesh was at till 3 from 09:14" style statements are out of bounds — the data simply has no lawful or honest basis for them.
- **Presence is not attendance.** `understaffed` is an operational nudge ("zone under target for 10 min"), not evidence for HR/performance action; the UI copy must say operational guide.
- **No cross-day or cross-store continuity** of any staff track; sessions end with the stream.
- **No demographic or 6th-sense inferences about staff or shoppers** in this feature (age/gender/etc. stay out of staff presence entirely).
- **No accuracy theater for option B**: no "99% vest detection" claims; if a vest head is ever trained, its real measured precision/recall on honest footage gets published next to an always-visible advisory-not-authoritative badge — and until then, the option stays off.
- **No claims from NOT_REASONED footage**: what the operator sees on the overlay is detection-dependent; if throughput degrades (`MODEL_THROUGHPUT_LOW`), presence numbers lag — cards show the "counts may lag" state instead of implying real-time truth.

## 5) Guardrails, tests, and honest caveats

- Operator verify walkthrough (same discipline as the other handoff docs): stand in the zone 10 s → amber chip within grace; step out → chip clears at session tag decay; mis-tag a lingering shopper → fix zone polygon in studio (configuration problem, stated as such); run the queue-no-staff drill → `response_time_s` settles with a real timestamp.
- Loop-video caveat (known from testing footage): sustained loops can re-tag; the sticky session tag makes it stable within a visit — treat reclassification jitter as a test case, not a hidden one.
- Mis-tag bias is ambient: the only dereferencable fact in the system is "a person, session-tagged staff, present in zone X for T s". Any UI word implying more than that is a spec violation.
- Everything in this doc degrades to honest nulls rather than fabricated staff numbers — including during camera outages, where the card shows NO DATA like every other live panel.
