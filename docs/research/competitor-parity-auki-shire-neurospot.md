# Competitor parity — Auki/Cactus · Shire Intelligence · Neurospot

**Audience:** ADLabs EdgeSight portal (Next.js `:3000` + FastAPI `:8000` + EdgeSight Docker)  
**Rule:** Map *publicly described* capabilities → open models/pipelines we already have or can download. **No proprietary model downloads. No facial identity product. No invented gender/age accuracy. No invented vendor partnerships.**

Honest maturity: **LIVE** / **PARTIAL** / **FUTURE**

---

## Verified identities (1-line)

| Vendor | Product | What they sell |
|--------|---------|----------------|
| **Auki Labs / Auki Network** | **Cactus** (spatial AI for retail; older informal “Cactus XR” / CactusXR references map here) | Shared store digital twin + shelf/product spatial map + AR search/nav + spatial task handovers; CCTV used as *attention* sensors on top of handhelds/robots |
| **Shire Intelligence** | **Shire** (Intelligence / POS / Agent) | YC F26 restaurant OS: existing CCTV → live table/floor state, role-routed staff alerts, AI ops assistant joined to POS/reservations/staffing |
| **Neurospot** (neurospot.tech) | **NBVR + Invoke (analytics) + ScanX (security)** | CV video analytics for retail/hospitality: traffic, paths, dwell, heatmaps, queues, staff activity; ScanX also markets FR / weapons (we **do not** clone FR) |

Sources (public):
- Cactus: https://www.getcactus.ai/ · https://pulse.auki.com/landing/cactus · https://www.auki.com/solutions/industries/retail
- Auki open stack: https://github.com/aukilabs/posemesh · https://docs.dev.aukiverse.com/docs/protocol/ · https://github.com/aukilabs/auki_robotics_cactus_search
- Shire: https://shireintelligence.com/ · https://www.ycombinator.com/companies/shire-intelligence
- Neurospot: https://neurospot.tech/ (site often bot-walled); channel + press describe retail CV modules — **no public SDK found**

---

## 1) Auki Labs — Cactus (not a separate “CactusXR” SKU today)

### What they sell
Cactus is Auki’s **spatial AI copilot for physical retail**: map the store (phone scan + QR anchors), register products/shelves into a shared 3D twin, then run shelf analytics, planogram compliance, product search with route optimization, AR staff/customer navigation (Gotu app-free option), and spatially anchored task handovers. CCTV is positioned as an **attention-mapping** input into the twin, alongside handhelds and robots—not as a pure people-counting NVR.

### Public tech / APIs
| Piece | Public? | URL / note |
|-------|---------|------------|
| Posemesh (collaborative spatial protocol) | Open source (MIT) | https://github.com/aukilabs/posemesh |
| Protocol docs / multi-lang SDK | Public docs | https://docs.dev.aukiverse.com/docs/protocol/ |
| Reconstruction node (SfM / twins) | Open repo | https://github.com/aukilabs/reconstruction-server |
| Relay / Hagall session net | Open repo | https://github.com/aukilabs/hagall |
| Cactus product search + 3D pose client | Public API + open wrapper | Gateway `https://cactus-public-api.lookingglassprotocol.com` · search `POST …/search/page` · recommendations `POST …/recommended` · https://github.com/aukilabs/auki_robotics_cactus_search |
| Enterprise Cactus cloud | Closed product | Contact / pilot — **not** an ADLabs partnership (do not invent) |

**Stack keywords (public copy):** digital twin, QR portals, shelf analytics, planogram compliance, sales heatmaps, CCTV attention mapping, AR product search, spatial task management, robot orchestration.

### Feature matrix vs our portal

| Our section | Cactus analogue | Our maturity | Open path (ours) |
|-------------|-----------------|--------------|------------------|
| Entrance / glass / stop-rate | Attention at facade (not their core) | **LIVE** tripwires; stop/engaged **PARTIAL→LIVE** via pose/engagement | YOLO26/11 + tripwires; glass-stop dwell rule; pose engagement |
| Floor paths / traction | Twin floor + sales/attention heatmaps | **LIVE** zones + heatmap JPEG | ByteTrack + zone polygons + heatmap writer |
| Queue timestamps | Weak (ops focus elsewhere) | **LIVE** length/wait; **PARTIAL** join/leave episodes | QueueAnalyzer + durable events (handoff) |
| Staffing | Spatial task + AR staff nav | **LIVE** staff zones; **FUTURE** spatial tasks | Staff polygons + dwell tag (**no FR**) |
| Safety | Not primary marketing | **PARTIAL** alert catalog | Heuristic alerts only |
| Retail intelligence / shelf | Shelf analytics + planogram | **PARTIAL→LIVE** `products_top` open-vocab | YOLO-World / YOLOE + CLIP text; **not** closed SKUs |
| Store compare | Multi-store twin compare | **FUTURE** | Multi-store rollups |
| Display interest | Attention mapping from CCTV | **LIVE/PARTIAL** engagement + products | Pose facing + open-vocab interest |
| Alerts | Planogram / task alerts | **PARTIAL** | Queue/staff/occupancy rules |

