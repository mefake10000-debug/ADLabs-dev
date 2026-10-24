export const BRAND = {
  name: "AD Labs",
  wordmarkA: "AD",
  wordmarkB: "Labs",
  legal: "Ad Labs Tech Pvt Ltd",
  city: "Bengaluru, India",
  founded: "2026",
  email: "sales@adlabs.in",
  domain: "adlabs.in",
  tagline: "Physical retail intelligence that respects human privacy.",
}

export const SOCIALS = {
  linkedin: "",
  instagram: "",
  label: "Pages opening soon",
}

export type Founder = {
  name: string
  role: string
  focus: string
  avatar: {
    skin: string
    hair: string
    hairPath: "A" | "B" | "C"
    glasses: boolean
    shirt: string
  }
}

export const FOUNDERS: Founder[] = [
  {
    name: "Nishant Parihar",
    role: "Co-Founder & CEO",
    focus: "One question started the company the industry couldn't answer — did the window work? — and he stopped accepting 'sales said so' as the answer.",
    avatar: { skin: "#eab78f", hair: "#26272a", hairPath: "A", glasses: true, shirt: "#39424b" },
  },
  {
    name: "Rajendra Choudhary",
    role: "Co-Founder & CTO",
    focus: "Zero faces, sub-second counts, 12W of edge — he builds the instrument so the street is measured, never watched.",
    avatar: { skin: "#c68d59", hair: "#151619", hairPath: "B", glasses: false, shirt: "#6e4a42" },
  },
  {
    name: "Mihir Salian",
    role: "Co-Founder & CDO",
    focus: "He treats the window as the brand — the way a cover earns a shelf, the glass has to earn the street's pause.",
    avatar: { skin: "#eec39b", hair: "#5f4a33", hairPath: "C", glasses: false, shirt: "#3f5d5b" },
  },
]

export const NAV = [
  { label: "The Blind Spot", href: "#blindspot" },
  { label: "Core Journey", href: "#journey" },
  { label: "In-Store", href: "#atelier" },
  { label: "Proof", href: "#proof" },
  { label: "System", href: "#system" },
  { label: "Signals", href: "#metrics" },
  { label: "Sectors", href: "#sectors" },
  { label: "Mission", href: "#mission" },
  { label: "Privacy", href: "#privacy" },
  { label: "How", href: "#how" },
  { label: "Team", href: "#team" },
]

export const PRIMARY_NAV: { label: string; href: string }[] = [
  { label: "Blind Spot", href: "#blindspot" },
  { label: "Journey", href: "#journey" },
  { label: "Proof", href: "#proof" },
  { label: "System", href: "#system" },
  { label: "Privacy", href: "#privacy" },
]

export type NavLinkDef = { label: string; href: string; desc?: string; new?: boolean }
export type NavGroup = { label: string; id: string; links: NavLinkDef[] }

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Product",
    id: "product",
    links: [
      { label: "The Blind Spot", href: "#blindspot", desc: "The customers you never counted" },
      { label: "The Sensor", href: "#sensor", desc: "One box that sees your whole store", new: true },
      { label: "Core Journey", href: "#journey", desc: "Street to product consideration" },
      { label: "Inside the Store", href: "#atelier", desc: "Zones, gaze and pace" },
      { label: "The System", href: "#system", desc: "Sensor → verdict in under a second" },
      { label: "Signals", href: "#metrics", desc: "Twelve storefront answers" },
      { label: "Live Dashboard", href: "/dashboard", desc: "See the product working", new: true },
    ],
  },
  {
    label: "Company",
    id: "company",
    links: [
      { label: "Proof", href: "#proof", desc: "A/B win, measured on the glass" },
      { label: "Why AD Labs", href: "#why", desc: "The differentiation, in four beats" },
      { label: "Environments", href: "#sectors", desc: "Fashion, beauty, jewellery, premium" },
      { label: "Mission", href: "#mission", desc: "Witness, not spy" },
      { label: "Team", href: "#team", desc: "The founders behind the lab" },
      { label: "About AD Labs", href: "/about", desc: "The company in depth" },
    ],
  },
  {
    label: "Support",
    id: "support",
    links: [
      { label: "How to Start", href: "#how", desc: "Plug-and-play on your cameras" },
      { label: "Pricing", href: "#pricing", desc: "Pilot terms, built on your budget" },
      { label: "Privacy Charter", href: "#privacy", desc: "Intelligence without surveillance" },
      { label: "FAQ", href: "#faq", desc: "Straight answers" },
      { label: "Contact", href: "#contact", desc: "A human replies — no bots" },
    ],
  },
]

export const HERO = {
  kicker: "Physical Retail Intelligence, Reimagined",
  headlineA: "Your storefront",
  headlineB: "deserves a brain.",
  sub: "Online retail has a brain — analytics on every click. Physical retail — 90% of the market — is flying blind. AD Labs puts a small sensor in your store that watches the street the way the market was always watched: not who walks in, but who decides outside, and why some windows win.",
  demoCta: "Try the live demo",
  primaryCta: "Join the founding pilot",
  secondaryCta: "See How It Works",
  badgeTenant: "ORGANIC CLOTHING CO. · BANDRA, MUMBAI",
  badgePrivacy: "Zero Facial Storage · Local AI",
  ticker: ["PASS · 1.4m/s", "STOPPED · 4.8s", "ENTER"],
  cam: "RTSP CAM 01 · BANDRA W · 09:14:07",
  tracking: [
    { label: "PASSER 07", meta: "1.4 m/s → window", x: 62, y: 28 },
    { label: "STOP", meta: "gaze 4.8s", x: 79, y: 56 },
  ],
  live: [
    { label: "people on the street", value: 2481 },
    { label: "stopped at the glass", value: 186 },
    { label: "stop rate", value: 7.5, suffix: "%" },
  ],
  footline: ["ON-PREMISES EDGE TELEMETRY", "NO CLOUD VIDEO UPLOAD · ZERO PII"],
  marquee: ["See the movement.", "Understand the attention.", "Improve the store."],
}

