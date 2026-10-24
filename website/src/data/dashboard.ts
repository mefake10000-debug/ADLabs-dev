export interface Kpi {
  id: string
  label: string
  value: string
  delta: string
  deltaTone: "pos" | "neg" | "flat"
  deltaNote: string
  peer?: string
  hint: string
}

export interface BusinessKpi {
  label: string
  value: string
  delta: string
  tone: "pos" | "neg" | "flat"
  note: string
  iconHint: string
}

export const BUSINESS_KPIS: BusinessKpi[] = [
  { label: "Shopper yield", value: "₹6,420", delta: "+9.4%", tone: "pos", note: "Revenue per visitor · sales-linked", iconHint: "yield" },
  { label: "Avg basket", value: "₹4,180", delta: "+5.1%", tone: "pos", note: "Average transaction value", iconHint: "basket" },
  { label: "Sales conversion", value: "34%", delta: "+2.2pp", tone: "pos", note: "Visitors who transacted (POS linked)", iconHint: "pos" },
  { label: "Campaign ROI", value: "6.8×", delta: "+0.9×", tone: "pos", note: "Attributed revenue vs OOH spend", iconHint: "megaphone" },
  { label: "Revenue / walk-in", value: "₹1,780", delta: "+6.0%", tone: "pos", note: "Value per door crossing", iconHint: "currency" },
]

export interface FlowEdge {
  from: string
  to: string
  pct: number
}

export const VISITOR_FLOW = {
  title: "Visitor flow · path popularity",
  sub: "How shoppers move across the floor — entry to exit. Thicker edge = more popular path.",
  nodes: [
    { id: "E0", name: "Entrance" },
    { id: "A1", name: "Apparel" },
    { id: "L2", name: "Leather Island" },
    { id: "H3", name: "Hero Rotunda" },
    { id: "S5", name: "Footwear" },
    { id: "R6", name: "Fitting" },
    { id: "T8", name: "Transit" },
  ],
  edges: [
    { from: "E0", to: "A1", pct: 41 },
    { from: "E0", to: "L2", pct: 68 },
    { from: "E0", to: "S5", pct: 22 },
    { from: "A1", to: "L2", pct: 46 },
    { from: "L2", to: "H3", pct: 71 },
    { from: "H3", to: "R6", pct: 55 },
    { from: "S5", to: "R6", pct: 30 },
    { from: "R6", to: "T8", pct: 74 },
  ],
}

export const FORECAST = {
  title: "Quarter outlook",
  sub: "Projected stop rate with confidence band (Prophet style, on aggregated events only).",
  measured: [
    { week: "W1", value: 9.2 }, { week: "W2", value: 9.4 }, { week: "W3", value: 9.1 },
    { week: "W4", value: 9.3 }, { week: "W5", value: 10.8 }, { week: "W6", value: 11.2 },
    { week: "W7", value: 11.0 }, { week: "W8", value: 10.6 }, { week: "W9", value: 10.9 },
    { week: "W10", value: 10.9 }, { week: "W11", value: 11.1 }, { week: "W12", value: 11.4 },
  ],
  projected: [
    { week: "W13", value: 11.7, lo: 11.2, hi: 12.2 },
    { week: "W14", value: 11.9, lo: 11.1, hi: 12.4 },
    { week: "W15", value: 12.0, lo: 11.0, hi: 12.6 },
    { week: "W16", value: 12.0, lo: 10.8, hi: 12.7 },
  ],
}

export const OCCUPANCY = {
  now: 34,
  capacity: 60,
  level: 57,
  queue: 3,
  avgWait: "02:14",
  peakWindow: "16:30 – 18:45",
  trend: [18, 22, 26, 30, 34, 36, 34],
}

export interface Store {
  id: string
  name: string
  city: string
  grade: "A" | "B" | "C"
  footfallToday: number
  stopRate: string
  trend: "up" | "flat" | "down"
  spark: number[]
  flag?: string
}

export const TENANT = { name: "Organic Clothing Co.", store: "Bandra Flagship · Mumbai" }

export const PERIODS = ["Today", "This week", "30 days", "Baseline → Wk 12"] as const
export type Period = (typeof PERIODS)[number]

export const KPIS: Record<"today" | "week", Kpi[]> = {
  today: [
    { id: "footfall", label: "Street Footfall", value: "2,481", delta: "+6.2%", deltaTone: "pos", deltaNote: "vs yesterday", hint: "Peak volume 16:30 – 18:45" },
    { id: "stop", label: "Window Stop Rate", value: "7.5%", delta: "+0.4pp", deltaTone: "pos", deltaNote: "vs yesterday", peer: "8.9%", hint: "Threshold: paused ≥ 4s" },
    { id: "walkins", label: "Walk-ins", value: "39", delta: "+3", deltaTone: "pos", deltaNote: "vs yesterday", hint: "Peak entry 16:30 – 18:45" },
    { id: "dwell", label: "In-Store Dwell", value: "6m 12s", delta: "+22s", deltaTone: "pos", deltaNote: "vs yesterday", hint: "Hero zone holds 9m 45s" },
  ],
  week: [
    { id: "footfall", label: "Street Footfall", value: "16,340", delta: "+1.5%", deltaTone: "pos", deltaNote: "vs last week", hint: "Best day: Saturday · 3,120" },
    { id: "stop", label: "Window Stop Rate", value: "11.4%", delta: "+0.3pp", deltaTone: "pos", deltaNote: "vs last week", peer: "8.9%", hint: "Threshold: paused ≥ 4s" },
    { id: "walkins", label: "Walk-ins", value: "391", delta: "+2.1%", deltaTone: "pos", deltaNote: "vs last week", hint: "Peak entry 16:30 – 18:45" },
    { id: "dwell", label: "In-Store Dwell", value: "6m 12s", delta: "+8s", deltaTone: "pos", deltaNote: "vs last week", hint: "Hero zone holds 9m 45s" },
  ],
}

