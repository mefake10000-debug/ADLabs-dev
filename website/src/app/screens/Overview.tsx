import { useState } from "react"
import { motion } from "framer-motion"
import { CountUp } from "../../components/CountUp"
import { RevenueKpis } from "../../components/RevenueKpis"
import { BusinessKpis, OccupancyGauge } from "../Business"
import { VisitorFlow } from "../FlowChart"
import { Skeleton } from "../../components/Skeleton"
import { useMountLoader } from "../../utils/useMountLoader"
import {
  TrendingUp, Store, Megaphone, Map, FileText, BarChart3, Eye, DoorOpen, Timer,
  Footprints, Users, Clock, Clock3, Landmark, Trophy,
} from "lucide-react"
import { Panel, Label, DeltaPill, PeerDot, Segmented, Chip } from "../ui"
import { AreaChart, FunnelBars, Sparkline } from "../charts"
import {
  KPIS, FUNNEL, TRAFFIC_HOURS, TENANT,
  STORES, BRIEF, SIMULATED_NOTE, CAMPAIGNS, INSIGHTS,
  PEER_BENCHMARK, OCCUPANCY,
} from "../../data/dashboard"

const AFT_CAMPAIGN = CAMPAIGNS[0]

const KPI_ICONS: Record<string, { icon: typeof Eye; tint: string }> = {
  footfall: { icon: Footprints, tint: "var(--app-accent)" },
  stop: { icon: Eye, tint: "var(--app-gold)" },
  walkins: { icon: DoorOpen, tint: "var(--app-pos)" },
  dwell: { icon: Timer, tint: "var(--app-accent)" },
}

const SNAPSHOT = [
  { icon: Eye, label: "Window stop rate", value: "7.5%", sub: "peer 8.9%" },
  { icon: Users, label: "Inside now", value: `${OCCUPANCY.now}`, sub: `capacity ${OCCUPANCY.capacity}` },
  { icon: Clock, label: "Till wait", value: OCCUPANCY.avgWait, sub: "avg queue 3" },
  { icon: Clock3, label: "Peak window", value: "16:30", sub: "– 18:45" },
]

const QUICK = [
  { icon: TrendingUp, label: "Storefront", screen: "storefront" as const },
  { icon: Store, label: "Stores", screen: "stores" as const },
  { icon: Megaphone, label: "Campaigns", screen: "campaigns" as const },
  { icon: Map, label: "Zones", screen: "zones" as const },
  { icon: FileText, label: "Brief", screen: "brief" as const },
  { icon: BarChart3, label: "Compare", screen: "compare" as const },
]