/* The instrument — the small edge sensor every store can afford */
export const SENSOR = {
  index: "02",
  kicker: "The Instrument",
  h2a: "One small box.",
  h2b: "One complete brain.",
  sub: "A 12-watt sensor the size of a mini PC. Plug it in behind your front counter, connect it to the cameras you already own, and it starts learning the truth about your street — in the store, never in a cloud.",
  name: "AD LABS · EDGE OBSERVER",
  aliases: ["SENSOR UNIT", "ON-PREM AI", "ZERO FACE STORAGE"],
  installTitle: "Installed in the time it takes your barista to make a coffee",
  installSteps: [
    { num: "01", title: "Unbox", desc: "A fanless 12W edge box, one cable, one wall or shelf mount. That is the entire delivery." },
    { num: "02", title: "Connect", desc: "Plug into your existing PoE camera switch — your RTSP/NVR line keeps working exactly as it did." },
    { num: "03", title: "Verify", desc: "We map your window sightlines and zones, calibrate, and verify gaze accuracy before one number counts." },
  ],
  specs: [
    { label: "Power", value: "12W · PoE" },
    { label: "Install", value: "~2 hours on site" },
    { label: "Cameras", value: "Your existing RTSP/NVR" },
    { label: "Processing", value: "On-device, sub-second" },
    { label: "Offline", value: "Keeps counting, always" },
    { label: "Faces", value: "None. Ever." },
  ],
  watch: {
    kicker: "Watch it work",
    title: "60 seconds to understand your store",
    sub: "Installation → calibration → live dashboard → Monday Brief. A 60-second look at the Sensor in a real store.",
    cta: "Play the storyboard",
    stories: [
      { t: "DAY 0 · UNBOX", d: "The box lands behind the counter. One cable in, one handshake with your cameras." },
      { t: "DAY 1 · CALIBRATE", d: "Window and zones mapped. Verified 93% gaze accuracy before the first count." },
      { t: "LIVE · DASHBOARD", d: "Street footfall, stop rate, zone attention — live on the same dashboard." },
      { t: "MONDAY · BRIEF", d: "The verdict, three actions, audited numbers. The rhythm is now weekly." },
    ],
  },
}

/* Why a brand owner picks AD Labs — the differentiation page on the home flow */
export const WHY_US = {
  index: "10",
  kicker: "Why AD Labs",
  h2a: "Not another analytics tool.",
  h2b: "A new kind of intelligence.",
  sub: "Every tool today sells you a dashboard. We sell you a verdict: a sensor that reads consumer behaviour in the physics of the store, learns it, and tells you the one thing worth doing next.",
  purpose: {
    title: "What a brand owner gets",
    subtitle: "The channel you can finally measure the way you measure your website:",
    beats: [
      { t: "Street-to-sale visibility", d: "Know the full physical funnel — pass, stop, enter, engage — not just the till." },
      { t: "Decisions with evidence", d: "Every window change becomes a measured A/B, not a Monday-morning opinion." },
      { t: "A store that learns", d: "The sensor builds your store's normal — and flags what breaks it before it costs a week." },
      { t: "Privacy that sells it", d: "Zero faces, zero cloud video. A pitch you can make with a clear conscience." },
    ],
  },
  pillars: [
    {
      icon: "plug",
      k: "01",
      title: "Zero new hardware",
      desc: "Works with the cameras already above your floor. One cable, a wall mount, done.",
      answer: "Your security line stays unchanged — the sensor reads the same feed, never records it.",
    },
    {
      icon: "shield",
      k: "02",
      title: "Privacy by architecture",
      desc: "It cannot watch. It counts. There is no face data to store, leak or explain away.",
      answer: "Frames become vectors of motion in volatile memory, then vanish. The cloud sees a timestamp, a dwell, an entry.",
    },
    {
      icon: "verdict",
      k: "03",
      title: "Verdicts, not dashboards",
      desc: "The Monday Brief ends with three actions and the evidence behind each one.",
      answer: "Physical A/B on every rotation, with confidence bands. Keep or kill — decided by the street.",
    },
    {
      icon: "learn",
      k: "04",
      title: "Learns your store",
      desc: "Baselines built from your own history, not a category average from a slide deck.",
      answer: "Anomaly watch tuned to your rhythm — the sensor knows your store's normal as well as its staff.",
    },
  ],
  kpi: {
    title: "The promises we can prove",
    strip: [
      { value: "12", label: "behavioural signals, one sensor" },
      { value: "1 day", label: "from unboxing to a live count" },
      { value: "~2 hrs", label: "total installation time" },
      { value: "0", label: "faces stored, ever" },
      { value: "14", label: "day physical A/B verdict cycle" },
    ],
  },
  ip: {
    title: "The IP behind the promise",
    chips: [
      { t: "On-device behavioural telemetry", d: "pass · stop · dwell · enter from a plain RTSP feed, sub-second" },
      { t: "Anonymous spatial analytics", d: "3D occupancy mesh, zero biometrics" },
      { t: "Physical A/B attribution", d: "14-day keep-or-kill verdicts with confidence bands" },
      { t: "Edge inference on commodity compute", d: "12W box that survives internet drops" },
    ],
  },
}

export const BLINDSPOT = {
  index: "01",
  kicker: "The Blind Spot",
  h2a: "You know how many people visit your store.",
  h2b: "But do you know how many noticed it?",
  cards: [
    {
      num: "01",
      tag: "THE STREET",
      title: "People walking past",
      metric: "100% Street Footfall",
      desc: "Thousands pass by your storefront every day without breaking stride. Invisible, unrecorded potential.",
      insight: "Traditional counters miss the decision. It happens at the glass — not the till.",
      image: "/images/blindspot-pass.jpg",
    },
    {
      num: "02",
      tag: "THE HOOK · CRUCIAL",
      title: "One person stops",
      metric: "The Stop Moment (Gaze & Dwell)",
      desc: "A window display arrests attention. They slow down, turn their gaze, and pause for 4+ seconds.",
      insight: "The window is the store's true landing page. A 4.8-second pause at 94% gaze intensity is where commerce begins.",
      image: "/images/blindspot-stop.jpg",
      highlight: true,
    },
    {
      num: "03",
      tag: "THE THRESHOLD",
      title: "One person enters",
      metric: "Walk-In Conversion",
      desc: "Curiosity turns into physical action. They cross your threshold and become a retail opportunity.",
      insight: "Enter is the only number the till ever saw — the decision that produced it happened at the glass.",
      image: "/images/blindspot-enter.jpg",
    },
  ],
  closer: "Traditional counters only count who came inside.",
  closerBold: "AD Labs reveals the passers-by who decided outside.",
  context: [
    "~86–92% of India's retail value still moves through physical stores — e-commerce is just 8–14% of the market (Brickwork Ratings 2024 · PCMI 2025).",
    "Apparel & high-street capture rate — the % of passers-by who actually enter — typically lands at 5–15%; above 20% is rare (Pygmalios 2026).",
    "Raw door counters are known to overstate traffic by 18–35% — most retailers can't even see the leak (Ward 2026).",
  ],
  verdictLabel: "THE WINDOW IS THE FIRST VERDICT",
  verdict: "Shoppers judge a display in 3–8 seconds (Gajjar 2024) — before staff, before product, before the till. That near-instant impression is measured at the glass, not the register.",
}