export interface BenchmarkRow {
  id: string
  label: string
  you: number
  peer: number
  unit: string
  suffix: string
  better: "higher" | "lower"
}

export const PEER_BENCHMARK = {
  title: "Your storefront vs. the cohort",
  sub: "Bandra flagship compared against the anonymised luxury retail cohort — 40 stores across Bengaluru, Mumbai, Delhi NCR and Hyderabad.",
  rows: [
    { id: "stop", label: "Window stop rate", you: 11.4, peer: 8.9, unit: "%", suffix: "pp", better: "higher" },
    { id: "look", label: "Deep look time", you: 39, peer: 31, unit: "%", suffix: "pp", better: "higher" },
    { id: "enter", label: "Stop-to-enter rate", you: 21, peer: 16, unit: "%", suffix: "pp", better: "higher" },
    { id: "dwell", label: "In-store dwell", you: 6.2, peer: 4.75, unit: "min", suffix: " min", better: "higher" },
    { id: "occupancy", label: "Peak occupancy", you: 71, peer: 57, unit: "%", suffix: "pp", better: "higher" },
  ],
  position: { rank: 6, cohort: 40, label: "Top 15% of cohort" },
  note: "Cohort: anonymised fashion & luxury flagships · updated weekly from on-device aggregates.",
}

export const FUNNEL = {
  today: [
    { stage: "Pass", value: 2481, rate: "100%", label: "Street Footfall" },
    { stage: "Stop", value: 186, rate: "7.5%", label: "Attention Hook" },
    { stage: "Enter", value: 39, rate: "21.0%", label: "Stop-to-Enter" },
    { stage: "Explore", value: 34, rate: "87.2%", label: "Active Browsing" },
    { stage: "Engage", value: 18, rate: "52.9%", label: "High-Intent Touch" },
  ],
  week: [
    { stage: "Pass", value: 16340, rate: "100%", label: "Street Footfall" },
    { stage: "Stop", value: 1861, rate: "11.4%", label: "Attention Hook" },
    { stage: "Enter", value: 391, rate: "21.0%", label: "Stop-to-Enter" },
    { stage: "Explore", value: 341, rate: "87.2%", label: "Active Browsing" },
    { stage: "Engage", value: 180, rate: "52.9%", label: "High-Intent Touch" },
  ],
}

export const TRAFFIC_HOURS = [
  { h: "09", v: 88 }, { h: "10", v: 132 }, { h: "11", v: 168 }, { h: "12", v: 198 },
  { h: "13", v: 186 }, { h: "14", v: 214 }, { h: "15", v: 262 }, { h: "16", v: 289 },
  { h: "17", v: 271 }, { h: "18", v: 196 }, { h: "19", v: 158 }, { h: "20", v: 112 },
  { h: "21", v: 107 },
]

export const PEAK_WINDOWS = [
  { label: "PEAK 15:00 – 17:00", note: "Window attention peaks · staff up 2" },
  { label: "PEAK 16:30 – 18:45", note: "Entry cluster · 3 on floor" },
]

export const STORES: Store[] = [
  {
    id: "madison",
    name: "Bandra Flagship · Mumbai",
    city: "Mumbai",
    grade: "A",
    footfallToday: 2481,
    stopRate: "7.5%",
    trend: "up",
    spark: [1.9, 2.1, 2.0, 2.3, 2.2, 2.4, 2.5],
  },
  {
    id: "beverly",
    name: "Indiranagar Boutique",
    city: "Bengaluru",
    grade: "B",
    footfallToday: 1620,
    stopRate: "6.2%",
    trend: "flat",
    spark: [1.7, 1.6, 1.7, 1.6, 1.7, 1.6, 1.6],
  },
  {
    id: "mayfair",
    name: "Koregaon Park Boutique",
    city: "Pune",
    grade: "C",
    footfallToday: 980,
    stopRate: "4.1%",
    trend: "down",
    spark: [1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.9],
    flag: "Window underperforming — stop rate 4.1% vs 8.9% cohort",
  },
]

export interface Zone {
  code: string
  name: string
  traffic: number
  dwell: string
  heat: number
  note?: string
  flag?: string
}

