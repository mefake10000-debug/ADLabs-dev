# Retail Edge AI Analytics — Research, Product Strategy & Pilot Plan

## Context

I am exploring a retail analytics product that uses **Mac mini / Apple Silicon as an on-premise edge AI device** connected to retailers' existing CCTV cameras.

The basic concept is:

```text
Existing CCTV Cameras
        ↓
NVR / RTSP / ONVIF
        ↓
Mac mini (Apple Silicon)
        ↓
Computer Vision / Tracking / Analytics
        ↓
Retail Events & Metrics
        ↓
Dashboard / Alerts / Business Intelligence
```

The key hypothesis is:

> **Can we turn existing CCTV infrastructure into an affordable, privacy-preserving retail intelligence system using a Mac mini, without requiring retailers to replace their cameras?**

I already have **partners willing to pilot the solution**, so this should be approached as a real product/pilot opportunity, not merely an academic computer-vision project.

The initial target market is likely **Indian retail**, but I want the architecture and product positioning to be potentially applicable globally.

---

# OBJECTIVE

Conduct a structured research and product-planning exercise and produce a practical roadmap for validating and building this company/product.

Do NOT jump directly into implementation.

First determine:

1. What retail problems are actually worth solving.
2. What existing companies already provide.
3. Where the gaps/opportunities are.
4. Which use cases should be prioritized.
5. Whether Mac mini is technically suitable as the edge compute platform.
6. What needs to be tested during pilots.
7. What the MVP should contain.
8. What should explicitly NOT be built initially.
9. What metrics determine whether the pilot is successful.
10. What could become a defensible product/business.

---

# PRIORITY FRAMEWORK

Use these priorities throughout the research.

## P0 — MUST VALIDATE

These are mandatory.

### Customer/problem research

Determine:

* What retail managers actually care about.
* Which problems have measurable financial impact.
* Which metrics retailers already track.
* Which metrics are missing.
* What decisions managers currently make manually.
* What information they wish they had in real time.
* What they would potentially pay for.

Create a list of questions that should be asked to my pilot partners.

Do NOT assume that every technically possible computer-vision feature is commercially valuable.

---

## P0 — Competitive research

Research existing companies/products, including but not limited to:

* RetailNext
* V-Count
* FootfallCam
* AXIS
* NVIDIA / Metropolis
* Any significant Indian retail analytics companies
* Other relevant computer-vision retail analytics companies

For every important competitor, determine:

* Target customer
* Main use cases
* Hardware requirements
* Whether existing CCTV can be used
* Edge vs cloud architecture
* Camera requirements
* People counting
* Occupancy
* Queue analytics
* Dwell time
* Heatmaps
* Customer journey
* Staff analytics
* Product interaction
* POS integration
* Conversion analytics
* Alerts
* Dashboard capabilities
* Pricing, if publicly available
* Deployment model
* Strengths
* Weaknesses
* Potential differentiation opportunity

Prefer official sources and credible technical/business sources.

Do not make up pricing or capabilities.

Clearly distinguish:

* Confirmed information
* Reasonable inference
* Unknown information

---

# P0 — USE-CASE DISCOVERY

Build a comprehensive retail computer-vision use-case list.

At minimum investigate:

### Traffic

* People counting
* Entry/exit
* Direction
* Occupancy
* Peak traffic

### Customer behavior

* Dwell time
* Zone visits
* Heatmaps
* Customer journey
* Repeat visits, if technically/privacy feasible
* Group behavior

### Queue

* Queue detection
* Queue length
* Waiting time
* Queue abandonment
* Counter utilization
* Queue alerts

### Conversion

Investigate integration of:

```text
Camera Footfall
+
POS Transactions
=
Conversion Rate
```

Determine how valuable this is and what data/integration is required.

### Staff

* Staff presence
* Staff availability
* Customer/staff interaction
* Staff-to-customer ratio
* Response time
* Zone coverage

### Merchandising

* Product interaction
* Display engagement
* Shelf interaction
* Promotion engagement
* Planogram compliance

### Loss prevention