export const JOURNEY = {
  index: "02",
  kicker: "Core Journey",
  h2: "Beyond footfall.",
  sub: "The complete behavioral continuum — from street attention to in-store product consideration.",
  funnelLabel: "Continuous Physical Funnel",
  funnelSub: "FROM STREET VISIBILITY TO BOUTIQUE ENGAGEMENT",
  bars: [
    { label: "Pass", value: 2481 },
    { label: "Stop", value: 186 },
    { label: "Enter", value: 39 },
    { label: "Explore", value: 34 },
    { label: "Engage", value: 18 },
  ],
  steps: [
    {
      step: "STEP 01",
      name: "PASS",
      count: 2481,
      countLabel: "Street Footfall",
      rate: "100%",
      rateLabel: "Base Street Volume",
      desc: "Pedestrians walking along your storefront perimeter.",
      metrics: ["Avg Pace: 1.4 m/s", "Street Width: 18m"],
      share: 100,
      answer: "All 2,481 people walked the same 18 metres of glass — the total opportunity the window competes for, every day.",
    },
    {
      step: "STEP 02",
      name: "STOP",
      count: 186,
      countLabel: "Attention Hook",
      rate: "7.5%",
      rateLabel: "Stop Rate",
      desc: "Passers-by who paused at the window for 4+ seconds.",
      metrics: ["Avg Window Dwell: 4.8s", "Gaze Intensity: 94%"],
      share: 7.5,
      answer: "The window earns a 4.8-second pause at 94% gaze intensity — stop is the storefront's true landing rate.",
    },
    {
      step: "STEP 03",
      name: "ENTER",
      count: 39,
      countLabel: "Threshold Cross",
      rate: "21.0%",
      rateLabel: "Stop-to-Enter",
      desc: "Attention converts into a physical visit through the door.",
      metrics: ["Threshold Velocity: 0.8 m/s"],
      share: 21.0,
      answer: "39 of 186 stoppers crossed the threshold. The door closes the deal the window started.",
    },
    {
      step: "STEP 04",
      name: "EXPLORE",
      count: 34,
      countLabel: "Zone Immersion",
      rate: "87.2%",
      rateLabel: "Active Browsing",
      desc: "Visitors moving through zones with deliberate engagement.",
      metrics: ["Top Zone: Leather Goods Island · 68% traffic share"],
      share: 87.2,
      answer: "87.2% of visitors browse deliberately — most flow to the Leather Goods Island, which takes 68% of in-store traffic.",
    },
    {
      step: "STEP 05",
      name: "ENGAGE",
      count: 18,
      countLabel: "Product Consideration",
      rate: "52.9%",
      rateLabel: "High-Intent Touch",
      desc: "Hands on product — the moment consideration becomes intent.",
      metrics: ["Avg Product Gaze: 8.4s", "Fitting Trials: 14"],
      share: 52.9,
      answer: "52.9% of explorers put hands on product — 8.4s of gaze on the hero vitrine, 14 fitting trials today.",
    },
  ],
  band: {
    title: "Full-Funnel Store Intelligence",
    sub: "From street sidewalk to high-touch checkout.",
    tags: ["Zero Face Biometrics", "100% Local Edge Compute", "Sub-Second Precision"],
  },
  demoNote: "Demo funnel for a single storefront day (Organic Clothing Co., Bandra). The same pipeline runs on your window from day one.",
}

export const ATELIER = {
  index: "04",
  kicker: "Inside The Boutique",
  h2: "What happens once they step inside?",
  sub: "In-store intelligence layered on your existing cameras — zones, gaze, pace and cohorts.",
  image: "/images/in-store-zones.jpg",
  camLabel: "BOUTIQUE INTERIOR CAM 02 · 3D OCCUPANCY MESH",
  ui: {
    store: "ORGANIC CLOTHING CO. · BANDRA FLAGSHIP",
    view: "IN-STORE INTELLIGENCE · CAM 02",
    live: "LIVE · TODAY",
    nav: "VIEWS",
  },
  tabs: [
    {
      id: "zones",
      label: "1. Zone Heatmaps",
      overlay: {
        tag: "ZONE 01 · APPAREL",
        big: "41% Traffic",
        lines: ["Avg Dwell: 6m 12s", "182 Shoppers"],
        note: "Zone H3 commands 55% of traffic; Zone F1 stays under-lit at 9% — a lighting problem, not a layout one.",
        move: "Relight Zone F1 and re-measure for 7 days — dead light reads as dead floor.",
      },
      pin: { title: "Hero Handbag Vitrine", value: "8.4s Gaze Time · 42% Touch Rate" },
      markers: [
        { title: "Zone H3 · Hero Rotunda", value: "55% traffic · 9m 45s", x: 62, y: 32 },
        { title: "Zone L2 · Leather Island", value: "68% traffic · 7m 04s", x: 34, y: 58 },
        { title: "Zone A1 · Apparel", value: "41% traffic · 6m 12s", x: 80, y: 68 },
        { title: "Zone F1 · Vitrine West", value: "9% traffic · under-lit", x: 18, y: 38 },
      ],
    },
    {
      id: "gaze",
      label: "2. Product Gaze & Sections",
      overlay: {
        tag: "HERO ZONE · ACCESSORIES",
        big: "68% Traffic",
        lines: ["Highest Store Density", "9m 45s Dwell"],
        note: "The hero vitrine holds an 8.4-second gaze — the longest single stare in the store.",
        move: "Capsule rail trails at 5.2s — after the launch, promote it over the sector leader.",
      },
      pin: { title: "Capsule Runway Rail", value: "5.2s Gaze Time · 24% Interaction" },
      markers: [
        { title: "Hero Handbag Vitrine", value: "8.4s gaze · 42% touch", x: 66, y: 30 },
        { title: "Capsule Runway Rail", value: "5.2s gaze · 24% touch", x: 38, y: 62 },
        { title: "Fragrance Counter", value: "6m 12s dwell · 55% touch", x: 84, y: 74 },
      ],
    },
    {
      id: "velocity",
      label: "3. Movement Velocity & Speed",
      overlay: {
        tag: "DECELERATION DETECTED",
        big: "0.3 m/s Browsing Pace",
        lines: ["Shoppers slow by 76% when entering the accessory rotunda."],
        note: "Deceleration is consideration — 0.3 m/s at the rotunda is where browsing becomes buying.",
        move: "Place the offer at the deceleration point, not the transit corridor at 1.3 m/s.",
      },
      pin: { title: "Transit Corridor", value: "1.3 m/s Pace" },
      markers: [
        { title: "Transit Corridor", value: "1.3 m/s — cold transit", x: 70, y: 20 },
        { title: "Entry flow", value: "0.8 m/s — hot zone", x: 16, y: 48 },
        { title: "Rotunda slowdown", value: "0.3 m/s browsing pace", x: 50, y: 60 },
      ],
    },
    {
      id: "cohorts",
      label: "4. Shopper Demographics",
      overlay: {
        tag: "ANONYMOUS COHORT TELEMETRY · TODAY",
        big: "Age 28–44 (62%)",
        lines: [
          "Primary Cohort",
          "Shopping Dynamic: 58% Solo · 42% Pair",
          "Peak Footfall Time: 16:30 – 18:45",
          "Fitting Room Conversion: 74%",
        ],
        note: "The 28–44 cohort peaks at 16:30 — and 74% of what reaches the fitting room converts.",
        move: "Staff pairs from 16:30 — pairs decide; solos research.",
      },
      pin: { title: "Advisory Salon", value: "Conversion: 38%" },
      markers: [
        { title: "Entry cohort · 28–44", value: "62% of stops", x: 20, y: 40 },
        { title: "Advisory Salon", value: "38% conversion · 15% traffic", x: 74, y: 46 },
        { title: "Fitting Rooms", value: "74% conversion", x: 56, y: 76 },
      ],
    },
  ],
  features: [
    {
      title: "Zone Dwell Share",
      sub: "Know your hottest sections",
      desc: "Which zones capture the most browsing time — and which floors traffic forgets.",
    },
    {
      title: "Product Gaze Duration",
      sub: "Measure fixture attention",
      desc: "Exact gaze time on hero products, vitrines and fixture drops.",
    },
    {
      title: "Movement Velocity",
      sub: "Track browsing speed",
      desc: "Where pace decelerates into consideration, and where corridors stay cold.",
    },
    {
      title: "Demographic Cohorts",
      sub: "Understand your audience",
      desc: "Privacy-safe age brackets and group dynamics across days and launches.",
    },
  ],
}

