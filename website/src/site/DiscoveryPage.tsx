"use client"

import { useEffect, useState } from "react"
import type { FormEvent, ReactNode } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  ArrowRight,
  ArrowLeft,
  Check,
  Send,
  Loader2,
  Target,
  TrendingUp,
  ShieldCheck,
  Users,
  BarChart3,
  Layers,
  Megaphone,
  FileText,
  Ruler,
  Plug,
  CalendarCheck,
  Trophy,
  Box,
  LayoutDashboard,
  FlaskConical,
  Activity,
  Eye,
  Lock,
  Database,
  Mail,
  MapPin,
  Clock,
  BadgeCheck,
  CircleOff,
  ClipboardList,
  Receipt,
  Video,
  Gauge,
  AlertTriangle,
} from "lucide-react"
import { BRAND } from "../data/site"
import { submitViaEmail } from "../utils/mailto"
import { Nav } from "./Nav"
import { Footer } from "./Footer"
import { Reveal } from "../components/Reveal"
import { EventStream } from "../components/EventStream"
import Link from "next/link"

const EASE = [0.22, 1, 0.36, 1] as const

const scrollToId = (id: string) => {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" })
}

/* ============================================================ */
/*  DATA — the offer, the timeline, the guarantees               */
/* ============================================================ */

const STAT_STRIP = [
  { value: "12", label: "signals from one sensor" },
  { value: "1 day", label: "from unboxing to live" },
  { value: "0", label: "new cameras to buy" },
  { value: "0", label: "faces ever stored" },
]

const DELIVERABLES = [
  {
    icon: Box,
    kicker: "01 · THE INSTRUMENT",
    title: "A 12W box that thinks on site",
    body: "One Edge Observer unit plugs into the cameras you already own. Everything is processed on-device — no cloud video, no stored faces, ever.",
    points: ["Plugs into your existing RTSP / NVR feed", "Runs offline — counts even when the internet drops", "Sleeps on a PoE cable; no new hardware, no network change"],
    spec: "12W · PoE · on-device inference",
    visual: "edge" as const,
  },
  {
    icon: LayoutDashboard,
    kicker: "02 · THE DASHBOARD",
    title: "Your storefront, live and legible",
    body: "A real-time view of the signals that decide revenue — who stopped, who entered, which zones pulled attention and when.",
    points: ["Street footfall, stop rate, look time, entry conversion", "Zone attention & pace inside the store", "Anomaly alerts before a trend costs you"],
    spec: "Live demo: /dashboard",
    visual: "hud" as const,
  },
  {
    icon: FileText,
    kicker: "03 · THE MONDAY BRIEF",
    title: "Three actions, every single Monday",
    body: "A 15-minute read for the founder. Baselines, the three changes that matter this week, and the numbers behind them — auditable, not authored.",
    points: ["Delivered every Monday before the store opens", "Each action traceable to a measured signal", "Your numbers compared to your own history — not a category average"],
    spec: "Monday · 07:30 · ~15 min read",
    visual: "brief" as const,
  },
  {
    icon: FlaskConical,
    kicker: "04 · THE A/B ENGINE",
    title: "Physical A/B. Measured on the glass.",
    body: "Two window treatments run head-to-head for 14 days. You get a keep-or-kill verdict with an uplift number — the debate ends on data, not opinion.",
    points: ["Test hero product placement, lighting, signage", "Same store, same street, controlled window", "Verdict with measured uplift you can action"],
    spec: "14-day cycles · keep / kill verdict",
    visual: "ab" as const,
  },
]

const TIMELINE = [
  {
    icon: Plug,
    day: "DAY 0",
    title: "Plug in",
    duration: "~2 hours on site",
    body: "The Edge Observer lands on a PoE cable and reads your existing cameras. No network change, no new infrastructure.",
  },
  {
    icon: Ruler,
    day: "DAY 1",
    title: "Calibrate",
    duration: "baselined & verified",
    body: "We map your zones and window sightline, then baseline the store — verified at 93% gaze accuracy before the first number counts.",
  },
  {
    icon: CalendarCheck,
    day: "DAY 7",
    title: "First Monday Brief",
    duration: "first weekly cadence",
    body: "Your first Monday Brief lands after one full week of measurement — baselines, three actions, audited numbers. The weekly rhythm is now live.",
  },
  {
    icon: Trophy,
    day: "DAY 14",
    title: "First A/B verdict",
    duration: "first keep / kill",
    body: "The first 14-day rotation closes with a measured uplift — verdict in hand. The engine keeps cycling from here while anomaly alerts stay live.",
  },
]

const GUARANTEES = [
  { icon: Eye, title: "Zero faces stored", body: "Faces blur before anything is kept — there is no face data to leak." },
  { icon: Lock, title: "Zero cloud video", body: "Raw footage stays in the store; only counts travel." },
  { icon: Database, title: "On-device by design", body: "The system cannot watch — it counts. Architecture, not policy." },
  { icon: ShieldCheck, title: "DPDP 2023 aligned", body: "Built to Indian retail and DPDP Act 2023 expectations." },
]

/* ============================================================ */
/*  DATA — the questionnaire                                     */
/* ============================================================ */

const PAIN_POINTS = [
  {
    id: "footfall",
    icon: Ruler,
    tag: "THE STREET",
    label: "Blind to the passers-by who decide outside",
    sub: "You count who enters, not who pauses at the glass and walks on. That decision is the leak — and it is invisible today.",
  },
  {
    id: "silos",
    icon: TrendingUp,
    tag: "THE SPLIT",
    label: "Storefront, campaign and store speak different languages",
    sub: "The window, the window campaign and the store each keep their own numbers. Nobody joins them into one verdict.",
  },
  {
    id: "guesswork",
    icon: Target,
    tag: "THE DEBATE",
    label: "Window changes run on opinion",
    sub: "No physical A/B, no measured result — the loudest voice on Monday morning decides what the glass shows this week.",
  },
  {
    id: "privacy",
    icon: ShieldCheck,
    tag: "THE BLOCKER",
    label: "Privacy risk keeps teams from even trying",
    sub: "Face-based analytics feel invasive and legally heavy. So most retailers simply skip the measurement altogether.",
  },
]

const PRIORITIES: Record<string, string> = {
  footfall: "Blind to the people who walk past",
  silos: "Storefront and campaigns live apart",
  guesswork: "Window changes run on opinion",
  privacy: "Privacy risk keeps teams from trying",
}

const TRACKING_OPTIONS = [
  {
    id: "nothing",
    icon: CircleOff,
    label: "Nothing — gut feel",
    note: "Baseline zero. That is the point of Day 1 — every pilot starts from a real number, not an impression.",
  },
  {
    id: "manual",
    icon: ClipboardList,
    label: "Manual counts",
    note: "Peak hours are the ones nobody counts — the visits that leak are exactly the ones a clipboard misses.",
  },
  {
    id: "pos",
    icon: Receipt,
    label: "POS / sales only",
    note: "The till tells you what sold, not why the glass earned it. We add the street layer that sits before the till.",
  },
  {
    id: "cctv",
    icon: Video,
    label: "CCTV, never counted",
    note: "Security feeds watch; they do not measure. Same cable, new lane — no camera, no infra change.",
  },
  {
    id: "vendor",
    icon: Gauge,
    label: "A vendor dashboard",
    note: "Dashboards can impress; an instrument has to act. The difference is a verdict tied to a measured change.",
  },
] as const

const STORE_FORMATS = [
  { id: "flagship", label: "High-street flagship" },
  { id: "mall", label: "Mall unit" },
  { id: "fb", label: "Café / F&B" },
  { id: "airport", label: "Airport boutique" },
  { id: "showroom", label: "Showroom / experience" },
] as const

const CAMERA_STACK = [
  { id: "ip", label: "Yes — IP / NVR with RTSP", hint: "Day 0 works out of the box." },
  { id: "mixed", label: "Mixed / not sure", hint: "We check the recorder model on the Day-0 call." },
  { id: "analog", label: "No — analog / dome CCTV", hint: "Still viable — we bridge at the recorder, no new cameras." },
] as const

