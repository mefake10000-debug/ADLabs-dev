# Privacy Badge Matrix — what the UI shows, section by section

Basis (system-wide, verified in code and config):
- **No facial identification.** Face detection (YuNet) is redaction-only; `face_identity` is hard-banked to `false` in the live payload.
- **Session-scoped Re-ID only.** OSNet embeddings live in an in-memory session gallery with TTL pruning; nothing persists across sessions and no face-ID is derived.
- **k-anonymity guardrail.** Demographic cohorts render only when `sample_size ≥ k (10)` and `publishable == true`; below that the UI suppresses by design.
- **Open-vocab display categories, never SKUs.** Product interest comes from YOLO-World text labels; revenue/POS claims remain explicit FUTURE.
- **Staff tagging is geometric, not biometric.** A sticky tag from standing ≥10 s in a staff polygon.
- **Track IDs are session integers.** They never act as customer identities in any export.

Badge meanings:
- **LIVE** — real field today; render actual values.
- **PARTIAL** — producer exists; display suppressed by a privacy/config gate; show copy below.
- **FUTURE** — no producer deployed; show copy below.

## The matrix

| Section | Metric | Badge | Why | UI copy when badge active |
|---|---|---|---|---|
| Entrance | Occupancy, footfall in/out, hourly history | LIVE | Active-track counting + tripwire events verified flowing | (render real numbers) |
| Entrance | Stop-rate | FUTURE | Tracker computes stationary seconds; dashboard field pending | "Stop-rate unlocks once entrance-zone dwell thresholds are exposed. The tracker already computes stationary seconds — we show nothing rather than estimate." |
| Floor | Zone traction + heatmap | LIVE | Zone membership + heatmap JPEG verified | (render real numbers) |
| Floor | Movement routes | FUTURE | No route model | "Traction is real today (zones + heatmap). Movement-route arcs need the route model and will not be approximated." |
| Queue | Length, wait, congestion alert | LIVE | QueueAnalyzer verified tick (length 1, wait 18.8 s seen live) | (render real numbers) |
| Queue | Per-counter service timestamps | FUTURE | Counter calibration not drawn | "Per-counter service timestamps need counter-level calibration, which hasn't been drawn yet." |
| Alerts | Crossing feed + congestion flags | LIVE | Events persisted and served verified | (render real numbers) |
| Alerts | Dwell-spike alerts | FUTURE | No rule deployed | "Dwell alerts activate when the alert rule is configured for your zones — aggregation fields (zone dwell) are live already." |
| Alerts | Safety (fall/surge) | FUTURE | No safety model | "No safety model on this edge node. We will not render fabricated alerts." |
| Staffing | Staff now + per-zone counts | LIVE | Geometric tagging verified (staff_now: 1 seen live) | (render real numbers) |
| Staffing | Shift/roster optimizer | FUTURE | No roster data | "Shows live staff-zone presence only; shift recommendations need roster data we don't have." |
| Safety | Crowd density surface | LIVE (proxy) | Heatmap density is real | "Aggregate crowd density — not incident detection." |
| Retail Intel | Demographics | PARTIAL | k≥10 gate suppresses until enough samples (verified: publishable=false) | "Cohort counts unlock after ≥10 anonymous samples inside the privacy window (k-anonymity). The real model runs — we suppress below the threshold by design." |
| Retail Intel | Attention / phone / groups | PARTIAL | Enrichment tier config-off in fast mode; honest zeros verified | "Attention metrics (facing/phone/groups) activate with pose + head-pose enrichment on this node. Rows show honest zeros today so the queue and footfall numbers are never contaminated." |
| Display | Category viewers/dwell | LIVE | YOLO-World pipeline verified (dated real history) | (render real numbers) |
| Display | POS/SKU attribution | FUTURE | No POS integration | "These are display-interest signals (what shoppers look at), not sales. Connecting a POS feed is a separate, consented integration." |
| Store Intel | Active occupancy + flow | LIVE | Snapshot-merge verified (occupancy_mode=active_tracks) | (render real numbers; overlap double-count documented) |
| Store Intel | Multi-store compare | FUTURE | Single store deployed | "Single-store deployment. Multi-store compare activates as soon as a second device registers — store_id is already ingest-ready." |
| Cross-cam | Person handoff / fusion | PARTIAL→FUTURE boundary | Session tracker per camera today | "Session-scoped person tracker only today. Cross-camera identity fusion requires the ReID gallery task — and stays anonymous unless policy changes." |

## Rules the UI must keep (zero-glitch policy)

1. A section never renders a zero where the truth is "not measured today" — zeros are only for genuinely-measured zero.
2. Every PARTIAL/FUTURE panel must show the exact copy above (not paraphrased promises).
3. `models` strip in the live payload is the single source of what's running; render it verbatim, including disabled items.
4. Staleness guard: when the frame-synced snapshot is stale, the live endpoint answers with `source: telemetry_rollups` and may add `snapshot_stale: true` — the UI must disclose which source it rendered.