export const PROOF = {
  index: "07",
  kicker: 'The "Aha" Moment',
  h2: "Did your storefront work?",
  sub: "Connect merchandising changes with changes in customer behaviour.",
  chip: "PHYSICAL A/B MEASUREMENT",
  store: "Organic Clothing Co. · Bandra Flagship · Mumbai",
  before: {
    label: "BASELINE",
    value: "6.4%",
    metric: "Window Stop Rate",
    desc: "Traditional static mannequin installation.",
    image: "/images/window-before.jpg",
  },
  after: {
    label: "NEW ROTATION",
    badges: ["AFTER", "VERIFIED"],
    value: "7.3%",
    metric: "Window Stop Rate",
    desc: "Statistically measured over a 14-Day A/B Rotation.",
    image: "/images/window-after.jpg",
  },
  uplift: "↑ +14.6% observed uplift",
  demoNote: "Illustrative pilot scenario — sample window rotation, fourteen-day cycle. Your baseline, rotation and verdict are computed from your own window on your own street.",
  benchmark: "As an industry reference, storefront A/B programmes typically see a 3–8% conversion uplift when the best-scoring display gets scaled (V-Count, vendor benchmark) — the 14-day verdict is the only way to know which display that is.",
}

export const SYSTEM = {
  index: "05",
  kicker: "One Sensor. One Decision Point.",
  h2: "The sensor tracks behavior. The brand tracks context. The engine finds the correlation.",
  sub: "You stop guessing. You start knowing.",
  trio: [
    {
      k: "01",
      title: "Sensor tracks behavior",
      desc: "Pass, stop, dwell, enter — measured on-device from your existing RTSP/NVR cameras.",
      answer: "Four behaviours, measured on-device in under a second — pass, stop, dwell, enter. No video ever leaves the box.",
    },
    {
      k: "02",
      title: "Brand tracks context",
      desc: "Window resets, campaigns, staffing and layout — the changes you make, logged.",
      answer: "Your resets and campaigns become timestamped changes — so every verdict later attributes to a real move you made.",
    },
    {
      k: "03",
      title: "Engine finds correlation",
      desc: "Every Monday: what changed, what moved, and the three actions worth your time.",
      answer: "Each Monday the engine cross-references your calendar against the street's curve and returns three actions with evidence.",
    },
  ],
  interface: {
    kicker: "The Interface",
    h2: "Quiet clarity.",
    sub: "No endless dashboards. Just the vital signals you need to make decisions — and the staffing behind them.",
    decision: "Every decision returns as a verdict: what the street chose, when, and with what confidence. Keep or kill, decided by evidence.",
    fixes: [
      {
        num: "01",
        tag: "MANAGER REPORTING",
        chip: "SOLVED",
        desc: "The Monday Brief replaces the weekly report — audited, attributed, and three actions to take. No more Friday guessing.",
      },
      {
        num: "02",
        tag: "STAFFING",
        chip: "SOLVED",
        desc: "Peak windows (15–17h), zone dwell and solo-vs-pair dynamics show exactly where and when to place staff. Coverage follows the crowd, not the calendar.",
      },
      {
        num: "03",
        tag: "CONSUMER · RETAIL INTELLIGENCE",
        chip: "THE OFFER",
        desc: "From street attention to buyer behaviour — the questions the till could never answer, now measured at the glass.",
      },
    ],
    store: "Organic Clothing Co. · Bandra Flagship · Mumbai",
    live: "LIVE · TODAY",
    stats: [
      { label: "People today", value: 2481 },
      { label: "Stop rate", value: 7.5, suffix: "%" },
      { label: "Walk-ins", value: 39 },
    ],
    trend: "HOURLY ATTENTION TREND",
    trendDelta: "+14.6% vs baseline",
    hours: "09:00 — 21:00",
    cta: "Explore the insights",
  },
}

export type MiniViz = { kind: "line" | "area" | "donut" | "bars"; data?: number[]; value?: number }

export type MetricCard = {
  title: string
  desc: string
  stat: string
  delta: string
  deltaTone: "pos" | "neg" | "flat"
  hint: string
  why: string
  spark: number[]
  viz: "line" | "area" | "donut" | "bars" | "gauge" | "split" | "hours"
  value?: number
  peer?: number
  max?: number
  parts?: { label: string; value: number }[]
  hours?: number[]
}