export const ZONES: Zone[] = [
  { code: "E0", name: "Entrance Gallery", traffic: 100, dwell: "0m 48s", heat: 0.42, note: "Threshold velocity 0.8 m/s" },
  { code: "A1", name: "Apparel Zone", traffic: 41, dwell: "6m 12s", heat: 0.62 },
  { code: "L2", name: "Leather Goods Island", traffic: 68, dwell: "7m 04s", heat: 0.86, note: "Top zone · 68% traffic share" },
  { code: "H3", name: "Accessories Hero · Rotunda", traffic: 55, dwell: "9m 45s", heat: 0.95, note: "Highest store density" },
  { code: "F1", name: "Window West", traffic: 9, dwell: "1m 02s", heat: 0.12, flag: "Under-lit after 18:00 — dwell 2.1× below floor average" },
  { code: "D4", name: "Denim Wall", traffic: 27, dwell: "3m 38s", heat: 0.38 },
  { code: "S5", name: "Footwear Alcove", traffic: 22, dwell: "2m 54s", heat: 0.3 },
  { code: "R6", name: "Fitting Rooms", traffic: 12, dwell: "8m 10s", heat: 0.58, note: "Conversion: 74%" },
  { code: "V7", name: "Advisory Salon", traffic: 15, dwell: "5m 26s", heat: 0.44, note: "Conversion: 38%" },
  { code: "T8", name: "Transit Corridor", traffic: 83, dwell: "0m 22s", heat: 0.18, note: "1.3 m/s pace — cold transit" },
]

export const DEMOGRAPHICS = {
  ages: [
    { band: "18–27", pct: 14 },
    { band: "28–44", pct: 62 },
    { band: "45–60", pct: 19 },
    { band: "60+", pct: 5 },
  ],
  dynamics: { solo: 58, pair: 42 },
  gender: { male: 54, female: 46 },
  party: { individual: 58, group: 42 },
  peak: "16:30 – 18:45",
  note: "Aggregated · minimum 10 individuals per cohort bucket",
}

export interface Campaign {
  id: string
  name: string
  week: string
  type: string
  metricLabel: string
  before: string
  after: string
  window: string
  verified: boolean
  uplift: string
  imageBefore: string
  imageAfter: string
}

export const CAMPAIGNS: Campaign[] = [
  {
    id: "winter",
    name: "Winter Rotation",
    week: "Wk 4",
    type: "Window reset",
    metricLabel: "Window Stop Rate",
    before: "6.4%",
    after: "7.3%",
    window: "14-Day A/B Rotation",
    verified: true,
    uplift: "+14.6% observed uplift",
    imageBefore: "/images/window-before.jpg",
    imageAfter: "/images/window-after.jpg",
  },
  {
    id: "sash",
    name: "Hero Sash Installation",
    week: "Wk 8",
    type: "Display change",
    metricLabel: "Avg Hero Gaze",
    before: "8.4s",
    after: "9.6s",
    window: "7-Day A/B Rotation",
    verified: true,
    uplift: "+14.3% observed uplift",
    imageBefore: "/images/in-store-zones.jpg",
    imageAfter: "/images/window-after.jpg",
  },
]

export const CAMPAIGN_TIMELINE = [
  { week: "W1", stop: 9.2 }, { week: "W2", stop: 9.4 }, { week: "W3", stop: 9.1 },
  { week: "W4", stop: 9.3, event: "Winter Rotation" }, { week: "W5", stop: 10.8 },
  { week: "W6", stop: 11.2 }, { week: "W7", stop: 11.0 }, { week: "W8", stop: 10.6, event: "Hero Sash" },
  { week: "W9", stop: 12.1 }, { week: "W10", stop: 12.4 }, { week: "W11", stop: 11.8 },
  { week: "W12", stop: 11.4 },
]

export const CAMPAIGN_VERDICT =
  "The Wk 4 rotation worked — stop rate beat baseline by +14.6% and held for three weeks. The Wk 8 sash lifted hero gaze by 1.2s. Keep the layout; test the offer next."

export const BRIEF = {
  week: "Wk 12",
  title: "Monday Decision Brief",
  minutes: "15-minute read · built for founders",
  verdict:
    "The window rotation is still paying for itself — stop rate is +14.6% vs baseline and stop rate sits 2.5pp above the luxury cohort. The west vitrine is now the weakest link.",
  actions: [
    {
      title: "Move the Leather Island 1.5m into the window sightline",
      why: "Zone F1 dwell is 2.1× the floor average after 18:00. The island already owns 68% traffic share — give it the glass.",
      priority: "High",
      tag: "Layout",
    },
    {
      title: "Staff up 2 for the 15:00 – 17:00 attention peak",
      why: "Walk-ins cluster in this window all week. Coverage converts.",
      priority: "Medium",
      tag: "Staffing",
    },
    {
      title: "Refresh Window West",
      why: "Deep Attention (> 4s) fell 6pp over two weeks. A rotation is due.",
      priority: "High",
      tag: "Visual",
    },
  ],
  benchmark: "Stop rate 11.4% vs peer 8.9% — luxury cohort · 37 stores · anonymised",
  evidence: [
    { image: "/images/window-before.jpg", label: "Baseline · Wk 3" },
    { image: "/images/window-after.jpg", label: "Rotation · Wk 5" },
    { image: "/images/in-store-zones.jpg", label: "Zones · Wk 12" },
  ],
}

