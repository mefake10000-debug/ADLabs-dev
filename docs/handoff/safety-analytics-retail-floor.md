# Safety Analytics for the Retail Floor — person/pose/zone capabilities

Design contract (siblings: `alerts-catalog-retail-grocery.csv`, `staff-presence-no-facial-id.md`). Signal sources marked LIVE are verified in the running edge loop; FUTURE rows need weights/sources we do not ship.

**Hard line (house discipline):** EdgeSight is an OPERATIONAL AID, not a certified life-safety or emergency-dispatch system. Every safety alert is an operator prompt for human review. Nothing here auto-calls anyone, auto-dispatches responders, or feeds insurance/HR/legal processes. Alert delivery rides the same in-flight rule engine and dedupe/hysteresis discipline as the alert catalog; camera outage = NO DATA honestly rendered, never zeros.

---

## 1) Capability catalog at a glance

| # | Alert id | Signal | Model | Zone/line needed | Alert text (to manager) | Status |
|---|---|---|---|---|---|---|
| 1 | SAFETY_EXIT_BLOCKED | stationary-tagged track dwelling in exit corridor ≥ grace; optional YOLO-World "trolley / pallet / shelf" category confirming obstruction | person detector (verified) + stationary policy tag (verified) + YOLO-World categories (verified) | `type: exit_corridor` zone (operator-calibrated) | "Emergency exit corridor occupied for N min — dispatch someone to clear the fire exit." | LIVE |
| 2 | SAFETY_CROWD_DENSITY | zone occupancy ≥ calibrated cap (or people/area ≥ density threshold) sustained ≥ 3 min | person detector + track dedupe (verified) | any customer zone + `zone_capacity_people` (from notifications/dwell doc) | "Crowd building in {zone} — open a lane / direct foot traffic." | LIVE |
| 3 | SAFETY_FALL_CANDIDATE_BBOX | collapse heuristics: bbox aspect ratio collapse + foot-point descent + post-event stillness ≥ 10 s | person detector only (verified) | none (global per camera) | "Possible fall — cam {id} at {ts} — human review required." | LIVE (candidate-only, high-false-positive disclaimer) |
| 4 | SAFETY_FALL_CANDIDATE_POSE | torso-angle vs vertical > threshold + head keypoint near floor + low movement ≥ 10 s | POSE head — weights NOT in shipped pack; `pose.enabled` false today | none | same as 3 with pose badge | FUTURE (weights + audited tuning) |
| 5 | SAFETY_AFTER_HOURS_MOTION | person_now ≥ 1 ≥ 10 s OR a fresh tripwire during closed window | person detector + verified zones/lines | `crowd_calibration.hours` schedule (NEW config block, designed shape in staff doc) | "Movement in-store outside opening hours — cam {id}, {ts}. Dispatch guard review." | PARTIAL (needs schedule calibration + alert pipeline) |
| 6 | SAFETY_RESTRICTED_ENTRY | confirmed track dwell ≥ min inside `type: restricted` zone | person detector (verified) | restricted zone (stockroom/office/plant) | "Person in restricted zone {name} — check authorization (session-based; no identity)." | LIVE |
| 7 | SAFETY_WEAPON_CANDIDATE | excluded — see section 6 | — | — | — | FUTURE (not recommended; disclaimer) |
| 8 | SAFETY_AGE_RESTRICTED_ZONE | excluded — see section 6 | — | — | — | FUTURE (disclaimer) |

Alert payload shape (all rows, durable events channel; additive enum):

```json
{
  "event": "safety_alert_raised",
  "alert_id": "SAFETY_EXIT_BLOCKED",
  "camera_id": "cam_checkout_01",
  "zone_id": "exit_1",
  "severity": "critical",
  "value": 143, "threshold": 120,
  "started_ts": "2026-10-23T12:01:33Z", "raised_ts": "...",
  "human_review_required": true, ...
}
```

## 2) YAML additions (normalized coords; operator-calibrated fields disabled until set)

```yaml
cameras:
  - id: cam_checkout_01
    normalized: true
    zones:
      - id: exit_1
        name: Fire exit - rear corridor
        type: exit_corridor                    # NEW zone type
        polygon: [[0.10, 0.35], [0.24, 0.35], [0.22, 0.62], [0.08, 0.58]]
        blocked_grace_seconds: 30              # stationary dwell that trips the alert
        raise_yolo_categories: [trolley, pallet, shelf]   # optional corroboration via YOLO-World prompts
      - id: stockroom_door
        name: Goods stockroom
        type: restricted                       # NEW zone type
        polygon: [[0.70, 0.20], [0.92, 0.22], [0.90, 0.50], [0.68, 0.46]]
        entry_grace_seconds: 5

  crowd:                                        # per-zone, parent node
    default_zone_capacity_people: 8            # rows without their own cap stay UNCALIBRATED
    density_alert_min_seconds: 180

schedule:                                      # after-hours; reuses the shape proven in staff doc
  hours: "09:00-21:30"
  grace_minutes: 10                            # ignore the first 10 min past close (closing crew)
  exceptions: []                               # e.g. auditing night; rows listed here never alert

safety:
  fall_bbox_min_still_seconds: 10              # live candidate tier (wide recall, human review after)
  response_timeout_minutes_verify: 5           # card asks for human confirmation; not auto-dismissed
```