export const METRICS: { index: string; kicker: string; h2: string; sub: string; note: string; items: MetricCard[] } = {
  index: "08",
  kicker: "What a brand can answer",
  h2: "Twelve signals. One sensor.",
  sub: "From impression to conversion — the storefront questions you could never ask before.",
  note: "Illustrative demo sample — a single storefront day (Organic Clothing Co., Bandra). Real numbers compute on-device from your own cameras from the first day of measurement.",
  items: [
    {
      title: "Stop rate",
      desc: "How many passers-by paused at your window.",
      stat: "7.5%",
      delta: "+0.4pp today",
      deltaTone: "pos",
      hint: "vs yesterday",
      why: "The window earns it. If stop rate falls, the street is telling you the glass stopped working.",
      viz: "line",
      spark: [6.8, 7.0, 7.1, 7.2, 7.3, 7.5],
    },
    {
      title: "Look time",
      desc: "How long they gazed — casual glance or deep attention.",
      stat: "39%",
      delta: "deep > 4s",
      deltaTone: "pos",
      hint: "vs last week",
      why: "Deep attention is the predictor of purchase. A flowing crowd means nothing; a pausing crowd means commerce.",
      viz: "donut",
      value: 39,
      spark: [30, 32, 34, 37, 38, 39],
    },
    {
      title: "Stop-to-enter rate",
      desc: "Of those who stopped, how many crossed the threshold.",
      stat: "21%",
      delta: "+1.2pp this wk",
      deltaTone: "pos",
      hint: "vs last week",
      why: "The glass is a door. Move the hero into the sightline and this number moves with it.",
      viz: "line",
      spark: [18.5, 19.2, 19.8, 20.4, 20.8, 21.0],
    },
    {
      title: "Street footfall",
      desc: "Total opportunity walking past, by hour and day.",
      stat: "2,481",
      delta: "today · peak 15–17",
      deltaTone: "flat",
      hint: "peak 15–17",
      why: "This is the addressable market of your storefront — staff and creative should follow its curve.",
      viz: "area",
      spark: [2.1, 2.2, 2.2, 2.3, 2.4, 2.5, 2.4],
    },
    {
      title: "Stop rate (week)",
      desc: "Seven-day window stop performance — the trendline.",
      stat: "11.4%",
      delta: "+2.5pp vs peer",
      deltaTone: "pos",
      hint: "vs peer 8.9%",
      why: "The weekly trend is the scoreboard. Peer context turns it into a judgement: is the glass winning the street?",
      viz: "bars",
      peer: 8.9,
      spark: [9.2, 9.6, 10.2, 10.8, 11.0, 11.4],
    },
    {
      title: "Zone dwell",
      desc: "Where attention lives inside the store.",
      stat: "9m 45s",
      delta: "hero rotunda",
      deltaTone: "pos",
      hint: "vs last week",
      why: "Dwell is the store's gravity map. Where it gathers, your best product and best staff should stand.",
      viz: "area",
      spark: [8.6, 8.9, 9.1, 9.4, 9.7, 9.8],
    },
    {
      title: "Dead zones",
      desc: "Floor areas traffic forgets — flagged and fixable.",
      stat: "18%",
      delta: "−3pp this wk",
      deltaTone: "pos",
      hint: "vs last week",
      why: "Dead zones are free revenue. A relight or a reset returns them, and the improvement is measurable in days.",
      viz: "donut",
      value: 18,
      spark: [24, 23, 21, 20, 19, 18],
    },
    {
      title: "Product gaze",
      desc: "Which fixtures and heroes earn real attention.",
      stat: "8.4s",
      delta: "hero handbag vitrine",
      deltaTone: "pos",
      hint: "vs last week",
      why: "Gaze maps desire. The fixture that wins it should be the fixture the window sells first.",
      viz: "line",
      spark: [7.6, 7.8, 7.9, 8.1, 8.3, 8.4],
    },
    {
      title: "Movement velocity",
      desc: "Where shoppers decelerate into consideration.",
      stat: "0.3 m/s",
      delta: "rotunda slow-down",
      deltaTone: "pos",
      hint: "vs last week",
      why: "Deceleration is consideration. When you can see it, you can place the offer exactly where it happens.",
      viz: "gauge",
      value: 0.3,
      max: 1.4,
      spark: [1.1, 0.9, 0.7, 0.5, 0.4, 0.3],
    },
    {
      title: "Group size",
      desc: "Solo browsers vs pairs vs parties — by daypart.",
      stat: "58 / 42",
      delta: "solo / pair",
      deltaTone: "flat",
      hint: "solo vs pair ratio",
      why: "Solos research, pairs decide. The floor conversation each needs is different — and now you know which is coming.",
      viz: "split",
      parts: [
        { label: "solo", value: 58 },
        { label: "pair", value: 42 },
      ],
      spark: [55, 56, 57, 58, 58, 58],
    },
    {
      title: "Peak windows",
      desc: "The exact hours your storefront performs.",
      stat: "15–17h",
      delta: "attention peak",
      deltaTone: "pos",
      hint: "daily peak",
      why: "Two peak windows. Staff them like mornings are staffed — coverage in a peak converts directly.",
      viz: "hours",
      hours: [2, 4, 6, 9, 7, 6, 8, 14, 16, 12, 9, 8, 7, 6, 5, 4],
      spark: [5, 7, 9, 10, 11, 10, 9],
    },
    {
      title: "Change attribution",
      desc: "Did the new window actually move the numbers?",
      stat: "+14.6%",
      delta: "verified A/B · 14d",
      deltaTone: "pos",
      hint: "verified A/B",
      why: "Keep or kill, decided by the street. The answer arrives as an A/B verdict on two real rotations.",
      viz: "bars",
      spark: [10.2, 10.8, 11.5, 12.1, 12.6, 13.1, 12.0],
    },
  ],
}