export const MANAGER = {
  store: "Bandra Flagship · Mumbai",
  date: "Monday · Wk 12",
  staffing: [
    { window: "12:30 – 14:30", need: "2 on floor", note: "Lunch overlap" },
    { window: "16:30 – 18:45", need: "3 on floor", note: "Entry cluster — peak" },
  ],
  checklist: [
    "Position Leather Island hero at 45° to the glass",
    "Count register float before 11:00",
    "Log window-change photos by 10:00",
    "Test Window West lighting at 18:00",
  ],
  alert: "Window stop rate is trending +0.4pp today. Keep the current rotation.",
}

export const WINDOW_ENGAGEMENT = [
  { label: "Casual Glance (< 2s)", pct: 42 },
  { label: "Deep Attention (> 4s dwell)", pct: 39 },
  { label: "Immediate Entry Turn", pct: 19 },
]

export const WEEKLY_HISTORY = [
  { week: "W1", footfall: 14200, stopRate: 9.2, walkins: 310, dwell: "5m 40s" },
  { week: "W2", footfall: 14800, stopRate: 9.4, walkins: 325, dwell: "5m 52s" },
  { week: "W3", footfall: 15100, stopRate: 9.1, walkins: 318, dwell: "5m 38s" },
  { week: "W4", footfall: 15400, stopRate: 9.3, walkins: 340, dwell: "5m 45s", event: "Winter Rotation" },
  { week: "W5", footfall: 15800, stopRate: 10.8, walkins: 355, dwell: "5m 55s" },
  { week: "W6", footfall: 16000, stopRate: 11.2, walkins: 370, dwell: "6m 02s" },
  { week: "W7", footfall: 15900, stopRate: 11.0, walkins: 368, dwell: "5m 58s" },
  { week: "W8", footfall: 15700, stopRate: 10.6, walkins: 375, dwell: "5m 48s", event: "Hero Sash" },
  { week: "W9", footfall: 15850, stopRate: 10.9, walkins: 379, dwell: "5m 56s" },
  { week: "W10", footfall: 15800, stopRate: 10.9, walkins: 375, dwell: "6m 00s" },
  { week: "W11", footfall: 16100, stopRate: 11.1, walkins: 383, dwell: "6m 04s" },
  { week: "W12", footfall: 16340, stopRate: 11.4, walkins: 391, dwell: "6m 12s" },
]

export interface Insight {
  id: string
  type: "prediction" | "anomaly" | "opportunity" | "recommendation"
  title: string
  description: string
  confidence: "high" | "medium" | "low"
  basis: string
  action: string
  screen?: string
}

export const INSIGHTS: Insight[] = [
  {
    id: "1", type: "prediction",
    title: "Stop rate on track",
    description: "At the 0.1pp/week trend of the last 8 weeks, stop rate reaches 12.0% — and capture (stop→enter) holds 21%.",
    confidence: "high", basis: "Linear projection, Wk 4–Wk 12",
    action: "Keep the current rotation — do not change creatives prematurely.", screen: "storefront",
  },
  {
    id: "2", type: "anomaly",
    title: "Zone F1 dwell declining",
    description: "Window West dwell has dropped 2.1× below floor average for 2 consecutive weeks. Deep attention fell 6pp.",
    confidence: "high", basis: "2-week trend vs floor average",
    action: "Rotate creative and relight at 18:00. Re-measure in 7 days.", screen: "zones",
  },
  {
    id: "3", type: "opportunity",
    title: "Saturday peak understaffed",
    description: "Saturday footfall exceeds weekday average by 40%, but staffing stays flat.",
    confidence: "medium", basis: "Week-over-week footfall comparison",
    action: "Add 2 staff for Saturday 15:00–18:00 next week.", screen: "manager",
  },
  {
    id: "4", type: "recommendation",
    title: "Leather Island deserves the glass",
    description: "Zone L2 owns 68% traffic share but is 1.5m back from the window sightline. Moving it could lift stop rate by an estimated 0.3–0.5pp.",
    confidence: "medium", basis: "Traffic share vs window proximity analysis",
    action: "Move Leather Island 1.5m into the window sightline. Test for 7 days.", screen: "brief",
  },
  {
    id: "5", type: "prediction",
    title: "Koregaon Park needs intervention",
    description: "At the current -0.3pp/week stop rate decline, Koregaon Park will drop below 3% stop rate by Wk 16.",
    confidence: "low", basis: "7-week trend extrapolation, n=1 store",
    action: "Audit window display. Benchmark against cohort median (8.9%).", screen: "compare",
  },
]

export interface Prediction {
  metric: string
  current: string
  projected: string
  timeframe: string
  confidence: string
  basis: string
  direction: "up" | "down" | "flat"
}

export const PREDICTIONS: Prediction[] = [
  { metric: "Stop rate", current: "11.4%", projected: "12.0%", timeframe: "Wk 16", confidence: "87%", basis: "Linear trend, 8-week window", direction: "up" },
  { metric: "Footfall (Saturday)", current: "3,120", projected: "3,280", timeframe: "Next Saturday", confidence: "72%", basis: "4-Saturday rolling average", direction: "up" },
  { metric: "Zone F1 dwell", current: "1m 02s", projected: "0m 54s", timeframe: "Wk 14 (unaddressed)", confidence: "64%", basis: "2-week decline trend", direction: "down" },
]