const SUCCESS_METRICS = [
  { id: "walkins", label: "More walk-ins", hint: "Raise the street→door conversion" },
  { id: "window", label: "Weekly window verdicts", hint: "Keep / kill decisions on the glass" },
  { id: "labour", label: "Staffing at peaks", hint: "Right people on the attention curve" },
  { id: "displays", label: "Fix the dead zones", hint: "Relight what traffic forgets" },
] as const

const FEATURES = [
  { id: "stoprate", label: "Window stop rate", group: "Retail", icon: Target, detail: "Who pauses at the glass and for how long" },
  { id: "zones", label: "In-store zone attention", group: "Retail", icon: Layers, detail: "Which zones pull eyes and feet once inside" },
  { id: "staffing", label: "Staffing alignment", group: "Ops", icon: Users, detail: "Peak-hour demand vs. people on the floor" },
  { id: "campaign", label: "Physical A/B verdicts", group: "Marketing", icon: Megaphone, detail: "Keep-or-kill with a measured uplift number" },
  { id: "consumer", label: "Consumer behaviour profile", group: "Data", icon: BarChart3, detail: "Patterns of stop, enter and engage across the day" },
  { id: "anomaly", label: "Anomaly alerts", group: "Ops", icon: Activity, detail: "The day your storefront stops working — flagged live" },
  { id: "forecast", label: "4-week forecast", group: "Data", icon: TrendingUp, detail: "Traffic outlook from your own recent history" },
  { id: "brief", label: "Weekly action brief", group: "Marketing", icon: FileText, detail: "Three measured actions every Monday morning" },
]

const PRIO_LEVELS = [
  { id: "noise", label: "NOISE", title: "Not needed" },
  { id: "nice", label: "NICE", title: "Nice to have" },
  { id: "must", label: "MUST", title: "Must have" },
] as const

type Prio = "noise" | "nice" | "must"

const COMMITMENTS = [
  { id: "lean", title: "A single flagship", line: "One store, fully instrumented. The fastest proof we can earn.", note: "1 store · days not weeks" },
  { id: "core", title: "Flagship + regional", line: "Two to three stores. Enough signal to see patterns, not just moments.", note: "2–3 stores · full cohort" },
  { id: "chain", title: "Chain rollout", line: "A first wave across the network, staged store by store.", note: "5+ stores · staged" },
] as const

const STEPS = [
  { id: "pain", n: "01", label: "The Pain" },
  { id: "scope", n: "02", label: "The Scope" },
  { id: "seat", n: "03", label: "The Seat" },
]

/* ============================================================ */
/*  SHARED STATE                                                 */
/* ============================================================ */

export type DiscoveryAnswers = {
  pain: string | null
  tracking: string | null
  cameras: string | null
  priorities: Record<string, Prio>
  commitment: "lean" | "core" | "chain" | null
  format: string | null
  footfall: number | null
  success: string | null
}

const EMPTY_ANSWERS: DiscoveryAnswers = {
  pain: null,
  tracking: null,
  cameras: null,
  priorities: {},
  commitment: null,
  format: null,
  footfall: null,
  success: null,
}

type Setter = <K extends keyof DiscoveryAnswers>(key: K, value: DiscoveryAnswers[K]) => void

/* ============================================================ */
/*  SECTION SHELL                                                */
/* ============================================================ */

function SectionShell({
  id,
  kicker,
  title,
  sub,
  children,
}: {
  id?: string
  kicker: string
  title: ReactNode
  sub?: ReactNode
  children: ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-24 border-t border-white/8 cosmic-bg py-12 sm:py-16 lg:py-20">
      <div className="mx-auto max-w-[1200px] px-6 relative z-10">
        <Reveal>
          <span className="inline-flex items-center gap-2 cosmic-text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--cosmic-violet)" }}>
            <span className="h-px w-6" style={{ background: "rgba(139, 124, 246, 0.5)" }} aria-hidden />
            {kicker}
          </span>
          <h2 className="mt-3 font-serif cosmic-text-3xl sm:cosmic-text-4xl font-semibold leading-[1.1] tracking-[-0.02em] cosmic-text">
            {title}
          </h2>
          {sub && <p className="mt-3 max-w-2xl cosmic-text-base leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>{sub}</p>}
        </Reveal>
        <div className="mt-8">{children}</div>
      </div>
    </section>
  )
}

function PhaseHeader({
  index,
  kicker,
  title,
  sub,
}: {
  index: string
  kicker: string
  title: ReactNode
  sub: string
}) {
  return (
    <Reveal>
      <div className="flex items-center gap-3">
        <span className="grid h-8 w-8 place-items-center rounded-full cosmic-border cosmic-gradient-violet/10 font-mono cosmic-text-xs font-semibold" style={{ color: "var(--cosmic-violet)" }}>
          {index}
        </span>
        <span className="cosmic-text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--cosmic-violet)" }}>{kicker}</span>
      </div>
      <h2 className="mt-3 font-serif cosmic-text-2xl sm:cosmic-text-3xl font-semibold leading-[1.15] tracking-[-0.02em] cosmic-text">
        {title}
      </h2>
      <p className="mt-3 max-w-2xl cosmic-text-base leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>{sub}</p>
    </Reveal>
  )
}

/* ============================================================ */
/*  DISCOVERY PAGE                                               */
/* ============================================================ */