Research possibilities but treat this as a later-stage area.

### Other

Identify additional high-value retail use cases that competitors solve or retailers commonly request.

---

# P0 — USE-CASE PRIORITIZATION

Create a scoring framework.

For every use case score:

* Business value: 1–10
* Customer willingness to pay: 1–10
* Technical difficulty: 1–10
* Required hardware: 1–10
* Data requirements: 1–10
* Accuracy difficulty: 1–10
* Privacy/legal risk: 1–10
* Deployment complexity: 1–10
* Differentiation potential: 1–10
* Pilot feasibility: 1–10

Then produce:

### Tier 1 — MVP

Must build/test.

### Tier 2 — After MVP

High-value but more complex.

### Tier 3 — Future

Potentially valuable but not worth building now.

### Explicitly avoid

Features that sound impressive but are poor initial bets.

Do not simply rank features by technical coolness.

---

# P1 — MAC MINI / APPLE SILICON FEASIBILITY

Research the current Mac mini Apple Silicon hardware relevant to edge AI.

Investigate:

* CPU
* GPU
* Neural Engine
* Unified memory
* Video decode
* Video encode
* H.264
* H.265
* Memory bandwidth
* Thermal characteristics
* Power consumption
* Multiple camera stream processing
* macOS limitations
* Long-running workloads

Research:

* Core ML
* ONNX Runtime
* CoreML Execution Provider
* MLX
* PyTorch on Apple Silicon
* OpenCV
* FFmpeg
* AVFoundation
* VideoToolbox

Determine which stack is most appropriate.

Do not assume that Neural Engine/GPU acceleration automatically means good production performance.

---

# P1 — MAC MINI BENCHMARK PLAN

Design an actual benchmark.

The benchmark should test something like:

```text
1 camera
4 cameras
8 cameras
12 cameras
16 cameras
20+ cameras
```

Use realistic retail CCTV conditions.

Test:

* 720p / 1080p
* 15 FPS / 25 FPS / 30 FPS where relevant
* H.264 / H.265
* Different model sizes
* Detection FPS
* End-to-end latency
* CPU utilization
* GPU utilization
* Memory utilization
* Thermal behavior
* Dropped frames
* Inference throughput
* Accuracy
* Power consumption

The key question:

> How many real-world CCTV streams can one Mac mini process reliably while maintaining acceptable accuracy and latency?

Provide a concrete benchmark methodology.

---

# P1 — EXISTING CCTV COMPATIBILITY

This is one of the most important business questions.

Research common CCTV/NVR infrastructure used in Indian retail, including vendors such as:

* Hikvision
* Dahua
* CP Plus
* Axis
* Uniview
* Other relevant vendors

Investigate:

* RTSP
* ONVIF
* NVR integration
* H.264
* H.265
* Authentication
* Multiple streams
* Sub-streams
* Camera discovery
* Network requirements

The ideal deployment should look approximately like:

```text
Existing Cameras
       ↓
Existing NVR
       ↓
RTSP
       ↓
Mac mini
```

The retailer should ideally NOT need to replace cameras.

Determine how realistic this is.

---

# P1 — PRIVACY & SECURITY

Research the architecture needed for enterprise retail deployment.

Prefer:

> Video stays inside the store.

The Mac mini performs inference locally.

Cloud should preferably receive metadata/events rather than raw video.

Example:

```json
{
  "store_id": "123",
  "timestamp": "...",
  "visitors": 17,
  "occupancy": 31,
  "queue_length": 4,
  "avg_dwell_seconds": 83,
  "zone": "electronics"
}
```

Research:

* Data minimization
* Video retention
* Metadata retention
* Encryption
* Access control
* Audit logs
* Indian privacy requirements
* DPDP Act implications
* Customer consent/signage where relevant
* Facial recognition implications

Do not recommend facial recognition as part of the initial MVP unless there is a compelling business reason.

---

# P1 — PILOT DESIGN

I already have pilot partners.

Create a pilot framework.

## Before installation

Collect:

* Store size
* Store layout
* Camera count
* Camera locations
* Camera models
* NVR model
* RTSP availability
* Camera resolution
* FPS
* POS system
* Transaction data availability
* Internet connectivity
* Existing analytics systems
* Staffing model
* Current pain points

Create a **pilot questionnaire**.

---

# PILOT PHASES

Design a phased pilot.

## Phase 0 — Site survey

Understand camera infrastructure and store operations.

## Phase 1 — Technical validation

Connect cameras and measure:

* Stream reliability
* Inference performance
* Detection accuracy
* Tracking accuracy
* Latency

## Phase 2 — Basic analytics

Implement:

* People counting
* Entry/exit
* Occupancy
* Zones
* Dwell
* Heatmaps

## Phase 3 — Queue

Implement:

* Queue detection
* Queue length
* Waiting time
* Alerts

## Phase 4 — Business intelligence

Integrate POS data.

Measure:

* Footfall
* Transactions
* Conversion
* Revenue per visitor
* Traffic vs sales
* Store/time comparisons

## Phase 5 — Operational impact

Determine whether analytics actually change:

* Staffing
* Queue management
* Store layout
* Promotions
* Customer experience

---

# P0 — PILOT SUCCESS METRICS

Define measurable success criteria.

Include:

### Technical

* Detection accuracy
* Counting accuracy
* Tracking accuracy
* Queue accuracy
* False positives
* False negatives
* Latency
* Uptime
* Camera stream reliability
* Mac mini utilization

### Business

* Reduction in waiting time
* Improvement in conversion
* Improvement in staffing efficiency
* Revenue impact
* Reduction in abandoned queues
* Manager time saved
* Store operational improvements

### Product

* Dashboard usage
* Alerts acted upon
* Reports viewed
* Features requested
* Willingness to pay

Do not invent target values without explaining the reasoning.

---

# P2 — MVP DEFINITION

Based on all research, propose the smallest product worth deploying commercially.

The likely candidate to investigate is:

```text
Existing CCTV
      ↓
Mac mini
      ↓
People Detection
      ↓
Tracking
      ↓
Zones / Lines
      ↓
Events
      ↓
Retail Metrics
      ↓
Dashboard
```

Potential initial metrics:

* Visitors
* Entries
* Exits
* Occupancy
* Dwell
* Zone traffic
* Heatmap
* Queue length
* Queue waiting time
* Conversion using POS

But do NOT assume all of these belong in MVP. Use the research to decide.

---

# P2 — ARCHITECTURE

Propose a production-oriented architecture.

Separate:

### Edge

* Camera ingestion
* Video decoding
* Detection
* Tracking
* Zone processing
* Event generation
* Local buffering
* Health monitoring

### Cloud

* Store management
* Metrics aggregation
* Dashboard
* User management
* Alerts
* Reports
* Configuration
* Fleet/device management

### Data

Define appropriate schemas for:

* Cameras
* Stores
* Zones
* Tracks
* Events
* Aggregated metrics
* POS transactions
* Alerts

Prefer sending metadata rather than video wherever possible.

---

# P2 — DEVICE MANAGEMENT

Research what is required to operate potentially hundreds/thousands of Mac minis.

Consider:

* Remote deployment
* Configuration
* Health checks
* Software updates
* Model updates
* Logs
* Monitoring
* Crash recovery
* Network failures
* Local buffering
* Remote diagnostics
* Device authentication
* Secure communication

This should be considered early because a prototype that works on one Mac mini is not necessarily a deployable product.

---

# P3 — FUTURE FEATURES

After establishing the core product, evaluate:

* Customer journey
* Staff analytics
* Product interaction
* Shelf analytics
* Promotion effectiveness
* Planogram compliance
* Loss prevention
* Advanced forecasting
* Store benchmarking
* Multi-store optimization
* AI-generated operational recommendations

Also investigate whether an LLM layer is genuinely useful.

For example:

Instead of merely showing:

> Queue = 8

the system could eventually provide:

> "Queue congestion has increased during 6–7 PM for the last 14 days. Consider adding one checkout during this period."