export interface PlanAction {
  title: string
  category: "visual" | "staffing" | "layout" | "product" | "maintenance"
  priority: "high" | "medium" | "low"
  impact: string
  cost: "free" | "low" | "medium" | "high"
  evidence: string
}

export const WEEKLY_PLAN = {
  week: "Wk 13",
  title: "Next week's plan",
  actions: [
    { title: "Keep the current window rotation", category: "visual", priority: "high", impact: "Projected +0.3pp stop rate continuation", cost: "free", evidence: "Stop rate trended up 4 consecutive weeks" },
    { title: "Rotate Window West creative", category: "visual", priority: "high", impact: "Recover 2pp dwell in Zone F1", cost: "low", evidence: "Deep attention fell 6pp over 2 weeks" },
    { title: "Staff up 2 for Saturday 15:00–18:00", category: "staffing", priority: "medium", impact: "Convert estimated 120 additional walk-ins", cost: "free", evidence: "Saturday footfall +40% vs weekday average" },
    { title: "Test a new hero product in Accessories Hero zone", category: "product", priority: "medium", impact: "Potential +5% touch rate on hero", cost: "medium", evidence: "Zone H3 owns 68% traffic but touch rate flat" },
    { title: "Relight Zone F1 at 18:00", category: "maintenance", priority: "low", impact: "Prevent further dwell decline", cost: "free", evidence: "Under-lit after 18:00, dwell 2.1× below average" },
  ],
}

export const FUNNEL_HISTORY = {
  baseline: { Pass: 15100, Stop: 1380, Enter: 320, Explore: 278, Engage: 146 },
  wk4: { Pass: 15400, Stop: 1520, Enter: 340, Explore: 300, Engage: 158 },
  wk8: { Pass: 15800, Stop: 1680, Enter: 355, Explore: 310, Engage: 162 },
  wk12: FUNNEL.week,
}

export const WEEK_OVER_WEEK = {
  current: { footfall: 16340, stopRate: 11.4, walkins: 391, dwell: "6m 12s" },
  previous: { footfall: 16100, stopRate: 11.1, walkins: 383, dwell: "6m 04s" },
  change: { footfall: "+1.5%", stopRate: "+0.3pp", walkins: "+2.1%", dwell: "+8s" },
}

export const DAY_HOUR_HEATMAP: number[][] = [
  [20, 25, 35, 48, 62, 78, 92, 95, 88, 65, 40, 22],
  [18, 22, 32, 45, 58, 75, 90, 93, 85, 62, 38, 20],
  [22, 28, 38, 52, 65, 82, 95, 96, 90, 68, 42, 24],
  [19, 24, 34, 46, 60, 76, 88, 90, 82, 60, 36, 18],
  [21, 27, 36, 50, 64, 80, 93, 94, 86, 64, 40, 22],
  [25, 30, 40, 55, 70, 85, 96, 97, 92, 70, 45, 28],
  [28, 34, 44, 58, 72, 88, 97, 98, 94, 72, 48, 30],
]

export interface IndustryFixture {
  name: string
  gaze: string
  touch: string
  trend: number[]
  conversion?: string
  note?: string
}

export interface IndustrySector {
  id: string
  label: string
  icon: string
  image: string
  description: string
  benchmark: string
  avgDwell: string
  avgConversion: string
  marketSize: string
  keyInsight: string
  items: IndustryFixture[]
}