export function DiscoveryPage() {
  const [answers, setAnswers] = useState(EMPTY_ANSWERS)
  const [active, setActive] = useState("pain")
  const set: Setter = (key, value) => setAnswers((a) => ({ ...a, [key]: value }))

  const fmt = (n: number) => n.toLocaleString("en-IN")

  const reads =
    answers.footfall && answers.footfall > 0
      ? {
          passers: Math.round(answers.footfall / 7),
          stops: Math.round((answers.footfall / 7) * 0.075),
          enters: Math.round((answers.footfall / 7) * 0.075 * 0.21),
          leak: Math.round(answers.footfall * 0.01 * 0.21),
        }
      : null

  useEffect(() => {
    const ids = STEPS.map((s) => s.id)
    const fn = () => {
      const probe = window.scrollY + 300
      let cur = ""
      for (const id of ids) {
        const el = document.getElementById(id)
        if (el && el.offsetTop <= probe) cur = id
      }
      setActive(cur)
    }
    fn()
    window.addEventListener("scroll", fn, { passive: true })
    return () => window.removeEventListener("scroll", fn)
  }, [])

  return (
    <div className="site-scope page-in cosmic-bg text-[#f5f5f7]">
      <Nav onPilot={() => scrollToId("seat")} />

      <main className="overflow-x-hidden">
        {/* ---------- HERO / THE OFFER ---------- */}
        <section id="question" className="relative overflow-hidden scroll-mt-16 cosmic-bg pb-10 pt-24 sm:pt-28 lg:pt-32">
          <div aria-hidden className="pointer-events-none absolute inset-0" style={{
            background: "var(--cosmic-gradient-glow-strong)",
          }} />

          <div className="relative mx-auto max-w-[1200px] px-6">
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full cosmic-border cosmic-gradient-violet/10 px-4 py-2 cosmic-text-sm font-medium" style={{ color: "var(--cosmic-text-dim)" }}
            >
              <ArrowLeft size={14} strokeWidth={2.4} />
              Back to the site
            </Link>

            <div className="grid items-center gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:gap-12 w-full max-w-full">
<motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: EASE }} className="w-full max-w-full overflow-hidden">
                <p className="mt-6 inline-flex items-center gap-2 cosmic-text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--cosmic-violet)" }}>
                  <BadgeCheck size={14} strokeWidth={2} />
                  Pilot program · 10 founding seats · {BRAND.city}
                </p>

                <h1 className="mt-5 max-w-3xl font-serif cosmic-text-4xl sm:cosmic-text-5xl font-semibold leading-[1.08] tracking-[-0.02em] cosmic-text">
                  Your website has analytics.{" "}
                  Your storefront is <em className="em-accent">flying blind.</em>
                </h1>

                <p className="mt-5 max-w-xl cosmic-text-lg leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>
                  Google Analytics tells you who visited and who bought on your site. Nothing tells you that for the
                  street in front of your store — who passed, who paused at the glass, who stepped in. AD Labs reads
                  your pavement from the cameras you already own and hands you a Monday verdict. No faces. No cloud video.
                </p>

                <div className="mt-7 flex flex-wrap items-center gap-3">
                  <a
                    href="#pain"
                    className="inline-flex items-center gap-2 rounded-full cosmic-gradient-violet px-7 py-3.5 cosmic-text-base font-semibold" style={{ color: "var(--cosmic-void)" }}
                    onClick={(e) => { e.preventDefault(); scrollToId("pain") }}
                  >
                    Scope your pilot
                    <ArrowRight size={16} strokeWidth={2.4} />
                  </a>
                  <Link
                    href="/dashboard"
                    className="inline-flex items-center gap-2 rounded-full cosmic-border cosmic-gradient-violet/10 px-7 py-3.5 cosmic-text-base font-medium" style={{ color: "var(--cosmic-text)" }}
                  >
                    See the live demo
                  </Link>
                </div>

                <p className="mt-4 cosmic-text-xs" style={{ color: "var(--cosmic-text-muted)" }}>
                  Five minutes, no sales call. Your answers shape what we build.
                </p>
              </motion.div>

              {/* The instrument, live on a storefront */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.1, ease: EASE }}
                className="relative w-full max-w-full overflow-hidden"
              >
                <div className="overflow-hidden rounded-3xl cosmic-border-strong shadow-[0_40px_90px_rgba(0,0,0,0.5)]">
                  <div className="relative">
                    <img
                      src="/images/hero-storefront.jpg"
                      alt="A storefront as the Edge Observer sees it"
                      className="img-grade aspect-[4/3] w-full object-cover"
                    />
                    <div aria-hidden className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30" />

                    <span className="absolute left-4 top-4 inline-flex items-center gap-2 rounded-full cosmic-border-strong cosmic-gradient-violet/10 px-3 py-1.5 font-mono cosmic-text-2xs tracking-[0.14em] backdrop-blur-sm" style={{ color: "rgba(255,255,255,0.9)" }}>
                      <span className="relative flex h-1.5 w-1.5">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full" style={{ background: "var(--cosmic-violet)", opacity: 0.7 }} />
                        <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ background: "var(--cosmic-violet)" }} />
                      </span>
                      CAM 03 · EDGE OBSERVER · LIVE
                    </span>
                    <span className="absolute right-4 top-4 rounded-full cosmic-border cosmic-gradient-violet/10 px-3 py-1.5 font-mono cosmic-text-2xs tracking-[0.14em] backdrop-blur-sm" style={{ color: "var(--cosmic-violet)" }}>
                      GAZE 94% · DEEP 39%
                    </span>

                    <div className="absolute inset-x-0 bottom-0 grid grid-cols-3 gap-px" style={{ background: "rgba(255,255,255,0.12)" }}>
                      <div className="px-4 py-2.5 backdrop-blur-sm" style={{ background: "rgba(0,0,0,0.55)" }}>
                        <p className="font-mono cosmic-text-2xs tracking-[0.14em]" style={{ color: "var(--cosmic-text-muted)" }}>PASS</p>
                        <p className="mt-0.5 cosmic-text-xl font-semibold cosmic-text">2,481</p>
                        <p className="font-mono cosmic-text-2xs tracking-[0.08em]" style={{ color: "var(--cosmic-text-muted)" }}>/ today</p>
                      </div>
                      <div className="px-4 py-2.5 backdrop-blur-sm" style={{ background: "rgba(0,0,0,0.55)" }}>
                        <p className="font-mono cosmic-text-2xs tracking-[0.14em]" style={{ color: "var(--cosmic-violet)" }}>STOP</p>
                        <p className="mt-0.5 cosmic-text-xl font-semibold cosmic-text">7.5% <span className="cosmic-text-sm font-medium" style={{ color: "var(--cosmic-text-dim)" }}>· 186</span></p>
                        <p className="font-mono cosmic-text-2xs tracking-[0.08em]" style={{ color: "var(--cosmic-text-muted)" }}>paused ≥ 4s</p>
                      </div>
                      <div className="px-4 py-2.5 backdrop-blur-sm" style={{ background: "rgba(0,0,0,0.55)" }}>
                        <p className="font-mono cosmic-text-2xs tracking-[0.14em]" style={{ color: "var(--cosmic-violet)" }}>ENTER</p>
                        <p className="mt-0.5 cosmic-text-xl font-semibold cosmic-text">21% <span className="cosmic-text-sm font-medium" style={{ color: "var(--cosmic-text-dim)" }}>· 39</span></p>
                        <p className="font-mono cosmic-text-2xs tracking-[0.08em]" style={{ color: "var(--cosmic-text-muted)" }}>crossed threshold</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4">
                  <EventStream rows={4} />
                </div>

                <div className="absolute -left-3 -top-3 rounded-full cosmic-gradient-violet px-3.5 py-1.5 font-mono cosmic-text-2xs font-bold tracking-[0.14em]" style={{ color: "var(--cosmic-void)" }}>
                  ONE SENSOR · 12W · POE
                </div>
              </motion.div>
            </div>

            {/* Stat strip */}
            <div className="mt-14 grid grid-cols-2 gap-px overflow-hidden rounded-2xl cosmic-border" style={{ background: "rgba(255,255,255,0.1)" }}>
              {STAT_STRIP.map((s) => (
                <div key={s.label} className="bg-[#05050a] px-6 py-5">
                  <p className="cosmic-text-2xl font-bold leading-none text-[#f5f5f7]">{s.value}</p>
                  <p className="mt-2 cosmic-text-xs leading-tight text-[#86868b]">{s.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---------- PURPOSE — why this exists ---------- */}
        <section className="scroll-mt-24 border-t border-white/8 bg-[#0c0c0f] py-14 sm:py-16">
          <div className="mx-auto max-w-[1200px] px-6">
            <div className="grid lg:grid-cols-[1fr_1.4fr] lg:gap-12">
              <div>
                <p className="cosmic-text-xs font-semibold uppercase tracking-[0.16em] text-[#8B7CF6]">The purpose</p>
                <h2 className="mt-3 cosmic-text-3xl font-bold leading-[1.08] tracking-[-0.025em] text-[#f5f5f7] sm:cosmic-text-3xl">
                  Built to answer the question{" "}
                  <em className="em-accent">every brand owner can&apos;t get answered.</em>
                </h2>
                <p className="mt-4 max-w-md cosmic-text-base leading-relaxed text-[#a1a1aa]">
                  Your storefront is the most expensive ad you will ever buy — rent, glass, light and staff pay for
                  it every day. E-commerce knows exactly what that spend earns. The street never told you. This pilot
                  exists to close that gap, on your cameras, from day one.
                </p>
              </div>
              <div className="mt-8 grid gap-3 sm:grid-cols-3 lg:mt-0">
                {[
                  { icon: Eye, t: "See the full journey", d: "Pass → stop → enter → engage. The decision starts at the glass, and now you can see it." },
                  { icon: Target, t: "Decide with evidence", d: "Every window change becomes a measured physical A/B. No more Monday-morning opinions." },
                  { icon: ShieldCheck, t: "Protect while you measure", d: "Zero faces, zero cloud video. Intelligence you can stand behind, to regulators and customers." },
                ].map((c) => {
                  const Icon = c.icon
                  return (
                    <div key={c.t} className="rounded-2xl border border-white/8 bg-[#12121a] p-5">
                      <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#8B7CF6]/12 text-[#8B7CF6]">
                        <Icon size={17} strokeWidth={2} />
                      </span>
                      <h3 className="mt-3 cosmic-text-sm font-semibold leading-snug text-[#f5f5f7]">{c.t}</h3>
                      <p className="mt-1.5 cosmic-text-xs leading-relaxed text-[#86868b]">{c.d}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </section>

        {/* ---------- WHAT SHIPS ---------- */}
        <SectionShell
          kicker="What the pilot ships"
          title={<>One box, three outputs. <em className="em-accent">Nothing fluffy.</em></>}
          sub="Every founding pilot puts one physical instrument in your store and three outputs in your hands — the live dashboard, the Monday Brief and the A/B engine. On the cameras you already own, from day one."
        >
          <div className="grid gap-5 md:grid-cols-2">
            {DELIVERABLES.map((d, i) => {
              const Icon = d.icon
              return (
                <Reveal key={d.kicker} delay={i * 0.08}>
                  <article className="site-card site-card-glare group flex h-full flex-col overflow-hidden">
                    {d.visual === "edge" && (
                      <div className="overflow-hidden border-b border-white/10 bg-[#0d0d11] relative">
                        <img
                          src="/images/in-store-zones.jpg"
                          alt="Live store zones as the Edge Observer reads them"
                          className="img-grade aspect-[16/7] w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                        />
                        <div className="absolute left-4 bottom-4 rounded-full bg-black/60 px-3 py-1 font-mono cosmic-text-2xs tracking-[0.14em] text-white/90 backdrop-blur-sm">
                          LIVE STORE ZONES
                        </div>
                      </div>
                    )}
                    {d.visual === "hud" && (
                      <div className="grid grid-cols-2 gap-px border-b border-white/10 bg-white/10">
                        {[
                          ["2,481", "STREET FOOTFALL"],
                          ["7.5%", "STOP RATE"],
                          ["39", "WALK-INS"],
                          ["6m 12s", "IN-STORE DWELL"],
                        ].map(([v, l]) => (
                          <div key={l} className="bg-[#0c0c14] px-4 py-3">
                            <p className="cosmic-text-base font-semibold text-[#f5f5f7]">{v}</p>
                            <p className="mt-0.5 font-mono cosmic-text-2xs tracking-[0.12em] text-[#86868b]">{l}</p>
                          </div>
                        ))}
                      </div>
                    )}
                    {d.visual === "brief" && (
                      <div className="border-b border-white/10 bg-[#0c0c14] px-5 py-4">
                        <div className="flex items-center justify-between font-mono cosmic-text-2xs tracking-[0.14em] text-[#86868b]">
                          <span>MONDAY BRIEF · WEEK 4</span>
                          <span>07:28 · 15 MIN</span>
                        </div>
                        <ul className="mt-3 space-y-2">
                          {[
                            ["01", "Staff up 2 for the 15–17 attention peak"],
                            ["02", "Rotate Window West creative — recover 2pp dwell"],
                            ["03", "Test the hero bag in the sightline — target +5% touch"],
                          ].map(([n, t]) => (
                            <li key={n} className="flex gap-2 cosmic-text-xs leading-snug text-[#c4c4cc]">
                              <span className="font-mono text-[#8B7CF6]">{n}</span>
                              {t}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {d.visual === "ab" && (
                      <div className="relative grid grid-cols-2 overflow-hidden border-b border-white/10 bg-[#0d0d11]">
                        <div className="relative">
                          <img src="/images/window-before.jpg" alt="Window treatment A" className="aspect-[4/5] w-full object-cover" />
                          <div className="absolute left-3 top-3 rounded-full bg-black/60 px-2 py-1 font-mono cosmic-text-2xs tracking-[0.1em] text-white/90 backdrop-blur-sm">A</div>
                        </div>
                        <div className="relative">
                          <img src="/images/window-after.jpg" alt="Window treatment B" className="aspect-[4/5] w-full object-cover" />
                          <div className="absolute left-3 top-3 rounded-full bg-black/60 px-2 py-1 font-mono cosmic-text-2xs tracking-[0.1em] text-white/90 backdrop-blur-sm">B</div>
                        </div>
                        <div aria-hidden className="absolute inset-x-0 bottom-0 flex justify-center pb-3">
                          <span className="rounded-full bg-[#8B7CF6] px-3 py-1 font-mono cosmic-text-2xs font-bold tracking-[0.1em] text-[#05050a] shadow-[0_8px_24px_rgba(139,124,246,0.35)]">
                            +14.6% · 14D VERDICT
                          </span>
                        </div>
                      </div>
                    )}

                    <div className="flex h-full flex-col p-6">
                      <div className="flex items-start justify-between">
                        <span className="grid h-11 w-11 place-items-center rounded-xl bg-[#8B7CF6]/10 text-[#8B7CF6] transition-all duration-300 group-hover:scale-110 group-hover:bg-[#8B7CF6] group-hover:text-[#05050a]">
                          <Icon size={19} strokeWidth={1.9} />
                        </span>
                        <span className="font-mono cosmic-text-2xs tracking-[0.14em] text-[#86868b]">{d.kicker.split("·")[1].trim()}</span>
                      </div>
                      <h3 className="mt-4 cosmic-text-base font-semibold leading-snug text-[#f5f5f7]">{d.title}</h3>
                      <p className="mt-2 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{d.body}</p>
                      <ul className="mt-4 flex flex-col gap-2 border-t border-white/8 pt-4">
                        {d.points.map((pt) => (
                          <li key={pt} className="flex items-start gap-2 cosmic-text-xs leading-snug text-[#c4c4cc]">
                            <Check size={13} strokeWidth={2.5} className="mt-0.5 shrink-0 text-[#8B7CF6]" />
                            {pt}
                          </li>
                        ))}
                      </ul>
                      <p className="mt-auto pt-4 font-mono cosmic-text-2xs tracking-[0.12em] text-[#86868b]">{d.spec}</p>
                    </div>
                  </article>
                </Reveal>
              )
            })}
          </div>
        </SectionShell>

        {/* ---------- HOW IT RUNS ---------- */}
        <SectionShell
          kicker="How it runs"
          title={<>Two weeks from carton <em className="em-accent">to verdict.</em></>}
          sub="A founding pilot runs on a fixed rhythm. Here is exactly what each stage means and when it lands."
        >
          <div className="relative grid gap-5 lg:grid-cols-4">
            <div aria-hidden className="absolute left-6 top-0 hidden h-full w-px bg-gradient-to-b from-[#8B7CF6]/50 via-white/10 to-transparent lg:left-1/2 lg:block" />
            {TIMELINE.map((t, i) => {
              const Icon = t.icon
              return (
                <Reveal key={t.day} delay={i * 0.1}>
                  <article className="relative flex h-full flex-col rounded-2xl border border-white/10 bg-[#12121a] p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[#8B7CF6]/40">
                    <div className="flex items-center justify-between">
                      <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#8B7CF6]/10 text-[#8B7CF6]">
                        <Icon size={18} strokeWidth={1.9} />
                      </span>
                      <span className="font-mono cosmic-text-xs font-semibold tracking-[0.14em] text-[#8B7CF6]">{t.day}</span>
                    </div>
                    <h3 className="mt-4 cosmic-text-base font-semibold text-[#f5f5f7]">{t.title}</h3>
                    <p className="mt-1 cosmic-text-xs font-medium text-[#8B7CF6]">{t.duration}</p>
                    <p className="mt-3 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{t.body}</p>
                  </article>
                </Reveal>
              )
            })}
          </div>
          <Reveal delay={0.2}>
            <p className="mt-6 flex items-center gap-2 rounded-2xl border border-white/10 bg-[#12121a]/70 px-5 py-4 cosmic-text-sm leading-relaxed text-[#a1a1aa]">
              <Activity size={16} strokeWidth={2} className="shrink-0 text-[#8B7CF6]" />
              Beyond the rhythm: anomaly alerts and the 4-week forecast switch on automatically as your pilot accumulates history.
            </p>
          </Reveal>
        </SectionShell>

        {/* ---------- PRIVACY ---------- */}
        <section className="border-t border-white/8 bg-[#05050a] py-10 lg:py-12">
          <div className="mx-auto max-w-[1200px] px-6">
            <Reveal>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 cosmic-text-xs font-semibold uppercase tracking-[0.12em] text-[#8B7CF6]">
                  <span className="h-px w-6 bg-[#8B7CF6]/50" aria-hidden />
                  Count it. Never watch it.
                </span>
                <p className="cosmic-text-sm text-[#86868b]">
                  Guarantees by architecture — how the hardware is built, not a policy on paper.
                </p>
              </div>
            </Reveal>
            <div className="mt-6 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
              {GUARANTEES.map((g) => {
                const Icon = g.icon
                return (
                  <div key={g.title} className="flex items-start gap-3 bg-[#12121a] px-5 py-4">
                    <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#8B7CF6]/10 text-[#8B7CF6]">
                      <Icon size={15} strokeWidth={2} />
                    </span>
                    <div className="min-w-0">
                      <p className="cosmic-text-sm font-semibold text-[#f5f5f7]">{g.title}</p>
                      <p className="mt-0.5 cosmic-text-xs leading-snug text-[#86868b]">{g.body}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* ---------- STEP RAIL ---------- */}
        <div className="sticky top-14 z-30 border-y border-white/10 bg-[#05050a]/95 shadow-[0_12px_32px_rgba(0,0,0,0.35)] backdrop-blur-xl">
          <div className="mx-auto flex max-w-[1200px] items-center justify-center gap-1 px-4 py-2.5">
            {STEPS.map((s) => {
              const on = active === s.id
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => scrollToId(s.id)}
                  className={`flex items-center gap-2 rounded-full px-4 py-1.5 cosmic-text-xs font-medium transition-all duration-200 ${
                    on ? "bg-[#8B7CF6] text-[#05050a]" : "text-[#a1a1aa] hover:text-[#f5f5f7]"
                  }`}
                >
                  <span className={`font-mono ${on ? "text-[#05050a]" : "text-[#8B7CF6]"}`}>{s.n}</span>
                  {s.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* ---------- THE PAIN ---------- */}
        <section id="pain" className="scroll-mt-32 bg-[#05050a] py-12 sm:py-16 lg:py-20">
          <div className="mx-auto max-w-[1200px] px-6">
            <PhaseHeader
              index="01"
              kicker="The pain"
              title={<>Which leak stings most?<br /><em className="em-accent">Pick the one we validate first.</em></>}
              sub="Two reads on this step: where the leak stings most, and what you're flying on today. That pair sets what we instrument first."
            />
            <Reveal>
              <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {PAIN_POINTS.map((p) => {
                  const Icon = p.icon
                  const selected = answers.pain === p.id
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => set("pain", p.id)}
                      aria-pressed={selected}
                      className={`group relative flex flex-col overflow-hidden rounded-3xl border p-6 text-left transition-all duration-300 ${
                        selected
                          ? "border-[#8B7CF6] bg-[#8B7CF6]/12 shadow-[0_0_60px_rgba(139,124,246,0.18)]"
                          : "border-white/10 bg-[#12121a] hover:-translate-y-1 hover:border-[#8B7CF6]/40"
                      }`}
                    >
                      <span className="font-mono cosmic-text-2xs tracking-[0.16em] text-[#8B7CF6]/80">{p.tag}</span>
                      <span className={`mt-4 grid h-11 w-11 place-items-center rounded-xl transition-colors ${selected ? "bg-[#8B7CF6] text-[#05050a]" : "bg-white/5 text-[#8B7CF6]"}`}>
                        <Icon size={19} strokeWidth={1.9} />
                      </span>
                      <h3 className="mt-4 cosmic-text-base font-semibold leading-snug text-[#f5f5f7]">{p.label}</h3>
                      <p className="mt-1.5 flex-1 cosmic-text-xs leading-relaxed text-[#a1a1aa]">{p.sub}</p>
                      <span className={`mt-4 inline-flex h-5 w-5 items-center justify-center rounded-full border cosmic-text-2xs font-bold transition-colors ${
                        selected ? "border-[#8B7CF6] bg-[#8B7CF6] text-[#05050a]" : "border-white/15 text-[#a1a1aa] group-hover:border-[#8B7CF6]/50"
                      }`}>
                        {selected ? <Check size={11} strokeWidth={3} /> : ""}
                      </span>
                    </button>
                  )
                })}
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="mt-10 border-t border-white/8 pt-8">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="cosmic-text-sm font-medium text-[#f5f5f7]">What are you flying on today?</p>
                  <span className="font-mono cosmic-text-2xs tracking-[0.14em] text-[#86868b]">TRACKING BASELINE</span>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                  {TRACKING_OPTIONS.map((t) => {
                    const Icon = t.icon
                    const selected = answers.tracking === t.id
                    return (
                      <button
                        key={t.id}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => set("tracking", t.id)}
                        className={`group flex items-center gap-2.5 rounded-2xl border px-4 py-3 text-left transition-all duration-200 ${
                          selected
                            ? "border-[#8B7CF6] bg-[#8B7CF6]/10"
                            : "border-white/10 bg-[#12121a] hover:-translate-y-0.5 hover:border-[#8B7CF6]/40"
                        }`}
                      >
                        <span
                          className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg transition-colors ${
                            selected ? "bg-[#8B7CF6] text-[#05050a]" : "bg-white/5 text-[#8B7CF6]"
                          }`}
                        >
                          <Icon size={15} strokeWidth={2} />
                        </span>
                        <span className="cosmic-text-xs font-medium leading-tight text-[#f5f5f7]">{t.label}</span>
                      </button>
                    )
                  })}
                </div>
                <AnimatePresence>
                  {answers.tracking && (
                    <motion.p
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="mt-4 rounded-xl border border-white/8 bg-[#12121a]/70 px-4 py-3 cosmic-text-xs leading-relaxed text-[#a1a1aa]"
                    >
                      <span className="font-semibold text-[#8B7CF6]">{TRACKING_OPTIONS.find((t) => t.id === answers.tracking)?.label}.</span>{" "}
                      {TRACKING_OPTIONS.find((t) => t.id === answers.tracking)?.note}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>
            </Reveal>

            <Reveal delay={0.15}>
              <div className="mt-8 border-t border-white/8 pt-8">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="cosmic-text-sm font-medium text-[#f5f5f7]">Do your cameras expose an IP feed?</p>
                  <span className="rounded-full border border-[#8B7CF6]/30 bg-[#8B7CF6]/10 px-3 py-0.5 font-mono cosmic-text-2xs tracking-[0.14em] text-[#8B7CF6]">
                    THE CAMERA GATE
                  </span>
                </div>
                <p className="mt-1 max-w-2xl cosmic-text-xs leading-relaxed text-[#86868b]">
                  The one feasibility question. We read your store from the cameras already on the wall — no new hardware,
                  no network change.
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  {CAMERA_STACK.map((c) => {
                    const selected = answers.cameras === c.id
                    return (
                      <button
                        key={c.id}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => set("cameras", c.id)}
                        className={`group rounded-2xl border px-4 py-3 text-left transition-all duration-200 ${
                          selected
                            ? "border-[#8B7CF6] bg-[#8B7CF6]/10"
                            : "border-white/10 bg-[#12121a] hover:-translate-y-0.5 hover:border-[#8B7CF6]/40"
                        }`}
                      >
                        <span className="flex items-center gap-2 cosmic-text-sm font-medium text-[#f5f5f7]">
                          <span
                            className={`grid h-4.5 w-4.5 shrink-0 place-items-center rounded-full border transition-colors ${
                              selected ? "border-[#8B7CF6] bg-[#8B7CF6]" : "border-white/20"
                            }`}
                          >
                            {selected && <Check size={10} strokeWidth={3.2} className="text-[#05050a]" />}
                          </span>
                          {c.label}
                        </span>
                        <span className="mt-1.5 block pl-6 cosmic-text-xs leading-snug text-[#86868b]">{c.hint}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </Reveal>

            <AnimatePresence>
              {answers.pain && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mt-6 flex flex-col items-start justify-between gap-4 rounded-2xl border border-[#8B7CF6]/30 bg-[#8B7CF6]/8 p-6 sm:flex-row sm:items-center"
                >
                  <p className="cosmic-text-base text-[#f5f5f7]/80">
                    Noted. <span className="font-semibold text-[#f5f5f7]">{PRIORITIES[answers.pain]}</span> is your top problem —{" "}
                    <span className="text-[#86868b]">this is the leak we instrument first.</span>
                  </p>
                  <button
                    type="button"
                    onClick={() => scrollToId("scope")}
                    className="inline-flex shrink-0 items-center gap-2 rounded-full bg-[#8B7CF6] px-7 py-3.5 cosmic-text-sm font-semibold text-[#05050a] transition-all duration-200 hover:bg-[#6E5CE6] hover:-translate-y-0.5 active:scale-[0.98]"
                  >
                    Next — set the scope <ArrowRight size={16} strokeWidth={2.4} />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </section>

        {/* ---------- THE SCOPE ---------- */}
        <section id="scope" className="scroll-mt-32 border-t border-white/8 bg-[#0c0c14] py-12 sm:py-16 lg:py-20">
          <div className="mx-auto max-w-[1200px] px-6">
            <PhaseHeader
              index="02"
              kicker="The scope"
              title={<>Mark what matters. <em className="em-accent">We build in that order.</em></>}
              sub="Each capability ships with its own verdict engine. Mark must / nice / noise, then tell us the shape of your roll-out — your priorities set the launch build order."
            />
            <Reveal>
              <div className="mt-8 overflow-hidden rounded-2xl border border-white/10">
                {FEATURES.map((f, fi) => {
                  const p: Prio | null = answers.priorities[f.id] ?? null
                  const FeatureIcon = f.icon
                  return (
                    <div
                      key={f.id}
                      className={`flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-[#12121a] sm:flex-row sm:items-center sm:justify-between ${fi % 2 ? "bg-[#12121a]" : "bg-[#12121a]"} ${fi !== 0 ? "border-t border-white/8" : ""}`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/10 bg-[#1a1a24] text-[#8B7CF6]">
                          <FeatureIcon size={15} strokeWidth={2} />
                        </span>
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="cosmic-text-base font-medium text-[#f5f5f7]">{f.label}</p>
                            <span className="rounded-full border border-white/12 bg-white/4 px-2.5 py-0.5 font-mono cosmic-text-2xs tracking-[0.12em] text-[#8B7CF6]">
                              {f.group.toUpperCase()}
                            </span>
                          </div>
                          <p className="mt-0.5 hidden cosmic-text-xs text-[#86868b] sm:block">{f.detail}</p>
                        </div>
                      </div>
                      <div className="flex gap-1.5">
                        {PRIO_LEVELS.map((lv) => {
                          const on = p === lv.id
                          return (
                            <button
                              key={lv.id}
                              type="button"
                              aria-pressed={on}
                              onClick={() => set("priorities", { ...answers.priorities, [f.id]: lv.id as Prio })}
                              className={`rounded-lg border px-3 py-1.5 cosmic-text-xs font-semibold transition-all duration-200 ${
                                on
                                  ? lv.id === "must"
                                    ? "border-[#8B7CF6] bg-[#8B7CF6] text-[#05050a]"
                                    : lv.id === "nice"
                                      ? "border-[#8B7CF6] bg-[#8B7CF6] text-[#05050a]"
                                      : "border-white/20 bg-white/5 text-[#a1a1aa]"
                                  : "border-white/12 bg-[#1a1a24] text-[#86868b] hover:border-white/25 hover:text-[#f5f5f7]"
                              }`}
                            >
                              {lv.label}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            </Reveal>

            <Reveal delay={0.05}>
              <div className="mt-8 rounded-2xl border border-white/10 bg-[#12121a] p-6 sm:p-8">
                <div className="flex items-center justify-between gap-4">
                  <p className="cosmic-text-base font-semibold text-[#f5f5f7]">The store profile</p>
                  <span className="rounded-full bg-[#8B7CF6]/10 px-3 py-1 font-mono cosmic-text-2xs tracking-[0.12em] text-[#8B7CF6]">
                    THE STORE PROFILE
                  </span>
                </div>
                <p className="mt-1 cosmic-text-xs text-[#86868b]">
                  Two numbers that shape the build — the format we provision for, and the street you serve.
                </p>

                <div className="mt-5">
                  <p className="mb-2 cosmic-text-sm font-medium text-[#f5f5f7]">Store format</p>
                  <div className="flex flex-wrap gap-2">
                    {STORE_FORMATS.map((f) => {
                      const selected = answers.format === f.id
                      return (
                        <button
                          key={f.id}
                          type="button"
                          aria-pressed={selected}
                          onClick={() => set("format", f.id)}
                          className={`rounded-full border px-4 py-2 cosmic-text-xs font-medium transition-all duration-200 ${
                            selected
                              ? "border-[#8B7CF6] bg-[#8B7CF6] text-[#05050a]"
                              : "border-white/12 bg-[#1a1a24] text-[#c4c4cc] hover:border-[#8B7CF6]/40 hover:text-[#f5f5f7]"
                          }`}
                        >
                          {f.label}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div className="mt-6 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
                  <div>
                    <label htmlFor="d-footfall" className="mb-1.5 block cosmic-text-sm font-medium text-[#f5f5f7]">
                      Estimated weekly footfall
                    </label>
                    <div className="relative">
                      <input
                        id="d-footfall"
                        type="text"
                        inputMode="numeric"
                        autoComplete="off"
                        value={answers.footfall ?? ""}
                        onChange={(e) => {
                          const raw = e.target.value.replace(/[^\d]/g, "")
                          set("footfall", raw ? Math.min(1_000_000, Number(raw)) : null)
                        }}
                        placeholder="17,000"
                        className="w-full rounded-xl border border-white/12 bg-[#1a1a24]/80 py-3 pl-4 pr-28 cosmic-text-base text-[#f5f5f7] outline-none transition-colors duration-200 placeholder:text-[#86868b] focus:border-[#8B7CF6]"
                      />
                      <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 font-mono cosmic-text-2xs tracking-[0.12em] text-[#86868b]">
                        PEOPLE / WEEK
                      </span>
                    </div>
                    <p className="mt-1.5 cosmic-text-xs text-[#86868b]">Rough is fine. This is the base for the read below.</p>
                  </div>

                  <div className="rounded-2xl border border-[#8B7CF6]/20 bg-[#8B7CF6]/5 p-4 sm:p-5">
                    <p className="flex items-center gap-2 cosmic-text-xs font-semibold uppercase tracking-[0.12em] text-[#8B7CF6]">
                      <TrendingUp size={13} strokeWidth={2.2} />
                      The street, read instantly
                    </p>
                    {reads ? (
                      <div className="mt-3 space-y-2">
                        <div className="flex items-baseline justify-between gap-3 rounded-lg bg-[#12121a]/80 px-3 py-2">
                          <span className="font-mono cosmic-text-base font-semibold text-[#f5f5f7]">≈ {fmt(reads.passers)}</span>
                          <span className="cosmic-text-xs text-[#86868b]">passers-by / day</span>
                        </div>
                        <div className="flex items-baseline justify-between gap-3 rounded-lg bg-[#12121a]/80 px-3 py-2">
                          <span className="font-mono cosmic-text-base font-semibold text-[#f5f5f7]">≈ {fmt(reads.stops)}</span>
                          <span className="cosmic-text-xs text-[#86868b]">pause at the glass · 7.5% stop</span>
                        </div>
                        <div className="flex items-baseline justify-between gap-3 rounded-lg bg-[#12121a]/80 px-3 py-2">
                          <span className="font-mono cosmic-text-base font-semibold text-[#f5f5f7]">≈ {fmt(reads.enters)}</span>
                          <span className="cosmic-text-xs text-[#86868b]">cross the threshold · 21% stop→enter</span>
                        </div>
                        <p className="rounded-lg border border-[#8B7CF6]/25 bg-[#8B7CF6]/8 px-3 py-2 cosmic-text-xs leading-snug text-[#8B7CF6]">
                          +1pp stop rate → <span className="font-semibold">+≈{fmt(reads.leak)} extra visits / week</span> — the target of your first A/B.
                        </p>
                      </div>
                    ) : (
                      <p className="mt-3 rounded-lg bg-[#12121a]/80 px-3 py-4 text-center cosmic-text-xs text-[#86868b]">
                        Enter your weekly footfall to see the first read.
                      </p>
                    )}
                    <p className="mt-3 cosmic-text-2xs leading-snug text-[#6e6e76]">
                      Base rates from our public demo (7.5% stop · 21% stop-to-enter). Your real numbers land after Day 1 calibration.
                    </p>
                  </div>

                  <div className="mt-6">
                    <p className="mb-2 cosmic-text-sm font-medium text-[#f5f5f7]">The number that has to move</p>
                    <div className="flex flex-wrap gap-2">
                      {SUCCESS_METRICS.map((s) => {
                        const selected = answers.success === s.id
                        return (
                          <button
                            key={s.id}
                            type="button"
                            aria-pressed={selected}
                            onClick={() => set("success", s.id)}
                            className={`rounded-full border px-4 py-2 cosmic-text-xs font-medium transition-all duration-200 ${
                              selected
                                ? "border-[#8B7CF6] bg-[#8B7CF6] text-[#05050a]"
                                : "border-white/12 bg-[#1a1a24] text-[#c4c4cc] hover:border-[#8B7CF6]/40 hover:text-[#f5f5f7]"
                            }`}
                          >
                            {s.label}
                          </button>
                        )
                      })}
                    </div>
                    <p className="mt-1.5 cosmic-text-xs text-[#86868b]">
                      {answers.success
                        ? SUCCESS_METRICS.find((s) => s.id === answers.success)?.hint
                        : "Pick the one metric you want the Monday Brief to own."}
                    </p>
                  </div>
                </div>
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="mt-8 rounded-2xl border border-white/10 bg-[#12121a] p-6 sm:p-8">
                <div className="flex items-center justify-between gap-4">
                  <p className="cosmic-text-base font-semibold text-[#f5f5f7]">
                    The shape of your roll-out
                  </p>
                  <span className="rounded-full bg-[#8B7CF6]/10 px-3 py-1 font-mono cosmic-text-2xs tracking-[0.12em] text-[#8B7CF6]">
                    THE ROLL-OUT
                  </span>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  {COMMITMENTS.map((c) => {
                    const on = answers.commitment === c.id
                    return (
                      <button
                        key={c.id}
                        type="button"
                        aria-pressed={on}
                        onClick={() => set("commitment", c.id)}
                        className={`flex flex-col rounded-2xl border p-5 text-left transition-all duration-300 ${
                          on ? "border-[#8B7CF6] bg-[#8B7CF6]/10 shadow-[0_0_40px_rgba(139,124,246,0.14)]" : "border-white/10 bg-[#1a1a24] hover:-translate-y-0.5 hover:border-[#8B7CF6]/40"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <h4 className="cosmic-text-sm font-semibold text-[#f5f5f7]">{c.title}</h4>
                          {on && <Check size={14} strokeWidth={2.5} className="text-[#8B7CF6]" />}
                        </div>
                        <p className="mt-1 flex-1 cosmic-text-xs leading-relaxed text-[#a1a1aa]">{c.line}</p>
                        <p className="mt-3 font-mono cosmic-text-2xs tracking-[0.14em] text-[#86868b]">{c.note}</p>
                      </button>
                    )
                  })}
                </div>
                <button
                  type="button"
                  onClick={() => scrollToId("seat")}
                  className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#8B7CF6] px-7 py-3.5 cosmic-text-sm font-semibold text-[#05050a] transition-all duration-200 hover:bg-[#6E5CE6] hover:-translate-y-0.5 active:scale-[0.98]"
                >
                  Take the seat <ArrowRight size={16} strokeWidth={2.4} />
                </button>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ---------- THE SEAT ---------- */}
        <Seat answers={answers} set={set} />
      </main>

      <Footer />
    </div>
  )
}

/* ============================================================ */
/*  03 · THE SEAT                                                */
/* ============================================================ */

function Seat({ answers, set: _set }: { answers: DiscoveryAnswers; set: Setter }) {
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)
  const [form, setForm] = useState({ name: "", brand: "", email: "", role: "", note: "" })
  const setF = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  const mustCount = Object.values(answers.priorities).filter((v) => v === "must").length

  const submit = (e: FormEvent) => {
    e.preventDefault()
    setSending(true)
    window.setTimeout(() => {
      submitViaEmail("Pilot seat — AD Labs Discovery", [
        { label: "Name", value: form.name },
        { label: "Brand", value: form.brand },
        { label: "Email", value: form.email },
        { label: "Role", value: form.role },
        { label: "Top problem", value: answers.pain ? PRIORITIES[answers.pain] : "" },
        { label: "Tracks today", value: answers.tracking ? TRACKING_OPTIONS.find((t) => t.id === answers.tracking)?.label : "" },
        { label: "Camera stack", value: answers.cameras ? CAMERA_STACK.find((c) => c.id === answers.cameras)?.label : "" },
        { label: "Must-haves", value: `${mustCount} capabilities` },
        { label: "Roll-out", value: COMMITMENTS.find((c) => c.id === answers.commitment)?.title ?? "" },
        { label: "Store profile", value: answers.format ? STORE_FORMATS.find((f) => f.id === answers.format)?.label : "" },
        { label: "Weekly footfall", value: answers.footfall ? `${answers.footfall.toLocaleString("en-IN")} people/week` : "" },
        { label: "Success metric", value: answers.success ? SUCCESS_METRICS.find((s) => s.id === answers.success)?.label : "" },
        { label: "Note", value: form.note },
      ])
      setSending(false)
      setSent(true)
    }, 700)
  }

  const inputCls =
    "w-full rounded-xl border border-white/12 bg-[#1a1a24]/80 px-4 py-3 cosmic-text-base text-[#f5f5f7] outline-none transition-colors duration-200 placeholder:text-[#86868b] focus:border-[#8B7CF6]"
  const labelCls = "mb-1.5 block cosmic-text-sm font-medium text-[#f5f5f7]"

  return (
    <section id="seat" className="scroll-mt-32 border-t border-white/8 bg-[#05050a] py-12 sm:py-16 lg:py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid items-start gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          {/* Left — summary of what they just chose */}
          <Reveal>
            <div className="flex h-full flex-col gap-5 lg:sticky lg:top-28">
              <PhaseHeader
                index="03"
                kicker="The seat"
                title={<>Claim a founding seat.</>}
                sub="We admit ten founding stores. Your answers above are already part of your application — just add the essentials to lock it in."
              />

              <div className="rounded-2xl border border-white/10 bg-[#12121a]/80 p-6">
                <p className="cosmic-text-xs font-semibold uppercase tracking-[0.14em] text-[#86868b]">Your application</p>
                <dl className="mt-4 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <dt className="cosmic-text-xs text-[#a1a1aa]">Top problem</dt>
                    <dd className="max-w-[60%] text-right cosmic-text-xs font-medium text-[#f5f5f7]">
                      {answers.pain ? PRIORITIES[answers.pain] : "—"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="cosmic-text-xs text-[#a1a1aa]">Must-haves</dt>
                    <dd className="max-w-[60%] text-right cosmic-text-xs font-medium text-[#f5f5f7]">{mustCount ? `${mustCount} of 8 capabilities` : "—"}</dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="cosmic-text-xs text-[#a1a1aa]">Roll-out</dt>
                    <dd className="max-w-[60%] text-right cosmic-text-xs font-medium text-[#f5f5f7]">
                      {COMMITMENTS.find((c) => c.id === answers.commitment)?.title ?? "—"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="cosmic-text-xs text-[#a1a1aa]">Tracks today</dt>
                    <dd className="max-w-[60%] text-right cosmic-text-xs font-medium text-[#f5f5f7]">
                      {answers.tracking ? TRACKING_OPTIONS.find((t) => t.id === answers.tracking)?.label : "—"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="cosmic-text-xs text-[#a1a1aa]">Store format</dt>
                    <dd className="max-w-[60%] text-right cosmic-text-xs font-medium text-[#f5f5f7]">
                      {answers.format ? STORE_FORMATS.find((f) => f.id === answers.format)?.label : "—"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="cosmic-text-xs text-[#a1a1aa]">Weekly footfall</dt>
                    <dd className="max-w-[60%] text-right cosmic-text-xs font-medium text-[#f5f5f7]">
                      {answers.footfall ? `${answers.footfall.toLocaleString("en-IN")} / week` : "—"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="cosmic-text-xs text-[#a1a1aa>">Camera stack</dt>
                    <dd className="max-w-[60%] text-right cosmic-text-xs font-medium text-[#f5f5f7]">
                      {answers.cameras ? CAMERA_STACK.find((c) => c.id === answers.cameras)?.label : "—"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="cosmic-text-xs text-[#a1a1aa]">Success metric</dt>
                    <dd className="max-w-[60%] text-right cosmic-text-xs font-medium text-[#f5f5f7]">
                      {answers.success ? SUCCESS_METRICS.find((s) => s.id === answers.success)?.label : "—"}
                    </dd>
                  </div>
                </dl>
                <div className="mt-5 flex flex-wrap gap-2 border-t border-white/10 pt-5">
                  <span className="inline-flex items-center gap-1.5 cosmic-text-xs text-[#86868b]"><Mail size={12} className="text-[#8B7CF6]" /> {BRAND.email}</span>
                  <span className="inline-flex items-center gap-1.5 cosmic-text-xs text-[#86868b]"><Clock size={12} className="text-[#8B7CF6]" /> replies within 24h</span>
                  <span className="inline-flex items-center gap-1.5 cosmic-text-xs text-[#86868b]"><MapPin size={12} className="text-[#8B7CF6]" /> {BRAND.city}</span>
                </div>
                <div className="mt-4 rounded-xl border border-[#8B7CF6]/20 bg-[#8B7CF6]/5 p-4">
                  <p className="flex items-center gap-2 cosmic-text-xs font-semibold uppercase tracking-[0.12em] text-[#8B7CF6]">
                    <ShieldCheck size={13} strokeWidth={2.2} />
                    What happens after you apply
                  </p>
                  <ol className="mt-2 space-y-2 cosmic-text-xs leading-relaxed text-[#c4c4cc]">
                    <li className="flex gap-2"><span className="shrink-0 font-mono text-[#8B7CF6]">01</span>Day-0 call (15 min) — camera check & scope confirm.</li>
                    <li className="flex gap-2"><span className="shrink-0 font-mono text-[#8B7CF6]">02</span>Edge Observer ships; we plug it in (2 hrs, on-site).</li>
                    <li className="flex gap-2"><span className="shrink-0 font-mono text-[#8B7CF6]">03</span>Day 1 calibration → first Monday Brief lands on Day 7.</li>
                  </ol>
                </div>
                <div className="mt-4 rounded-xl border border-[#8B7CF6]/20 bg-[#8B7CF6]/5 p-4">
                  <p className="flex items-center gap-2 cosmic-text-xs font-semibold uppercase tracking-[0.12em] text-[#8B7CF6]">
                    <AlertTriangle size={13} strokeWidth={2.2} />
                    Founding cohort status
                  </p>
                  <p className="mt-1 cosmic-text-xs leading-relaxed text-[#c4c4cc]">
                    10 seats · <span className="font-semibold text-[#f5f5f7]">0 filled</span>. No waitlist — first 10 complete applications lock in.
                  </p>
                </div>
              </div>
            </div>
          </Reveal>

          {/* Right — the form */}
          <Reveal delay={0.1}>
            <div className="rounded-2xl border border-white/10 bg-[#1a1a24]/80 p-6 sm:p-9">
              {sent ? (
                <motion.div
                  className="flex min-h-[420px] flex-col items-center justify-center text-center"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.45, ease: EASE }}
                >
                  <motion.span
                    className="grid h-14 w-14 place-items-center rounded-full bg-[#8B7CF6] text-[#05050a]"
                    initial={{ scale: 0.4, rotate: -12 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: "spring", stiffness: 260, damping: 16, delay: 0.08 }}
                  >
                    <Send size={22} strokeWidth={2.5} />
                  </motion.span>
                  <h3 className="mt-6 cosmic-text-2xl font-bold text-[#f5f5f7]">Seat requested.</h3>
                  <p className="mt-3 max-w-sm cosmic-text-base leading-relaxed text-[#a1a1aa]">
                    A human reads every application. We&apos;ll reply to {form.email || "your inbox"} within 24 hours with
                    the next step — usually a 20-minute walkthrough, nothing more.
                  </p>
                  <button
                    type="button"
                    onClick={() => { setSent(false); setForm({ name: "", brand: "", email: "", role: "", note: "" }) }}
                    className="mt-8 cosmic-text-sm font-medium text-[#8B7CF6] underline-offset-4 hover:underline"
                  >
                    Edit and resend
                  </button>
                </motion.div>
              ) : (
                <form onSubmit={submit} className="flex flex-col gap-5">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="cosmic-text-xl font-bold text-[#f5f5f7]">Request a founding seat</h3>
                    <span className="rounded-full bg-[#8B7CF6]/10 px-3 py-1 font-mono cosmic-text-2xs tracking-[0.12em] text-[#8B7CF6]">
                      {mustCount} must-haves
                    </span>
                  </div>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <div>
                      <label htmlFor="d-name" className={labelCls}>Name</label>
                      <input id="d-name" required value={form.name} onChange={setF("name")} placeholder="Ananya Rao" className={inputCls} />
                    </div>
                    <div>
                      <label htmlFor="d-brand" className={labelCls}>Brand</label>
                      <input id="d-brand" required value={form.brand} onChange={setF("brand")} placeholder="Organic Clothing Co." className={inputCls} />
                    </div>
                    <div>
                      <label htmlFor="d-email" className={labelCls}>Work email</label>
                      <input id="d-email" type="email" required value={form.email} onChange={setF("email")} placeholder="you@brand.com" className={inputCls} />
                    </div>
                    <div>
                      <label htmlFor="d-role" className={labelCls}>Role</label>
                      <input id="d-role" value={form.role} onChange={setF("role")} placeholder="Founder / Retail Head / Ops" className={inputCls} />
                    </div>
                  </div>
                  <div>
                    <label htmlFor="d-note" className={labelCls}>Anything else we should know?</label>
                    <textarea
                      id="d-note"
                      value={form.note}
                      onChange={setF("note")}
                      rows={4}
                      placeholder="A typical Tuesday, a window that's underperforming, a launch coming up…"
                      className={`${inputCls} resize-none`}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={sending}
                    className="inline-flex items-center justify-center gap-2 rounded-full bg-[#8B7CF6] px-7 py-3.5 cosmic-text-base font-semibold text-[#05050a] transition-all duration-200 hover:bg-[#6E5CE6] hover:-translate-y-0.5 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {sending ? (
                      <><Loader2 size={16} className="animate-spin" /> Sending…</>
                    ) : (
                      <>Request the seat <ArrowRight size={16} strokeWidth={2.4} /></>
                    )}
                  </button>
                  <p className="cosmic-text-xs leading-relaxed text-[#86868b]">
                    No obligation. No sales pipeline. Your answers go to {BRAND.email} and shape the founding build.
                  </p>
                </form>
              )}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