## 3) Per-capability rules and honest notes

**3.1 SAFETY_EXIT_BLOCKED (LIVE).** Person transits the corridor many times a day; only STATIONARY tracks (verified tracker tag) beyond `blocked_grace_seconds` fire. Corroboration: a YOLO-World category like `trolley` inside the same zone upgrades confidence wording in the alert text but is never required to fire. False-positive mode: staff staging goods near the door → staff-tagged tracks still count (they belong in corridors rarely; keep grace ≥ 30 s). Clear: zone empties 60 s → `safety_alert_cleared`.

**3.2 SAFETY_CROWD_DENSITY (LIVE).** Reuses verified zone occupancy with the calibrated cap discipline from the alert catalog: no cap set → `UNCALIBRATED`, never evaluated. Counts in overlapping camera FOV double-count; the UI carries the documented `occupancy_note` next to any density number. Severity: warning at cap, critical at cap × 1.5 held 5 min.

**3.3 SAFETY_FALL_CANDIDATE (bbox tier LIVE, pose tier FUTURE).**
- Bbox tier (ships today on verified boxes): a confirmed track whose bbox aspect collapses toward horizontal, whose foot-point drops sharply, and which then stays put (stationary tag) for `fall_bbox_min_still_seconds` → candidate alert. This heuristic is deliberately billed as a **candidate**: crouching to a low shelf, sitting on a bench, and floor-level shopping all trip it. Every such alert routes to human review; staff may dismiss with a reason that lands in the events stream (for tuning, not for training models on customer imagery).
- Pose tier (FUTURE): needs pose weights added to the pack + an audited rule set (torso angle, head-height fraction, post-fall stillness). Even when shipped, the alert text stays "candidate — human review required". No automated medical claims, no "the system detected a fall" phrasing — detection of a fall CANDIDATE is the honest ceiling.

**3.4 SAFETY_AFTER_HOURS_MOTION (PARTIAL).** Needs the `schedule` block (config-only, no model gap) + the in-flight alert pipeline. Person presence during closed windows fires; closing-crew grace window and `exceptions` rows prevent nightly false positives; staff-tagged tracks still count unless an explicit staff exception is set (operator decision, stated in the alert text: "unless cleaning crew scheduled"). While the system is OFF after hours per camera power schedule, no sensor exists — honest gap, not coverage claimed by the dashboard.

**3.5 SAFETY_RESTRICTED_ENTRY (LIVE).** Zone entry with the verified zone-machinery grace; durable event includes only `{camera_id, zone_id, ts, session track ref, duration}` — no identity. Alert text avoids accusation ("check authorization") because the system cannot know authorization; repeated-entry aggregation is allowed (person X once per minute) but identity stays forbidden per the staff doc.

## 4) Visual denotation on the overlay

- Safety zones outline in red-family zone color with legend entry "Safety zone (operational aid — not a certified safety system)"; restricted zones get hatch fill in the studio preview only.
- Safety alerts surface on the video overlay as keyed pulsing chips near events; cards mirror the catalog's reference model (cards keyed to the earliest incident anchor; whole-minute tinted rows; MISSED-TIMING rows earn the badge only after human review > 30 min).
- All safety chips carry the universal "human review" marker; nothing here renders as an automated verdict.

## 5) What we must NOT claim

- Not a life-safety or fire-compliance system; does not replace smoke/occupancy-certified hardware; every alert is advisory for a human.
- No auto-dispatch to emergency services, no automated 911/emergency calls, no incident auto-adjudication.
- No identity, no face matching, no attendance/legal/HR use (inherits the staff-presence hard lines).
- No claims of fall DETECTION — only fall CANDIDATES for human review, even once the pose tier ships.
- No fabricated precision/recall numbers; if any tier is ever measured, the HONEST measured number is published next to the sample size and the footage date range.

## 6) Deliberately excluded (FUTURE-with-disclaimer, never auto-fire)

| Row | Why excluded from live use | Disclaimer the UI must show |
|---|---|---|
| SAFETY_WEAPON_CANDIDATE | Open-source person models do not reliably classify weapons; CCTV angles/lighting make it worse; false positives are costly and skewed; the field has no honest, auditable model for this store context. Until a governed external source exists, do not build it. | "Requires external governed source; EdgeSight does not and cannot detect weapons. Any third-party integration must be a policy decision outside this roadmap." |
| SAFETY_AGE_RESTRICTED_ZONE (e.g. minors at alcohol) | Visual age guessing is unreliable and, as decisioning, unlawful in this pipeline; demographics never gate access. | "Age inference from appearance is out of scope by policy. Use a governed verified-age source (POS/ID compliance tooling) if required — video remains advisory-only." |

Both rows stay red-chipped in any catalog UI as "requires external data source — not available in EdgeSight", same as the POS/identity FUTURE rows in the alert catalog.