export const SECTORS = {
  index: "09",
  kicker: "Environments",
  h2: "Built for spaces where impression is everything.",
  context: "India runs on ~13 million independent shops, and they still ring up ~79–88% of a retail market already past USD 1 trillion (RAI · Redseer 2025). The physics of attention is universal — the instrument adapts.",
  cards: [
    {
      id: "fashion",
      num: "01",
      title: "Fashion",
      sub: "Haute couture & ready-to-wear flagships",
      tag: "SEASONAL COLLECTIONS",
      image: "/images/sector-fashion.jpg",
    },
    {
      id: "beauty",
      num: "02",
      title: "Beauty",
      sub: "Fragrance & luxury cosmetic ateliers",
      tag: "INTERACTIVE COUNTERS",
      image: "/images/sector-beauty.jpg",
    },
    {
      id: "jewellery",
      num: "03",
      title: "Jewellery",
      sub: "High jewellery & fine timepiece salons",
      tag: "HERO VITRINES",
      image: "/images/sector-jewellery.jpg",
    },
    {
      id: "premium",
      num: "04",
      title: "Premium Retail",
      sub: "Concept destinations & department stores",
      tag: "CORNERSTONE ENTRANCES",
      image: "/images/sector-premium-retail.jpg",
    },
  ],
}

export const PRIVACY = {
  index: "06",
  kicker: "Architectural Principle",
  h2: "Intelligence without surveillance.",
  sub: "Privacy is not a policy footer here. It is the architecture.",
  dpdp: {
    title: "Aligned to the DPDP Act 2023 by construction",
    body: "Anonymous aggregate behavioural analytics are not 'personal data' under the Act (s.2(1)(t)) — no faces, no identifiers, nothing to trade. Notice and consent rules (s.5–6) govern identifiable data; we simply never produce it. The alternative design — storing camera feeds or facial data — is what exposes retailers to penalties up to ₹250 crore.",
    chips: ["s.2(1)(t) — not personal data", "₹250 crore avoided by design", "consent-free by construction"],
    source: "Digital Personal Data Protection Act 2023 · MeitY — core obligations fully effective 13 May 2027",
  },
  principles: [
    {
      num: "01",
      title: "Video stays local.",
      desc: "Frames are processed in volatile memory inside your store. Nothing is recorded, nothing is uploaded.",
      answer: "Frames are reduced to vectors of motion in volatile memory, then discarded — recording never begins.",
      chips: ["in-memory", "0 uploaded"],
    },
    {
      num: "02",
      title: "No persistent customer identity.",
      desc: "No facial recognition, no re-identification, no cross-store tracking. Every person is an anonymous vector.",
      answer: "Every person is an anonymous vector of behaviour — no face map, no ID, no cross-store trail to follow.",
      chips: ["0 faces", "0 re-identification"],
    },
    {
      num: "03",
      title: "Only anonymised behavioural events leave the store.",
      desc: "Pure numbers: a timestamp, dwell duration in seconds, and entry status. That is all the cloud ever sees.",
      answer: "The cloud only ever sees a timestamp, a dwell in seconds, and an entry status. That is the entire payload.",
      chips: ["ts · dwell · entry", "pure numbers"],
    },
  ],
  pipeline: [
    { stage: "ORIGIN", title: "Store Camera", desc: "Existing RTSP / NVR feeds" },
    { stage: "PROCESSING", title: "Local Intelligence", desc: "On-prem edge inferencing", badge: "Zero Cloud Video" },
    { stage: "OUTPUT", title: "Anonymised Insights", desc: "Pure numerical telemetry" },
  ],
}

export const HOW = {
  index: "12",
  kicker: "How it works",
  h2: "Your cameras become the instrument. Monday brings the verdict.",
  steps: [
    { num: "01", title: "Connect", desc: "Existing RTSP/NVR cameras. Plug-and-play edge compute. Zero new hardware.", answer: "Measured on-device — pass, stop, dwell and enter on the same dashboard." },
    { num: "02", title: "Calibrate", desc: "We map your windows, zones and light. The system learns your store's rhythm.", answer: "We tune zones and thresholds until the numbers reflect your store's rhythm." },
    { num: "03", title: "Monday Brief", desc: "Every Monday: the verdict, three actions, benchmark context. Fifteen minutes, done.", answer: "A physical A/B verdict on every move the window made." },
  ],
  compat: "COMPATIBLE WITH EXISTING RTSP/NVR STREAMS · ZERO HARDWARE OVERHAUL",
  wishlist: {
    kicker: "Join the pilot list",
    h2: "What happens outside your store matters. Start understanding it.",
    sub: "Tell us about your flagship. A human from the lab reviews your camera setup and sketches a scope.",
    successTitle: "You're on the runway.",
    successBody: "We'll review your storefront camera setup with you and schedule installation.",
    successNote: "Confirmation will be sent to",
    feedbackQ: "Was this page clear?",
    feedbackYes: "Yes, crystal",
    feedbackNo: "Not yet",
    feedbackThanks: "Thank you — noted.",
  },
}

export const PILOT_FORM = {
  title: "Exclusive Retail Pilot Program",
  h2: "Deploy AD Labs in your flagship store.",
  sub: "Plug-and-play with the cameras you already own. First stop-rate report from your first full day of measurement.",
  fields: {
    brand: { label: "Retail Brand / House Name", placeholder: "e.g. Maison Laurent" },
    sector: {
      label: "Sector",
      options: [
        "Fashion & Apparel",
        "Fashion & Haute Couture",
        "Beauty & Cosmetics",
        "Jewellery & Watches",
        "Department Store / Concept",
        "Premium Footwear",
      ],
    },
    locations: {
      label: "Store Locations",
      options: ["1 Flagship Location", "1-5 Stores", "2 - 5 Stores", "6 - 20 Stores", "20+ Global Network"],
    },
    problem: {
      label: "What problem should we solve first?",
      options: [
        "Window & display — which windows actually pull people in",
        "Front-of-store — why people walk past without stopping",
        "Conversion — link street traffic to in-store sales",
        "Staffing & scheduling around real footfall",
        "In-store dead zones & shopper journey",
        "Something else — I'll describe it below",
      ],
    },
    budget: {
      label: "How should we scope your pilot? (helps us shape exposure)",
      options: [
        "One flagship, start at the window",
        "Two to five stores, benchmark together",
        "A network rollout, driven by evidence",
        "Value-first — show me before I commit",
      ],
    },
    detail: { label: "Describe the problem in your own words (optional)", placeholder: "e.g. Our entrance window gets footfall but nobody comes in…" },
    email: { label: "Executive / Work Email", placeholder: "name@brand.com" },
  },
  note: "Hardware Guarantee: Zero new cameras required. Works with your existing IP camera infrastructure via local plug-and-play edge compute.",
  submit: "Request Pilot Access",
  successTitle: "Pilot Request Received.",
  successBody: "Our partner team reviews your storefront camera setup with you and schedules installation.",
  return: "Return to Website",
}