export const INDUSTRY_SECTORS: IndustrySector[] = [
  {
    id: "fashion", label: "Fashion & Apparel", icon: "👗",
    image: "/images/sector-fashion.jpg",
    description: "Luxury and premium fashion retail — window displays, runway rails, and leather goods drive the highest dwell times.",
    benchmark: "Stop rate 8.9% · conversion 21%",
    avgDwell: "6m 12s",
    avgConversion: "21%",
    marketSize: "₹2.4T",
    keyInsight: "Hero handbags own 42% of window attention. Move them to the glass.",
    items: [
      { name: "Hero Handbag Vitrine", gaze: "8.4s", touch: "42%", trend: [7.8, 8.0, 8.2, 8.4], conversion: "34%", note: "Peak 15:00–17:00" },
      { name: "Leather Goods Island", gaze: "7m 04s", touch: "68%", trend: [6.8, 6.9, 7.0, 7.0], conversion: "41%", note: "Top zone · 68% traffic share" },
      { name: "Capsule Runway Rail", gaze: "5.2s", touch: "24%", trend: [5.0, 5.1, 5.1, 5.2], conversion: "18%", note: "Low touch · high dwell" },
      { name: "Denim Wall", gaze: "3m 38s", touch: "38%", trend: [3.5, 3.6, 3.7, 3.8], conversion: "22%", note: "Weekend peak" },
      { name: "Accessories Rotunda", gaze: "9m 45s", touch: "55%", trend: [9.0, 9.2, 9.4, 9.6], conversion: "38%", note: "Highest store density" },
    ],
  },
  {
    id: "beauty", label: "Beauty & Cosmetics", icon: "💄",
    image: "/images/sector-beauty.jpg",
    description: "Fragrance and cosmetic counters — testers drive high interaction. Impulse purchase rate is sector-leading.",
    benchmark: "Stop rate 11.2% · conversion 28%",
    avgDwell: "4m 22s",
    avgConversion: "28%",
    marketSize: "₹1.1T",
    keyInsight: "Fragrance testers convert at 55% — the highest interaction rate in beauty.",
    items: [
      { name: "Fragrance Counter", gaze: "6m 12s", touch: "55%", trend: [6.0, 6.1, 6.1, 6.1], conversion: "32%", note: "Tester-driven" },
      { name: "Skincare Bench", gaze: "3m 48s", touch: "40%", trend: [3.5, 3.6, 3.7, 3.8], conversion: "26%", note: "Consultant-assisted" },
      { name: "Cosmetic Display", gaze: "4m 22s", touch: "32%", trend: [4.0, 4.1, 4.2, 4.2], conversion: "24%", note: "Self-service" },
      { name: "Lipstick Wall", gaze: "2m 18s", touch: "48%", trend: [2.0, 2.1, 2.1, 2.2], conversion: "38%", note: "Impulse · low price point" },
    ],
  },
  {
    id: "jewellery", label: "Jewellery & Watches", icon: "💎",
    image: "/images/sector-jewellery.jpg",
    description: "High-value vitrines — longest dwell times, highest conversion when staffed. Security and lighting are critical.",
    benchmark: "Stop rate 12.4% · conversion 18%",
    avgDwell: "9m 45s",
    avgConversion: "18%",
    marketSize: "₹3.2T",
    keyInsight: "High jewellery vitrines hold 9m 45s dwell — the longest in any retail sector.",
    items: [
      { name: "High Jewellery Vitrine", gaze: "9m 45s", touch: "72%", trend: [9.0, 9.2, 9.4, 9.6], conversion: "24%", note: "Staffed hours only" },
      { name: "Fine Timepiece Rail", gaze: "7m 30s", touch: "58%", trend: [7.0, 7.2, 7.3, 7.3], conversion: "19%", note: "Male-skewed · 28–44" },
      { name: "Signature Ring Display", gaze: "5m 18s", touch: "44%", trend: [4.8, 5.0, 5.1, 5.2], conversion: "16%", note: "Engagement season peak" },
      { name: "Silver & Casual Case", gaze: "3m 10s", touch: "36%", trend: [2.8, 2.9, 3.0, 3.1], conversion: "22%", note: "Entry price point" },
    ],
  },
  {
    id: "electronics", label: "Consumer Electronics", icon: "📱",
    image: "/images/sector-premium-retail.jpg",
    description: "Demo-driven retail — screen time and product interaction are the primary conversion levers.",
    benchmark: "Stop rate 9.6% · conversion 15%",
    avgDwell: "5m 20s",
    avgConversion: "15%",
    marketSize: "₹1.8T",
    keyInsight: "Demo units with screen-on convert at 2× the rate of sealed-box displays.",
    items: [
      { name: "Hero Phone Display", gaze: "4m 52s", touch: "62%", trend: [4.5, 4.6, 4.7, 4.8], conversion: "18%", note: "Live demo unit" },
      { name: "Audio Listening Station", gaze: "6m 10s", touch: "48%", trend: [5.8, 5.9, 6.0, 6.1], conversion: "14%", note: "Headphone trials" },
      { name: "Laptop Open-Display", gaze: "3m 44s", touch: "55%", trend: [3.4, 3.5, 3.6, 3.7], conversion: "12%", note: "Keyboard interaction" },
      { name: "Smart Home Wall", gaze: "2m 30s", touch: "28%", trend: [2.1, 2.2, 2.3, 2.4], conversion: "8%", note: "Low touch · aspirational" },
    ],
  },
  {
    id: "food", label: "Food & Beverage", icon: "🍷",
    image: "/images/sector-beauty.jpg",
    description: "Sensory retail — aroma, tasting, and visual merchandising drive impulse purchases. High repeat-visit rates.",
    benchmark: "Stop rate 14.2% · conversion 35%",
    avgDwell: "3m 10s",
    avgConversion: "35%",
    marketSize: "₹800B",
    keyInsight: "Tasting counters convert at 35% — the highest conversion rate across all sectors.",
    items: [
      { name: "Tasting Counter", gaze: "3m 10s", touch: "68%", trend: [2.8, 2.9, 3.0, 3.1], conversion: "35%", note: "Aroma-driven" },
      { name: "Artisanal Shelf", gaze: "2m 44s", touch: "42%", trend: [2.5, 2.6, 2.7, 2.8], conversion: "28%", note: "Premium positioning" },
      { name: "Seasonal Display", gaze: "1m 58s", touch: "55%", trend: [1.8, 1.9, 1.9, 2.0], conversion: "42%", note: "Limited-time urgency" },
      { name: "Grab-and-Go Bay", gaze: "1m 12s", touch: "72%", trend: [1.0, 1.1, 1.1, 1.2], conversion: "48%", note: "Fastest conversion" },
    ],
  },
  {
    id: "home", label: "Home & Living", icon: "🛋️",
    image: "/images/sector-premium-retail.jpg",
    description: "Room-set merchandising — shoppers need to visualise the product in their space. Dwell correlates with purchase.",
    benchmark: "Stop rate 7.8% · conversion 12%",
    avgDwell: "8m 20s",
    avgConversion: "12%",
    marketSize: "₹1.6T",
    keyInsight: "Room-set displays hold 8m+ dwell — but only 12% convert. Design needs to close the gap.",
    items: [
      { name: "Living Room Set", gaze: "8m 20s", touch: "36%", trend: [7.8, 7.9, 8.0, 8.2], conversion: "14%", note: "Highest dwell" },
      { name: "Kitchen Island Demo", gaze: "5m 40s", touch: "48%", trend: [5.2, 5.3, 5.5, 5.7], conversion: "18%", note: "Interactive surfaces" },
      { name: "Bedroom Concept", gaze: "6m 12s", touch: "28%", trend: [5.8, 5.9, 6.0, 6.1], conversion: "10%", note: "Low touch · aspirational" },
      { name: "Lighting Gallery", gaze: "4m 30s", touch: "52%", trend: [4.2, 4.3, 4.4, 4.5], conversion: "22%", note: "Impulse add-on" },
    ],
  },
  {
    id: "sports", label: "Sports & Active", icon: "👟",
    image: "/images/sector-fashion.jpg",
    description: "Experience-led retail — try-on, performance demos, and community events drive the highest footfall-to-enter rates.",
    benchmark: "Stop rate 10.8% · conversion 24%",
    avgDwell: "5m 45s",
    avgConversion: "24%",
    marketSize: "₹900B",
    keyInsight: "Try-on stations convert at 2× shelf-only displays. Put the shoe on the customer.",
    items: [
      { name: "Hero Sneaker Wall", gaze: "4m 30s", touch: "58%", trend: [4.2, 4.3, 4.4, 4.5], conversion: "28%", note: "Limited drops" },
      { name: "Try-On Station", gaze: "6m 20s", touch: "72%", trend: [6.0, 6.1, 6.2, 6.2], conversion: "42%", note: "Highest conversion" },
      { name: "Performance Apparel Rail", gaze: "3m 15s", touch: "34%", trend: [2.9, 3.0, 3.1, 3.2], conversion: "18%", note: "Function-led" },
      { name: "Accessories Bay", gaze: "2m 05s", touch: "44%", trend: [1.9, 2.0, 2.0, 2.1], conversion: "32%", note: "Impulse · socks, bags" },
    ],
  },
  {
    id: "pharmacy", label: "Health & Pharmacy", icon: "💊",
    image: "/images/sector-beauty.jpg",
    description: "Trust-driven retail — consultation and product knowledge are the primary conversion levers. Compliance matters.",
    benchmark: "Stop rate 6.4% · conversion 30%",
    avgDwell: "3m 40s",
    avgConversion: "30%",
    marketSize: "₹2.1T",
    keyInsight: "Consultation-led displays convert at 30% — the pharmacist is the storefront.",
    items: [
      { name: "OTC Health Counter", gaze: "3m 40s", touch: "52%", trend: [3.2, 3.3, 3.4, 3.5], conversion: "30%", note: "Pharmacist-assisted" },
      { name: "Wellness Vitrine", gaze: "2m 50s", touch: "38%", trend: [2.6, 2.7, 2.8, 2.9], conversion: "22%", note: "Supplements · vitamins" },
      { name: "Skincare Aisle", gaze: "4m 10s", touch: "44%", trend: [3.8, 3.9, 4.0, 4.1], conversion: "26%", note: "Dermocosmetics growth" },
      { name: "Seasonal Flu Bay", gaze: "1m 30s", touch: "62%", trend: [1.2, 1.3, 1.3, 1.4], conversion: "48%", note: "Urgency-driven" },
    ],
  },
]