### Parity UX to add (not clone IP)
1. **Shelf meter / fixture cards** — interest + dwell per fixture polygon (we have category interest; add fixture IDs).  
2. **Attention overlay** — “what shoppers face” heatmap (pose facing_ratio × zones), distinct from footfall heat.  
3. **Spatial task stubs** — owner actions pinned to zones (“restock F3”, “open till”) without AR SDK.  
4. **Optional later:** evaluate Auki posemesh / Cactus public search **as an integration**, not a model steal — only if product decides on a real partner deal.

---

## 2) Shire Intelligence

### What they sell
**Restaurant** AI floor manager on **existing CCTV**: live table states, host seating balance, server/busser attention alerts (greet / order / check / bus), AI ops assistant that joins **visual activity + POS + reservations + staffing**. Separate Shire Agent (text-ops) and full Shire POS SKUs. Spelling confirmed: **Shire Intelligence** (Myrtle Beach; YC Fall 2026).

### Public tech / APIs
- Marketing site + pricing: https://shireintelligence.com/  
- YC profile: https://www.ycombinator.com/companies/shire-intelligence  
- **No public CV SDK, model names, or GitHub** found for their vision stack. Treat vision as closed.  
- Transferable *product* pattern: CCTV state machine + role-routed alerts + POS join — not a downloadable model.

### Feature matrix vs our portal

| Our section | Shire analogue | Our maturity | Open path |
|-------------|----------------|--------------|-----------|
| Entrance / stop | Door / host flow | **LIVE** | Tripwires |
| Floor paths | Live host floor map | **LIVE** occupancy; **FUTURE** table-state UX | Zones as “sections” |
| Queue timestamps | Wait / turn times | **LIVE/PARTIAL** | Queue episodes + wait_ms |
| Staffing | Live team coordination | **LIVE** counts; **PARTIAL** response_time_to_queue | Staff zones + linked queues |
| Safety | Limited | **PARTIAL** | Alerts catalog |
| Retail intelligence | Menu / pricing sims (POS) | **FUTURE** for grocery POS | POS join (not CV) |
| Store compare | Multi-location enterprise | **FUTURE** | Tenant rollups |
| Display interest | N/A (FOH tables) | — | — |
| Alerts | Role-routed push (host/server/busser) | **PARTIAL** | Alert feed + role tags |

### Parity UX to add
1. **Role-routed alert inbox** — queue_wait / no_staff / understaffed with recommended *owner action* (already in alerts handoff).  
2. **Zone state chips** — idle / busy / needs_staff (geometry + occupancy, not table FR).  
3. **Ops assistant panel** — LLM over *our* live JSON + history only; cite sources; never invent sales.  
4. **POS join (FUTURE)** — turn times / abandon $ — integration, not a model.

---

## 3) Neurospot

### What they sell
Computer-vision **video analytics** (hardware NBVR + software). Public/press describe: traffic, visitor dwell, paths/heatmaps, queue/wait, staff activity, shelf interest, loss-prevention modules. Product split often cited as **Invoke** (business analytics) vs **ScanX** (security: repeat-offender FR, weapons — **out of scope / blocked for ADLabs**). Site https://neurospot.tech/ is frequently behind an interstitial; treat marketing claims carefully.

### Public tech / APIs
- Site: https://neurospot.tech/en/solutions/retail/ (fetch often fails / bot wall)  
- YouTube @neurospot — module demos (barista, track monitoring, robbery, etc.)  
- **No public API/SDK/GitHub for the commercial product** found in this pass. Unrelated GitHub “NeuroSpot” repos (ADHD / stroke hackathons) are **not** this vendor.  
- **Do not** download or claim their proprietary nets.

### Feature matrix vs our portal

| Our section | Neurospot analogue | Our maturity | Open path |
|-------------|-------------------|--------------|-----------|
| Entrance / stop | Traffic + engagement | **LIVE** | YOLO + tripwire + stop dwell |
| Floor paths / heatmaps | Paths + heatmaps | **LIVE** | ByteTrack + heatmap |
| Queue timestamps | Queue length / wait | **LIVE/PARTIAL** | QueueAnalyzer |
| Staffing | Staff productivity CV | **LIVE** presence; **FUTURE** gesture/task | Staff zones; pose optional; **no hand-productivity policing as product claim** |
| Safety / LP | ScanX weapons / FR | **BLOCKED** for FR; **FUTURE** object heuristics | YOLO-World “suspicious linger” only as pattern |
| Retail intelligence | Shelf / interest | **PARTIAL→LIVE** | YOLO-World / YOLOE |
| Store compare | Multi-site dashboards | **FUTURE** | Tenant compare |
| Display interest | Dwell at displays | **LIVE/PARTIAL** | products_top + engagement |
| Alerts | Real-time module alerts | **PARTIAL** | Our alerts catalog |