export const MISSION = {
  index: "10",
  kicker: "Our Mission",
  h2: "The storefront deserves an answer.",
  sub: "Physical retail has been flying blind since glass windows were invented. We turn the camera you already own into an honest witness — so a boutique owner knows what the street decided, not what the spreadsheet guessed.",
  image: "/images/window-after.jpg",
  principles: [
    {
      title: "Witness, not spy",
      desc: "We measure behaviour as numbers. Nobody is watched, stored or identified — ever.",
      answer: "Frames are reduced to vectors of motion in volatile memory and discarded — 179k events a day, zero faces stored.",
      chips: ["0 faces stored", "179k events / day"],
    },
    {
      title: "Decision-grade",
      desc: "Every statistic ships with its evidence chain: how measured, how verified, how it links to a move.",
      answer: "Every figure on this page is recomputed from raw events before it ships — if it can't be reproduced by hand, it doesn't print.",
      chips: ["every stat audited", "×3 blind checks"],
    },
    {
      title: "On-premise by design",
      desc: "Video never leaves your store. The cloud sees numbers only — zero surveillance transfer.",
      answer: "Camera data stays inside a 12W box at your store — the store keeps counting even with the internet down.",
      chips: ["0 cloud upload", "12W edge box"],
    },
  ],
  stat: { value: 10, suffix: "/10", label: "flagship seats in the founding cohort — 0 filled so far" },
  context: "India's retail market is roughly USD 0.94–1.06 trillion (2024) and is projected to nearly double by 2030 (BCG–RAI · Deloitte–FICCI). Yet analytics adoption remains 62% concentrated in large enterprises — the small shop shelf is wide open (IMARC).",
}

export const ABOUT = {
  hero: {
    kicker: "The Lab",
    h2a: "The storefront",
    h2b: "deserves an answer.",
    sub: "AD Labs builds physical retail intelligence — an honest witness on the camera you already own, so boutique owners know what the street decided, not what the spreadsheet guessed. Founded 2026 · Bengaluru, India.",
    stats: [
      { value: "86–92%", label: "of Indian retail value still moves through physical stores (Brickwork Ratings 2024 · PCMI 2025)" },
      { value: "5–15%", label: "typical capture rate — passers-by who actually enter (Pygmalios 2026)" },
      { value: "~13M", label: "independent shops ring up ~79–88% of retail (RAI · Redseer 2025)" },
    ],
  },
  vision: {
    title: "A world where no store flies blind again.",
    body: "The internet made digital retail measurable to the millisecond. Physical retail has been flying blind since glass windows were invented. Our vision is the parity: every shopfront as measurable as its own P&L — and intelligence that grows in the same direction as privacy, never against it.",
  },
  mission: {
    title: "Turn the camera you own into an honest witness.",
    body: "We measure the street before the door and the floor past it — on-device, from the cameras a store already owns. Then we ship the answer as a Monday Brief: a verdict, the evidence, and three actions worth taking. No dashboards to babysit. No identity captured. Just the number and the move.",
  },
  problem: {
    index: "02",
    kicker: "THE PROBLEM",
    title: "The problem",
    lead: "You know how many people visit your store. You do not know how many noticed it.",
    points: [
      { num: "01", text: "Traditional counters only count who came inside — the decision happened outside, at the glass, in the seconds before the door." },
      { num: "02", text: "Windows are changed on opinion, campaigns judged by a sales number blurred by a dozen other variables." },
      { num: "03", text: "A flagship spends its budget on the glass and never learns whether the glass worked." },
    ],
    stat: { value: "5–15%", label: "of passers-by typically enter a storefront — the 85%+ leak is usually unmeasured (Pygmalios 2026)" },
  },
  solution: {
    index: "03",
    kicker: "THE SOLUTION",
    title: "The solution",
    sub: "One sensor. One decision point. You stop guessing. You start knowing.",
    points: [
      { num: "01", text: "A 12W edge box plugs into your existing PoE / RTSP / NVR camera line — no new hardware, no heavy setup." },
      { num: "02", text: "It measures the continuous physical funnel — pass · stop · enter · explore · engage — on-device, sub-second." },
      { num: "03", text: "Every Monday it ships the verdict: what changed, what moved, and three actions worth your time." },
    ],
  },
  usp: {
    index: "04",
    kicker: "AD LABS USP",
    title: "Why it's different",
    sub: "Four sentences about how we build. Everything else is a spec sheet.",
    cards: [
      {
        num: "01",
        title: "Zero-new-hardware",
        desc: "Plug-and-play with the cameras you already own.",
        answer: "One PoE cable and a wall mount — no electrician, no cloud subscription.",
      },
      {
        num: "02",
        title: "Privacy by architecture",
        desc: "It literally cannot watch. It counts.",
        answer: "No faces, no re-identification, no cloud video. Only a timestamp, a dwell in seconds, and an entry status leave the store.",
      },
      {
        num: "03",
        title: "Verdicts, not dashboards",
        desc: "Numbers that end in a move.",
        answer: "A physical A/B engine — 14-day keep-or-kill verdicts decided by the street, plus the Monday Brief's three actions.",
      },
      {
        num: "04",
        title: "Learns your store",
        desc: "Not a template model.",
        answer: "Store-specific baselines and anomaly watch — your Monday is compared to your own history, not a category average.",
      },
    ],
  },
  ip: {
    index: "06",
    kicker: "INTELLECTUAL PROPERTY",
    title: "What we own",
    sub: "The engineering that makes the promise hold.",
    points: [
      { num: "01", title: "On-device behavioural telemetry", desc: "Pass · stop · dwell · enter recognised from a plain RTSP / NVR feed — sub-second, inside the store." },
      { num: "02", title: "Anonymous spatial analytics", desc: "A 3D occupancy mesh over your existing cameras: zones, trajectories and cohorts — with zero biometrics." },
      { num: "03", title: "Physical A/B attribution", desc: "A 14-day window-resolution experimental engine — which reset moved the street, with confidence bands." },
      { num: "04", title: "Edge inference on commodity compute", desc: "A 12W PoE box that keeps counting with the internet gone — no cloud video, no surveillance transfer." },
    ],
  },
  status: {
    index: "07",
    kicker: "WHERE WE ARE",
    title: "Honest status, on record.",
    body: "Founded 2026 in Bengaluru. We are currently accepting applications for the 10-seat founding pilot cohort across India.",
    points: [
      { num: "01", text: "Flagship pilot enrollment open" },
      { num: "02", text: "Bengaluru engineering lab" },
      { num: "03", text: "Sub-second on-prem inference engine" },
    ],
    cta: "Join the founding cohort",
  },
  product: {
    index: "08",
    kicker: "THE PRODUCT",
    title: "The product",
    sub: "From street attention to buyer's decision — one line of sight.",
    steps: [
      { num: "01", title: "Plug and play", desc: "Connect. The 12W edge box reads your PoE camera line — zero new hardware, zero network changes.", answer: "Footfall and stop rate appear on the same dashboard as they happen." },
      { num: "02", title: "Calibrate", desc: "We map your windows, zones and light. The system learns your store's rhythm.", answer: "Zones and thresholds are tuned until the numbers reflect your store's rhythm." },
      { num: "03", title: "Every Monday", desc: "Brief. The verdict, three actions, benchmark context. Fifteen minutes, done.", answer: "A physical A/B verdict on every move the window made." },
    ],
    ctaLabel: "Explore the live dashboard",
    ctaSub: "or watch how the system fits into your store —",
  },
  team: {
    index: "10",
    kicker: "The Lab",
    title: "Small team. Singular obsession.",
    sub: "Retail people and machine people — building the instrument the street was missing.",
  },
  demoNote: "Illustrative sample across the home page covers a single storefront day — real numbers compute on-device from your own cameras from the first day of measurement.",
}