export const PRODUCT_DATA = {
  sectors: INDUSTRY_SECTORS.map((s) => ({
    id: s.id,
    label: s.label,
    image: s.image,
    items: s.items.map((f) => ({ name: f.name, gaze: f.gaze, touch: f.touch, trend: f.trend })),
  })),
}

export const INDUSTRY_OVERVIEW = {
  totalSectors: 8,
  topPerformer: "Fashion & Apparel",
  avgStopRate: "10.2%",
  avgConversion: "22.8%",
  bestInsight: "Hero fixtures in the top 20% of the store own 68% of dwell time — but 80% of stores don't know which fixture that is.",
}

export const ALERTS = [
  { id: "1", severity: "critical", zone: "F1", message: "Under-lit after 18:00 — dwell 2.1× below average", time: "2h ago", action: "Relight at 18:00, re-measure in 7 days", screen: "zones" },
  { id: "2", severity: "high", store: "Koregaon Park", message: "Stop rate 4.1% vs 8.9% cohort — declining 0.3pp/week", time: "4h ago", action: "Audit window display, benchmark cohort", screen: "stores" },
  { id: "3", severity: "medium", zone: "V7", message: "Advisory Salon conversion dropped 3pp this week", time: "1d ago", action: "Review consultant placement, re-measure", screen: "zones" },
  { id: "4", severity: "low", zone: "T8", message: "Transit Corridor pace 1.3 m/s — cold transit", time: "2d ago", action: "Add visual anchor, re-measure in 14 days", screen: "zones" },
]

