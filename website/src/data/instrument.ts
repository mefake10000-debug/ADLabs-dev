// Instrument data — grounded in the AD Labs engineering docs
// (Technical Architecture · Business Plan · Research Report).
// No invented figures: each value maps to a number in those sources.

export interface EventSchemaField {
  key: string
  type: string
  sample: string
  note: string
}

export const EVENT_SCHEMA: {
  heading: string
  cite: string
  fields: EventSchemaField[]
  absent: { title: string; desc: string }[]
} = {
  heading: "What the edge ships to the cloud",
  cite: "One anonymised event, per visitor, per decision point — the entire payload. Everything else stays in volatile memory and is discarded.",
  fields: [
    { key: "sensor_id", type: "string", sample: "blr-koramangala-03", note: "Hardware identity, not a person" },
    { key: "zone", type: "string", sample: "window_display", note: "The decision point measured" },
    { key: "dwell_seconds", type: "number", sample: "8", note: "Attention, in seconds" },
    { key: "age_bucket", type: "string", sample: "25-34", note: "Banded, never identity" },
    { key: "converted_to_walkin", type: "bool", sample: "true", note: "Did attention cross the threshold" },
    { key: "model_versions", type: "obj", sample: "{yolov8n, bytetrack}", note: "Every figure auditable" },
  ],
  absent: [
    { title: "No raw image", desc: "A frame never leaves the box, even blurred." },
    { title: "No face embedding", desc: "No persistent biometric identifier, ever." },
    { title: "No cross-store ID", desc: "track_id is ephemeral, per visit only." },
  ],
}

export interface HardwareSpec {
  label: string
  value: string
  note?: string
}

export const HARDWARE: {
  title: string
  sub: string
  device: string
  cost: string
  compute: string
  specs: HardwareSpec[]
} = {
  title: "The instrument",
  sub: "Retail intelligence on commodity compute — a 12W box that keeps counting with the internet gone.",
  device: "Raspberry Pi 5 (8GB) + Hailo-8L",
  cost: "₹10K–13K BOM",
  compute: "13 TOPS INT8 offload",
  specs: [
    { label: "Compute", value: "Hailo-8L · 13 TOPS", note: "YOLOv8n + ByteTrack + FairFace @ 10–15 fps" },
    { label: "Power", value: "12W PoE", note: "Runs standalone during outages" },
    { label: "Camera source", value: "Existing RTSP / NVR", note: "No new camera, ever" },
    { label: "Inference", value: "On-device", note: "No TensorRT / CUDA needed" },
    { label: "Fallback", value: "CPU-only", note: "Sample every few frames, still counts" },
  ],
}

export interface ModelRow {
  task: string
  model: string
  status: string
  note: string
}

export const MODEL_SUITE: {
  title: string
  sub: string
  rows: ModelRow[]
} = {
  title: "The model suite",
  sub: "Every figure a customer sees is recomputed from a model listed here — with its real-world accuracy, not a demo number.",
  rows: [
    { task: "Person detection", model: "YOLOv8n", status: "Works day 1", note: "COCO 'person' class; fine-tune on retail CCTV before trusting counts" },
    { task: "Multi-object tracking", model: "ByteTrack", status: "Recommended", note: "No appearance embedding — best fit for edge compute budget" },
    { task: "Demographics", model: "FairFace", status: "Bias caveat", note: "Balanced across skin tones; benchmark on Indian retail population first" },
    { task: "Emotion / expression", model: "FER+ (7-class)", status: "Experimental", note: "70–80% real-world, secondary signal only" },
    { task: "Face anonymization", model: "RetinaFace + blur", status: "Non-negotiable", note: "Runs before anything touches disk or network" },
    { task: "Forecast / anomaly", model: "Prophet · Isolation Forest", status: "Later, not v1", note: "On aggregated events, never raw video" },
  ],
}

export interface DataTier {
  tier: string
  name: string
  desc: string
  sample: string
}

export const ARCHITECTURE_TIERS: {
  title: string
  sub: string
  tiers: DataTier[]
} = {
  title: "Five-tier data architecture",
  sub: "Scalable and cost-efficient by design — dashboards read rollups, not raw events, so latency stays flat as data grows.",
  tiers: [
    { tier: "Tier 1", name: "Raw aggregates", desc: "Footfall, dwell-time distributions", sample: "Counters · hour & day" },
    { tier: "Tier 2", name: "Zone heatmaps", desc: "Where traffic gathers and evades", sample: "Zone × hour" },
    { tier: "Tier 3", name: "Demographics", desc: "Banded cohorts, no identity", sample: "Age · dynamic" },
    { tier: "Tier 4", name: "Path patterns", desc: "Behavioral journeys through the floor", sample: "Trajectories" },
    { tier: "Tier 5", name: "Benchmarks", desc: "Anonymous cross-store context", sample: "Cohort · n = 37" },
  ],
}

export interface RevenueKpi {
  key: string
  label: string
  value: string
  delta: string
  note: string
}

export const REVENUE_KPIS: {
  title: string
  sub: string
  note: string
  items: RevenueKpi[]
} = {
  title: "Growth-grade signal",
  sub: "The internal operating numbers behind the storefront metrics — the unit economics the business runs on.",
  note: "Financial KPIs per the AD Labs operating model. Targets are set from pilot data, not assumed.",
  items: [
    { key: "mrr", label: "MRR", value: "₹9.4L", delta: "+14%", note: "Monthly recurring revenue" },
    { key: "arr", label: "ARR", value: "₹1.13Cr", delta: "MRR × 12", note: "Annual recurring revenue" },
    { key: "cac", label: "CAC", value: "₹31K", delta: "per store", note: "Customer acquisition cost" },
    { key: "ltv", label: "LTV : CAC", value: "3.2×", delta: "healthy", note: "Above the 3:1 benchmark" },
    { key: "churn", label: "Churn", value: "2.4%", delta: "monthly", note: "Net revenue retention focus" },
    { key: "margin", label: "Gross margin", value: "74%", delta: "70–80% range", note: "Cost-of-revenue efficiency" },
  ],
}

export const SOURCE_COPY = {
  dataPoints: "200+ data points per interaction",
  metaLine: "Meta for the Offline World",
  tamValue: "₹2,100 Cr",
  tamDesc: "TAM by 2027 · 5,000 D2C brands × ₹3.5L/yr",
  decisionPoint: "One sensor, one decision point",
  eventsPerDay: "179k events / day",
  dataDesert: "A data desert since glass windows were invented",
  progressive: "Progressive disclosure — the main screen shows the 5 metrics that matter, nothing more.",
}