But treat this as a later layer on top of reliable structured analytics.

---

# IMPORTANT — DO NOT OVERBUILD

Explicitly identify things that should NOT be built in the first version.

Potential examples:

* Facial recognition
* Emotion recognition
* Age/gender classification
* Complex product recognition
* Full inventory automation
* Autonomous checkout
* Advanced theft detection
* Mobile app
* Complicated LLM chatbot
* Large cloud video-processing infrastructure

Explain why each should be deferred.

---

# COMPETITIVE POSITIONING

Based on research, propose 3–5 possible positioning strategies.

Examples to investigate:

### Positioning A

"Turn existing CCTV into AI-powered retail analytics."

### Positioning B

"Affordable retail intelligence for Indian retailers."

### Positioning C

"Privacy-first, on-premise retail AI."

### Positioning D

"Plug-and-play retail analytics using edge AI."

### Positioning E

"From CCTV data to actionable store operations."

For each, evaluate:

* Competitive strength
* Customer appeal
* Technical defensibility
* Pricing potential
* Ease of communicating the value

Recommend one primary positioning.

---

# BUSINESS MODEL

Research possible pricing models.

Examples:

* Per store / month
* Per camera / month
* Hardware + SaaS
* Mac mini lease + SaaS
* One-time installation + recurring analytics
* Enterprise license

Do NOT make unsupported pricing claims.

Instead determine the economic model required to make the business attractive.

Calculate rough unit economics for:

* 1 store
* 10 stores
* 100 stores
* 1,000 stores

Consider:

* Mac mini cost
* Installation
* Internet/networking
* Cloud
* Support
* Software
* Monitoring
* Replacement hardware
* Gross margin

---

# RESEARCH OUTPUT

Produce the final research in this structure:

## 1. Executive Summary

Maximum 1–2 pages.

Answer:

> Is this a compelling opportunity?

> Why or why not?

> What should I build first?

---

## 2. Market Landscape

Competitors and their capabilities.

Include a comparison table.

---

## 3. Retail Use Cases

Comprehensive list with prioritization.

---

## 4. Recommended MVP

Clearly state:

### BUILD NOW

### BUILD NEXT

### BUILD LATER

### DO NOT BUILD

---

## 5. Mac mini Feasibility

Hardware/software analysis.

---

## 6. Benchmark Plan

Exact experiments to run.

---

## 7. Pilot Plan

Detailed 30/60/90-day plan.

---

## 8. Pilot Partner Questionnaire

Questions I can directly use with retailers.

---

## 9. Technical Architecture

Edge + cloud + data architecture.

---

## 10. Security & Privacy

Requirements and recommendations.

---

## 11. Business Model

Potential pricing and unit economics framework.

---

## 12. Competitive Advantage

Identify the strongest possible differentiation.

---

## 13. Risks

Technical, commercial, operational, privacy and deployment risks.

---

## 14. Decision Framework

At the end provide explicit GO / NO-GO criteria.

For example:

### GO

If:

* X accuracy
* X camera scalability
* X pilot ROI
* X customer willingness to pay

### PIVOT

If:

* ...

### STOP

If:

* ...

---

# RESEARCH QUALITY RULES

1. Use current information.
2. Prefer official company/product documentation.
3. Use credible technical sources for hardware/software benchmarks.
4. Use primary sources whenever possible.
5. Cite important claims.
6. Do not invent pricing.
7. Clearly label assumptions.
8. Separate facts from recommendations.
9. Be critical rather than optimistic.
10. Look for reasons this business could fail.
11. Do not assume that because a feature is technically possible, customers will pay for it.
12. Focus heavily on Indian retail deployment realities.
13. Compare against existing solutions rather than pretending this is a greenfield market.

---

# MOST IMPORTANT FINAL QUESTION

After completing the research, answer this directly:

> **If you were building this company yourself, with access to several retail partners willing to pilot, what EXACTLY would you build in the next 90 days, what would you test, and what evidence would convince you to invest another 12 months into the business?**

Give a concrete answer, not a generic startup roadmap.