### Parity UX to add
1. **Path / traction story** — zone sequence graph (session ReID, in-store only).  
2. **Honest LP patterns** — prolonged high-value dwell without staff tag = *suspicious pattern*, never “theft detected”.  
3. **Queue + staff coupling** — response_time_to_queue (handoff already drafted).  
4. Explicit **privacy wall** in UI: YuNet redaction ON; no FR; no repeat-offender identity.

---

## Recommended model / feature backlog (ours)

| # | Capability (UX parity) | Inspired by | Models / code we use | Status |
|---|------------------------|-------------|----------------------|--------|
| 1 | Role-routed actionable alerts | Shire | Existing events + alerts catalog JSON | **PARTIAL** → next |
| 2 | Fixture-level display interest | Cactus / Neurospot | YOLO-World/YOLOE + fixture polygons | **PARTIAL** |
| 3 | Attention heatmap (facing ≠ footfall) | Cactus | Pose engagement × zones | **PARTIAL** |
| 4 | Queue join/leave timestamps + series | Shire / Neurospot | QueueAnalyzer upgrade handoff | **PARTIAL** |
| 5 | Session path graph (soft ReID) | Neurospot | OSNet ONNX session gallery | **PARTIAL** (quality mode) |
| 6 | Staff response_time_to_queue | Shire | Staff zones + queue alerts | **PARTIAL** |
| 7 | Store-compare rollups | All | Multi-store analytics | **FUTURE** |
| 8 | Spatial twin / AR nav | Cactus | Optional posemesh eval only | **FUTURE** (partner) |
| 9 | POS-joined abandon $ | Shire | POS API | **FUTURE** |
| 10 | Facial identity / repeat offender | Neurospot ScanX | — | **BLOCKED** |

**Already LIVE (keep honest):** entrance tripwires, floor zones, footfall heatmap, queue length/wait defaults, staff zone counts, MJPEG wall, `products_top` when models loaded, engagement when enrichment/quality on.

---

## Field map stubs (`/api/v1/live` → portal)

Wire only real keys; empty → PARTIAL/NO-DATA — never fake metrics.

| Portal card | Prefer live fields | Badge rule |
|-------------|-------------------|------------|
| Entrance / glass / stop | `total_visitors`, tripwire counts, `engagement.engaged_ratio` | LIVE if tripwire counts non-null + models loaded |
| Floor paths / traction | `cameras[].dwell_zones[]`, heatmap endpoint | LIVE if zones array present (empty list OK) |
| Queue timestamps | `queues[]` / `queue_length`, `avg_queue_wait_seconds`, `queue_alert_active` | LIVE length/wait; PARTIAL until join_ts/leave_ts |
| Staffing | `staff_now`, staff_zones, `counts.staff_visible` | LIVE presence; PARTIAL response_time |
| Safety | alerts feed (when shipped) | PARTIAL heuristics; no FR |
| Retail / shelf | `products_top[]` | LIVE if non-empty + product model loaded; else PARTIAL analytics |
| Store compare | — | FUTURE |
| Display interest | `products_top`, `engagement` | LIVE/PARTIAL as above |
| Alerts | `queue_alert_active` + catalog | PARTIAL |

Portal proxy: `:3000/api/edgesight/live` → EdgeSight `:8000/api/v1/live` (+ `live/state` builder in `data-freshness.ts`).

---

## Implementation checklist (next agent)

1. Ship **Intelligence parity** panel on Live ops (this branch) — cards only, badges from section badges / FUTURE static.  
2. Finish queue episode events + Alerts screen (handoff docs already in ADLabs-dev).  
3. Fixture polygons in Calibration Studio → `products_top` keyed by fixture_id.  
4. Facing/attention layer separate from footfall heatmap.  
5. Soft ReID path graph UI (session only; quality mode).  
6. Do **not** wire Neurospot FR, Auki private clouds, or Shire POS without a real contract.  
7. Optional spike: call Cactus *public* search against a demo domain_id — document only; no product claim until legal.

---

## Explicit non-claims

- We did **not** download proprietary closed models from Auki, Shire, or Neurospot.  
- We do **not** have API partnerships with these vendors.  
- Demographics stay **k-anon PARTIAL**; no gender/age accuracy marketing.  
- No facial identity / repeat-offender product.