export function Overview({ onNavigate }: { onNavigate?: (screen: string) => void }) {
  const [period, setPeriod] = useState<"Today" | "This week">("This week")
  const loading = useMountLoader()
  const kpis = period === "Today" ? KPIS.today : KPIS.week
  const funnel = period === "Today" ? FUNNEL.today : FUNNEL.week

  return (
    <div className="flex flex-col gap-5">
      {/* Greeting + status */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-inter cosmic-text-base font-semibold text-[var(--app-text)]">
            <OverviewGreeting /> — Maison&nbsp;Étoile
          </p>
          <p className="mt-0.5 font-inter font-medium cosmic-text-xs text-[var(--app-sub)]">
            Your storefront answered the street before the door opened.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Chip tone="gold" title={SIMULATED_NOTE}>Sample data</Chip>
        </div>
      </div>

      {/* Storefront snapshot — pictorial header */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut" }}>
        <Panel pad={false} className="overflow-hidden">
          <div className="relative">
            <img
              src="/images/in-store-zones.jpg"
              alt={`${TENANT.name} storefront — ${TENANT.store}`}
              loading="lazy"
              className="h-52 w-full object-cover sm:h-60"
            />
            <div aria-hidden className="absolute inset-0 bg-gradient-to-t from-[var(--app-bg)] via-[var(--app-bg)]/72 to-transparent" />
            <div className="absolute left-0 right-0 top-4 flex flex-wrap items-center gap-2 px-6">
              <Chip tone="gold">Sample preview</Chip>
              <Chip tone="neutral">{TENANT.store}</Chip>
              <Chip tone="gold">WK 12 · FOUNDING PILOT</Chip>
            </div>
            <div className="absolute bottom-0 left-0 right-0 px-6 pb-6">
              <p className="font-inter cosmic-text-xs font-semibold uppercase tracking-[0.14em] text-[var(--app-faint)]">
                {TENANT.name}
              </p>
              <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {SNAPSHOT.map((s) => {
                  const Icon = s.icon
                  return (
                    <div key={s.label} className="flex items-center gap-2.5 rounded-xl border border-[var(--app-line)] bg-[var(--app-card)]/85 px-3.5 py-3 backdrop-blur-sm">
                      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[var(--app-accent-soft)] text-[var(--app-accent)]">
                        <Icon size={15} strokeWidth={2} />
                      </span>
                      <div className="min-w-0">
                        <p className="font-num cosmic-text-base font-bold leading-none text-[var(--app-text)]">{s.value}</p>
                        <p className="mt-0.5 truncate font-inter cosmic-text-2xs leading-tight text-[var(--app-faint)]">
                          {s.label} · {s.sub}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </Panel>
      </motion.div>

      {/* Period */}
      <div className="flex justify-end">
        <Segmented options={["Today", "This week"] as const} value={period} onChange={setPeriod} />
      </div>

      {/* KPI band */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4" aria-busy={loading}>
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Panel key={i} className="h-full">
                <Skeleton className="h-[11px] w-16" />
                <Skeleton className="mt-3 h-[26px] w-24" />
                <Skeleton className="mt-3 h-[20px] w-28" />
              </Panel>
            ))
          : kpis.map((k, i) => (
          <motion.div
            key={k.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.05, ease: "easeOut" }}
          >
            <Panel className="h-full">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  {(() => {
                    const meta = KPI_ICONS[k.id]
                    const Icon = meta ? meta.icon : TrendingUp
                    return (
                      <span
                        className="grid h-7 w-7 shrink-0 place-items-center rounded-lg"
                        style={{ background: "var(--app-accent-soft)", color: meta ? meta.tint : "var(--app-accent)" }}
                      >
                        <Icon size={14} strokeWidth={2.1} />
                      </span>
                    )
                  })()}
                  <Label>{k.label}</Label>
                </div>
                {k.peer && <PeerDot peer={k.peer} />}
              </div>
              <p className="mt-2.5 font-num cosmic-text-2xl font-bold leading-none tracking-[-0.01em] text-[var(--app-text)]">
                <MagicNumber value={k.value} />
              </p>
              <div className="mt-2.5 flex items-center gap-2">
                <DeltaPill delta={k.delta} tone={k.deltaTone} note={k.deltaNote} />
              </div>
            </Panel>
          </motion.div>
        ))}
      </div>

      {/* Peer / competitor benchmark */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}>
        <Panel
          title={PEER_BENCHMARK.title}
          action={
            <div className="flex items-center gap-2">
              <Chip tone="gold">
                <Landmark size={12} className="mr-1 inline" />
                {PEER_BENCHMARK.position.label}
              </Chip>
            </div>
          }
        >
          <div aria-hidden className="mb-5 flex items-center gap-6 cosmic-text-2xs font-semibold uppercase tracking-[0.12em]">
            <span className="flex items-center gap-1.5 text-[var(--app-accent)]">
              <span className="h-2 w-2 rounded-full bg-[var(--app-accent)]" /> this store
            </span>
            <span className="flex items-center gap-1.5 text-[var(--app-faint)]">
              <span className="h-2 w-2 rounded-full bg-[var(--app-faint)]" /> peer median · n=40
            </span>
          </div>

          <div className="flex flex-col gap-5">
            {PEER_BENCHMARK.rows.map((r) => {
              const max = Math.max(r.you, r.peer) * 1.25
              const youPct = Math.max((r.you / max) * 100, 4)
              const peerPct = Math.max((r.peer / max) * 100, 4)
              const diff = Math.abs(parseFloat((r.you - r.peer).toFixed(2)))
              const ahead = r.better === "higher" ? r.you >= r.peer : r.you <= r.peer
              return (
                <div key={r.id}>
                  <div className="flex items-center justify-between gap-3">
                    <Label>{r.label}</Label>
                    <span
                      className="font-inter cosmic-text-xs font-semibold"
                      style={{ color: ahead ? "var(--app-pos)" : "var(--app-neg)" }}
                    >
                      {ahead ? "▲" : "▼"} {diff}{r.suffix} {ahead ? "ahead" : "behind"}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-col gap-1.5">
                    <div className="flex items-center gap-3">
                      <span className="w-9 shrink-0 font-inter cosmic-text-2xs font-semibold uppercase tracking-wide text-[var(--app-accent)]">You</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--app-line)]">
                        <motion.div
                          className="h-full rounded-full"
                          style={{ background: "var(--app-accent)" }}
                          initial={{ width: 0 }}
                          whileInView={{ width: `${youPct}%` }}
                          viewport={{ once: true, margin: "-40px" }}
                          transition={{ duration: 0.8, ease: [0.25, 1, 0.5, 1] }}
                        />
                      </div>
                      <span className="w-16 shrink-0 text-right font-num cosmic-text-xs font-bold leading-none text-[var(--app-text)]">
                        {r.you}{r.unit}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="w-9 shrink-0 font-inter cosmic-text-2xs font-semibold uppercase tracking-wide text-[var(--app-faint)]">Peer</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--app-line)]">
                        <motion.div
                          className="h-full rounded-full"
                          style={{ background: "var(--app-faint)" }}
                          initial={{ width: 0 }}
                          whileInView={{ width: `${peerPct}%` }}
                          viewport={{ once: true, margin: "-40px" }}
                          transition={{ duration: 0.8, delay: 0.1, ease: [0.25, 1, 0.5, 1] }}
                        />
                      </div>
                      <span className="w-16 shrink-0 text-right font-num cosmic-text-xs font-bold leading-none text-[var(--app-faint)]">
                        {r.peer}{r.unit}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-6 flex items-center gap-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-raise)] px-4 py-3">
            <Trophy size={16} strokeWidth={2} className="shrink-0" style={{ color: "var(--app-gold)" }} />
            <p className="font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">
              Position: <span className="font-semibold text-[var(--app-text)]">#{PEER_BENCHMARK.position.rank} of {PEER_BENCHMARK.position.cohort}</span> stores by
              stop rate — {PEER_BENCHMARK.position.label}.
            </p>
          </div>
        </Panel>
      </motion.div>

      {/* Business on the floor */}
      <BusinessKpis />

      {/* Chart + funnel */}
      <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="Street footfall" action={<Label>by hour · {period}</Label>} verified="Illustrative sample">
          <AreaChart data={TRAFFIC_HOURS} peaks={[{ from: "15", to: "17" }]} />
        </Panel>
        <Panel title="Physical funnel" action={<Label>{period}</Label>}>
          <FunnelBars stages={funnel} />
        </Panel>
      </div>

      {/* Live occupancy + visitor flow */}
      <div className="grid gap-5 xl:grid-cols-[1fr_2fr]">
        <OccupancyGauge />
        <Panel title="How shoppers move" action={<Label>path popularity</Label>} info="Thicker edge = more travelled path. Anonymised trajectories on aggregate.">
          <VisitorFlow />
        </Panel>
      </div>

      {/* Revenue-grade signal */}
      <RevenueKpis />

      {/* Stores + A/B */}
      <div className="grid gap-5 xl:grid-cols-[1fr_1.3fr]">
        <Panel title="Stores" action={<Label>{STORES.length}</Label>}>
          <div className="flex flex-col gap-3">
            {STORES.map((s) => (
              <div key={s.id} className="flex items-center justify-between gap-3 rounded-xl border border-[var(--app-line)] p-3.5">
                <div className="min-w-0">
                  <p className="truncate font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{s.name}</p>
                  <p className="font-inter font-medium cosmic-text-xs text-[var(--app-faint)]">
                    {s.footfallToday.toLocaleString("en-IN")} · stop {s.stopRate}
                  </p>
                </div>
                <Sparkline data={s.spark} tone={s.trend === "up" ? "pos" : s.trend === "down" ? "neg" : "gold"} />
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          title="Window reset"
          action={<Label>{AFT_CAMPAIGN.window}</Label>}
          verified="Sample scenario"
        >
          <div className="flex flex-col gap-5">
            <div>
              <div className="mb-1.5 flex items-baseline justify-between gap-3">
                <span className="font-inter cosmic-text-xs text-[var(--app-text)]">{AFT_CAMPAIGN.metricLabel}</span>
                <span className="font-inter cosmic-text-xs font-semibold font-num text-[var(--app-text)]">
                  {AFT_CAMPAIGN.before} <span className="text-[var(--app-faint)]">→</span> {AFT_CAMPAIGN.after}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="h-2.5 w-full overflow-hidden rounded-full" style={{ background: "var(--app-grid)" }}>
                  <div className="h-full rounded-full" style={{ width: "100%", background: "var(--app-faint)" }} />
                </div>
                <span className="font-num cosmic-text-xs font-semibold text-[var(--app-faint)]">{AFT_CAMPAIGN.before}</span>
              </div>
              <div className="mt-1.5 flex items-center gap-3">
                <div className="h-2.5 w-full overflow-hidden rounded-full" style={{ background: "var(--app-grid)" }}>
                  <div className="h-full rounded-full" style={{ width: "88%", background: "var(--app-gold)" }} />
                </div>
                <span className="font-num cosmic-text-xs font-semibold text-[var(--app-text)]">{AFT_CAMPAIGN.after}</span>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <span className="font-inter cosmic-text-lg font-bold font-num" style={{ color: "var(--app-pos)" }}>
                {AFT_CAMPAIGN.uplift}
              </span>
            </div>
          </div>
        </Panel>
      </div>

      {/* Flip + decisions */}
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Signals for the floor" action={<Label>{INSIGHTS.length} records</Label>}>
          <div className="flex flex-col gap-2.5">
            {INSIGHTS.slice(0, 3).map((ins, i) => (
              <div key={ins.id} className="flex items-center gap-3 rounded-xl border border-[var(--app-line)] p-3.5">
                <span
                  className="grid h-6 w-6 shrink-0 place-items-center rounded-full font-inter cosmic-text-2xs font-bold"
                  style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}
                >
                  {i + 1}
                </span>
                <p className="font-inter cosmic-text-sm font-medium text-[var(--app-text)]">{ins.title}</p>
                <span className="ml-auto shrink-0 font-inter cosmic-text-2xs text-[var(--app-faint)]">{ins.type}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          title="This week · decisions"
          action={<Label>{BRIEF.week}</Label>}
        >
          <ol className="flex flex-col gap-3">
            {BRIEF.actions.map((a, i) => (
              <li key={a.title} className="flex items-start gap-3.5">
                <span
                  className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full font-inter font-medium cosmic-text-xs font-bold"
                  style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}
                >
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <p className="font-inter cosmic-text-sm font-medium leading-snug text-[var(--app-text)]">{a.title}</p>
                  <p className="mt-0.5 font-inter font-medium cosmic-text-xs text-[var(--app-faint)]">{a.tag} · {a.priority}</p>
                </div>
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      {/* Quick nav */}
      <Panel pad={false}>
        <div className="grid grid-cols-3 gap-2 p-3 sm:grid-cols-6">
          {QUICK.map((q) => (
            <button
              key={q.label}
              onClick={() => onNavigate?.(q.screen)}
              className="group flex flex-col items-center gap-2 rounded-2xl px-3 py-4 text-center transition-colors hover:bg-[var(--app-raise)]"
            >
              <q.icon size={18} strokeWidth={2} className="text-[var(--app-sub)] transition-colors group-hover:text-[var(--app-gold)]" />
              <span className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">{q.label}</span>
            </button>
          ))}
        </div>
      </Panel>

      <p className="font-inter font-medium cosmic-text-xs text-[var(--app-faint)]">
        {TENANT.name} · {TENANT.store} · {SIMULATED_NOTE}
      </p>
    </div>
  )
}

function OverviewGreeting() {
  const h = new Date().getHours()
  const g = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"
  return <>{g}</>
}

function MagicNumber({ value }: { value: string }) {
  const isNumeric = /^-?[\d][\d,]*\.?\d*%?$/.test(value.trim())
  if (!isNumeric) return <>{value}</>
  const hasPct = value.includes("%")
  const num = parseFloat(value.replace(/[^0-9.]/g, ""))
  if (!Number.isFinite(num)) return <>{value}</>
  const decimals = hasPct ? 1 : value.includes(".") ? 1 : 0
  return (
    <>
      <CountUp to={num} decimals={decimals} />
      {hasPct ? "%" : ""}
    </>
  )
}