export const PRICING = {
  index: "13",
  kicker: "Pilot Pricing",
  h2: "Priced for the pilot, not the prospectus.",
  sub: "We're not selling a subscription — we're piloting an instrument. Tell us your budget and store count on a call, and we'll shape the pilot around it.",
  plans: [
    {
      name: "Single Store",
      tag: "START AT THE WINDOW",
      desc: "One flagship, the glass, and the Monday Brief.",
      includes: [
        "1 storefront + edge box",
        "Verified stop rate from day one",
        "Monday Brief for one store",
        "Privacy architecture by default",
      ],
      price: "Pilot terms — we'll tell you on a 10-minute call",
      cta: "Ask pilot pricing",
    },
    {
      name: "Retail Group",
      tag: "MOST COMMON PILOT",
      desc: "Two to five stores, one benchmark to beat.",
      includes: [
        "Up to 5 storefronts",
        "Cross-store benchmarking",
        "Peak staffing windows",
        "Dedicated onboarding",
      ],
      price: "Custom pilot terms",
      cta: "Shape a pilot",
      featured: true,
    },
    {
      name: "Enterprise Network",
      tag: "FOR CHAINS",
      desc: "Six or more doors, rolled out on evidence.",
      includes: [
        "Network-wide deployment",
        "Physical A/B on every window",
        "Executive Monday Brief",
        "On-site support + SLA",
      ],
      price: "Scoped engagement",
      cta: "Plan a rollout",
    },
  ],
  bottom: "No lock-ins. No seat counts. If the glass proves itself, we talk about a wider pilot.",
}

export const FAQ = {
  index: "14",
  kicker: "Common Questions",
  h2: "Questions every store owner asks.",
  sub: "Straight answers, fast. For anything deeper, the contact form below reaches a human directly.",
  items: [
    {
      q: "Do we need to buy any new hardware?",
      a: "No. The 12W edge box plugs into your existing PoE / RTSP / NVR camera line — one cable and a wall mount. No electrician, no camera upgrades.",
    },
    {
      q: "Is this surveillance? Do you ever see faces?",
      a: "No. Frames are reduced to anonymous behavioural vectors — position, pace, pause — inside the store, in volatile memory, and discarded. There is no face map, no re-identification, and nothing to look at later.",
    },
    {
      q: "Where does our data go?",
      a: "Nowhere. Video never leaves your store. When the cloud is used at all, it only receives a timestamp, a dwell time in seconds, and an entry status.",
    },
    {
      q: "How do you prove a window 'worked'?",
      a: "We run a physical A/B: two window rotations, measured over 14 days on your street. The verdict — keep or kill — ships with confidence bands, not opinions.",
    },
    {
      q: "How fast do we get results?",
      a: "Stop rate is live from your first full day of measurement. The Monday Brief then arrives weekly — a verdict, the evidence, and three actions.",
    },
    {
      q: "What happens if our internet drops?",
      a: "The store keeps counting. The edge box runs standalone and syncs its summary once the line returns — the instrument degrades gracefully, or not at all.",
    },
    {
      q: "What does a pilot actually look like?",
      a: "Scoped to one flagship. We map your windows and zones, install on your existing cameras, and hand you a weekly Monday Brief for the pilot term. You decide keep-or-kill with real numbers.",
    },
    {
      q: "Do we have space for a flagship location?",
      a: "Our instrument measures footfall, gaze, and dwell across your existing window configuration. We’ll tell you whether a dedicated flagship is justified — or whether the current layout is already at capacity.",
    },
    {
      q: "How do you price?",
      a: "Pilot-first. We shape a pilot from your budget and store count on a short call — no lock-ins, no seat counts. Tell us what feels right and we build the terms around it.",
    },
    {
      q: "Is this compliant with India's DPDP Act 2023?",
      a: "Compliant by construction. Anonymous aggregate behavioural analytics are not 'personal data' under the Act (s.2(1)(t)) — no faces, no IDs, nothing to trade. Because we never store camera feeds or identifiable data, the notice, consent and breach duties (s.5–8) don't attach to us, and we never carry the exposure they were built to guard against. Core obligations phase in through 13 May 2027; our architecture already matches the end-state.",
    },
  ],
}

export const CONTACT = {
  index: "15",
  kicker: "Talk to the lab",
  h2: "Tell us about your storefront.",
  sub: "Pilot requests, storefront questions, or partner programmes — a human from the lab replies.",
  email: "sales@adlabs.in",
  city: "Bengaluru, India",
  response: "A human replies",
  fields: {
    name: { label: "Your name", placeholder: "e.g. Aisha Verma" },
    email: { label: "Work email", placeholder: "name@brand.com" },
    brand: { label: "Retail brand / house", placeholder: "e.g. Maison Laurent" },
    sector: {
      label: "Store role",
      placeholder: "Select what you need",
      options: ["Window & storefront intelligence", "Pilot with a budget in mind", "Partner / integration programme", "Press & analyst", "Something else"],
    },
    message: { label: "What should we measure first?", placeholder: "e.g. Our entrance window gets footfall but nobody comes in…" },
  },
  submit: "Send to the lab",
  successTitle: "Message received.",
  successBody: "A human from the lab reads every message that lands here.\n\nFor anything urgent, write to sales@adlabs.in directly.",
}