export interface AdCampaign {
  id: string
  name: string
  channel: string
  placement: string
  week: string
  spend: string
  impressions: number
  attributedWalkins: number
  attributedRate: string
  convertRate: string
  uplift: string
  flowImage: string
  redirect: { zone: string; name: string; pct: number }[]
}

export const ADS: AdCampaign[] = [
  {
    id: "poster-marion",
    name: "Street poster · Marion",
    channel: "Out-of-home poster",
    placement: "2 blocks from storefront",
    week: "Wk 13",
    spend: "₹1,02,000",
    impressions: 12400,
    attributedWalkins: 38,
    attributedRate: "0.31%",
    convertRate: "47%",
    uplift: "+12.4% vs unexposed",
    flowImage: "/images/sector-premium-retail.jpg",
    redirect: [
      { zone: "L2", name: "Leather Goods Island", pct: 41 },
      { zone: "H3", name: "Accessories Hero", pct: 33 },
      { zone: "A1", name: "Apparel Zone", pct: 26 },
    ],
  },
  {
    id: "digital-ooh",
    name: "Digital OOH screen",
    channel: "Digital out-of-home",
    placement: "Across the avenue · 40m sightline",
    week: "Wk 12",
    spend: "₹2,21,000",
    impressions: 18800,
    attributedWalkins: 52,
    attributedRate: "0.28%",
    convertRate: "52%",
    uplift: "+9.8% vs unexposed",
    flowImage: "/images/in-store-zones.jpg",
    redirect: [
      { zone: "H3", name: "Accessories Hero", pct: 48 },
      { zone: "V7", name: "Advisory Salon", pct: 29 },
      { zone: "L2", name: "Leather Goods Island", pct: 23 },
    ],
  },
  {
    id: "window-trail",
    name: "Window trail campaign",
    channel: "Window-mounted QR",
    placement: "On the glass itself",
    week: "Wk 11",
    spend: "₹38,000",
    impressions: 6900,
    attributedWalkins: 41,
    attributedRate: "0.59%",
    convertRate: "61%",
    uplift: "+17.2% vs unexposed",
    flowImage: "/images/window-after.jpg",
    redirect: [
      { zone: "F1", name: "Window West", pct: 38 },
      { zone: "H3", name: "Accessories Hero", pct: 35 },
      { zone: "L2", name: "Leather Goods Island", pct: 27 },
    ],
  },
]

export const AD_FLOW = {
  steps: [
    { key: "saw", title: "Saw the ad", desc: "People passing the placement during the flight. Counted anonymously.", image: "/images/blindspot-pass.jpg", value: "18,800" },
    { key: "entered", title: "Entered the store", desc: "Of those, the ones who walked in inside the attribution window.", image: "/images/blindspot-enter.jpg", value: "52" },
    { key: "zone", title: "Reached a zone", desc: "Which fixture area the attributed visitor first went to.", image: "/images/in-store-zones.jpg", value: "H3 · 48%" },
    { key: "converted", title: "Engaged & converted", desc: "High-intent touch on a product — the ad's real revenue signal.", image: "/images/sector-fashion.jpg", value: "52% · 27 buyers" },
  ],
}

export const SIMULATED_NOTE = "Simulated showcase data"
export const PEER_NOTE = "Peer set: anonymised luxury cohort · n = 37 stores"

export interface StaffingDay {
  day: string
  footfall: number
  staff: number
  hotHours: string[]
  peak: string
  level: "low" | "medium" | "high" | "peak"
}

export const STAFFING_INTEL: { days: StaffingDay[]; rule: string } = {
  days: [
    { day: "Mon", footfall: 2150, staff: 3, hotHours: ["12–14", "17–20"], peak: "17–20", level: "medium" },
    { day: "Tue", footfall: 1980, staff: 3, hotHours: ["13–15", "18–20"], peak: "13–15", level: "medium" },
    { day: "Wed", footfall: 2240, staff: 3, hotHours: ["12–14", "16–19"], peak: "16–19", level: "medium" },
    { day: "Thu", footfall: 2410, staff: 4, hotHours: ["12–15", "17–20"], peak: "17–20", level: "high" },
    { day: "Fri", footfall: 2860, staff: 4, hotHours: ["15–18", "19–21"], peak: "15–18", level: "high" },
    { day: "Sat", footfall: 3120, staff: 5, hotHours: ["15–18", "18–21"], peak: "15–18", level: "peak" },
    { day: "Sun", footfall: 2680, staff: 4, hotHours: ["16–19", "18–20"], peak: "16–19", level: "high" },
  ],
  rule: "Rule: 1 staff per 800 peak-hour passers-by · +1 for Fridays & weekends (festive surge in Indian retail)",
}

export const STORE_PERFORMANCE = {
  todayGrade: "A",
  weekGrade: "A",
  weekScore: 91,
  weeklyFootfall: 16340,
  revenueSignal: "+8.2%",
  bestDay: { day: "Saturday", footfall: 3120 },
  move: "Add 2 staff for Saturday 15:00–18:00 — festive surge is inbound",
}
