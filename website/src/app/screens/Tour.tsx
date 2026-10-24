import {
  Eye, Footprints, Timer, Megaphone, Sparkles, Route, ShieldCheck, ArrowUpRight,
} from "lucide-react"
import { Panel, Label, DeltaPill, Chip, InfoTip } from "../ui"
import { AreaChart, FunnelBars, Sparkline, DonutChart, HeatGrid } from "../charts"
import {
  KPIS, FUNNEL, TRAFFIC_HOURS, STORES, ZONES, ALERTS, TENANT,
  WINDOW_ENGAGEMENT, SIMULATED_NOTE, PEER_NOTE,
} from "../../data/dashboard"

const DATA_CLASSES = [
  {
    icon: Footprints,
    title: "Footfall",
    where: "Overview · Storefront",
    desc: "How many people pass your store. Shown as a daily number and an hourly curve.",
    visual: <Sparkline data={[88, 132, 168, 198, 186, 214, 262, 289, 271, 196, 158, 112]} tone="gold" />,
  },
  {
    icon: Eye,
    title: "Stop rate + window engagement",
    where: "Storefront · Window",
    desc: "Who pauses at the glass, and how long — glance, deep attention, or a turn inside.",
    visual: (
      <div className="flex items-end gap-1.5">
        {[42, 39, 19].map((p, i) => (
          <div key={i} className="flex flex-col items-center gap-1">
            <div className="w-8 rounded-md" style={{ height: `${p * 1.6}px`, background: i === 0 ? "var(--app-gold)" : i === 1 ? "color-mix(in srgb, var(--app-gold) 60%, var(--app-card))" : "var(--app-faint)", opacity: 1 - i * 0.15 }} />
          </div>
        ))}
      </div>
    ),
  },
  {
    icon: Timer,
    title: "Dwell & attention depth",
    where: "Zones · Product",
    desc: "Minutes inside, and which fixtures hold people longest — the heatmap makes it obvious.",
    visual: <DonutChart data={WINDOW_ENGAGEMENT} size={84} showCenter={false} />,
  },
  {
    icon: Megaphone,
    title: "Campaign proof",
    where: "Campaigns",
    desc: "Before/after capture: the same window, two rotations, one honest number.",
    visual: (
      <div className="flex items-center gap-2 font-num">
        <span className="font-mono cosmic-text-base font-bold text-[var(--app-sub)]">6.4%</span>
        <span className="text-[var(--app-faint)]">→</span>
        <span className="font-mono cosmic-text-base font-bold text-[var(--app-pos)]">7.3%</span>
        <span className="rounded-full px-1.5 py-0.5 font-inter cosmic-text-2xs font-bold" style={{ background: "color-mix(in srgb, var(--app-pos) 12%, transparent)", color: "var(--app-pos)" }}>
          +14.6%
        </span>
      </div>
    ),
  },
  {
    icon: Route,
    title: "Zone heat",
    where: "Zones",
    desc: "Every zone on one grid — darkest cell is where the day is happening.",
    visual: <HeatGrid zones={ZONES.slice(0, 5)} />,
  },
]

const TIMELINE = [
  {
    phase: "Day 1",
    chip: "Available after camera setup",
    items: [
      "Your storefront hero — footfall, stop rate, walk-ins, dwell, dead zones",
      "Today's curve with the peak band",
      "The five numbers that matter",
    ],
  },
  {
    phase: "Week 1",
    chip: "Patterns begin to talk",
    items: [
      "Traffic by day × hour — the heatmap",
      "Window engagement breakdown (glance vs deep attention)",
      "First zone flags and alerts",
    ],
  },
  {
    phase: "Month 1",
    chip: "Intelligence compounds",
    items: [
      "12-week history + forecast with confidence band",
      "Verified before/after campaign results",
      "Monday Brief with three actions — generated from your data, not from templates",
    ],
  },
]

export function Tour() {
  const k = KPIS.today

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow uppercase tracking-[0.14em] text-[var(--app-sub)]">Onboarding · 60 seconds</p>
          <h1 className="mt-3 font-serif tracking-[-0.01em] cosmic-text-4xl leading-[1.02] text-[var(--app-text)] sm:cosmic-text-5xl">
            This is how you'll see it
          </h1>
          <p className="mt-3 max-w-2xl font-inter cosmic-text-sm leading-relaxed text-[var(--app-sub)]">
            Your store, your street, your numbers — exactly as the owner interface renders them. These are
            real components with sample data so you can judge the product before the equipment arrives.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Chip tone="gold">{SIMULATED_NOTE}</Chip>
          <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">{PEER_NOTE}</span>
        </div>
      </div>

      {/* Owner interface preview */}
      <Panel pad={false} verified="Sample preview">
        <div className="border-b border-[var(--app-line)] p-6 sm:p-7">
          <div className="flex items-center gap-3">
            <span
              className="grid h-11 w-11 place-items-center rounded-2xl"
              style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}
            >
              <Sparkles size={20} strokeWidth={1.8} />
            </span>
            <div>
              <p className="card-title text-[var(--app-text)]">Your owner dashboard</p>
              <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">
                This is the exact interface — logged in as the owner of {TENANT.name} · one store, one sensor.
              </p>
            </div>
          </div>
        </div>

        {/* Browser frame */}
        <div className="p-5 sm:p-7">
          <div className="overflow-hidden rounded-2xl border border-[var(--app-line)]" style={{ background: "var(--app-bg)" }}>
            {/* Window chrome */}
            <div className="flex items-center gap-2 border-b border-[var(--app-line)] px-4 py-2.5" style={{ background: "var(--app-card)" }}>
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#ff5f57" }} />
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#febc2e" }} />
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#28c840" }} />
              <span className="ml-3 flex-1 truncate rounded-lg border border-[var(--app-line)] px-3 py-1 font-mono cosmic-text-2xs text-[var(--app-faint)]">
                adlabs.app/owner — {TENANT.store}
              </span>
            </div>

            {/* Mini dashboard */}
            <div className="p-4 sm:p-5">
              {/* Topbar */}
              <div className="flex flex-wrap items-center justify-between gap-2 pb-4">
                <div>
                  <p className="card-title text-[var(--app-text)]">Overview</p>
                  <p className="font-inter cosmic-text-2xs text-[var(--app-faint)]">Owner view · {TENANT.store}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <Chip tone="gold">Sample</Chip>
                  <Chip tone="gold">Demo</Chip>
                </div>
              </div>

              {/* Mini KPIs */}
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-5">
                {k.map((item) => (
                  <div key={item.id} className="rounded-xl border border-[var(--app-line)] p-3" style={{ background: "var(--app-card)" }}>
                    <Label>{item.label}</Label>
                    <p className="mt-1.5 font-inter cosmic-text-lg font-bold font-num leading-none tracking-[-0.02em] text-[var(--app-text)]">{item.value}</p>
                    <div className="mt-1.5">
                      <DeltaPill delta={item.delta} tone={item.deltaTone} note={item.deltaNote} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Mini charts */}
              <div className="mt-3 grid gap-2.5 xl:grid-cols-[1.5fr_1fr]">
                <div className="rounded-xl border border-[var(--app-line)] p-3.5" style={{ background: "var(--app-card)" }}>
                  <div className="mb-2 flex items-center justify-between">
                    <p className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">Street footfall by hour</p>
                    <InfoTip text="Gold band = peak attention window. This cues your staffing for tomorrow." />
                  </div>
                  <AreaChart data={TRAFFIC_HOURS} peaks={[{ from: "15", to: "17" }]} height={120} />
                </div>
                <div className="rounded-xl border border-[var(--app-line)] p-3.5" style={{ background: "var(--app-card)" }}>
                  <div className="mb-2 flex items-center justify-between">
                    <p className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">Physical funnel</p>
                    <Label>Today</Label>
                  </div>
                  <FunnelBars stages={FUNNEL.today.slice(0, 4)} />
                </div>
              </div>

              {/* Mini store strip */}
              <div className="mt-3 rounded-xl border border-[var(--app-line)] p-3.5" style={{ background: "var(--app-card)" }}>
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">Your stores</p>
                  <span className="font-inter cosmic-text-2xs text-[var(--app-faint)]">3 locations · status</span>
                </div>
                <div className="grid gap-2 sm:grid-cols-3">
                  {STORES.map((s) => (
                    <div key={s.id} className="flex items-center justify-between gap-2 rounded-lg border border-[var(--app-line)] px-3 py-2.5">
                      <div className="min-w-0">
                        <p className="truncate font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">{s.name}</p>
                        <p className="font-inter cosmic-text-2xs text-[var(--app-faint)]">Stop {s.stopRate} · {s.footfallToday.toLocaleString("en-US")}</p>
                      </div>
                      <Sparkline data={s.spark} tone={s.trend === "up" ? "pos" : s.trend === "down" ? "neg" : "gold"} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Capture ribbon */}
              <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-[var(--app-line)] p-3" style={{ background: "var(--app-card)" }}>
                <ShieldCheck size={14} className="shrink-0 text-[var(--app-gold)]" strokeWidth={2.2} />
                <p className="font-inter cosmic-text-xs text-[var(--app-sub)]">
                  Faces never leave the device. This preview is sample data — your store renders with your own numbers as soon as the sensor starts measuring.
                </p>
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* What you'll be looking at */}
      <Panel
        title="What you'll be looking at"
        action={<Label>6 data classes</Label>}
        info="Six data classes — each card previews how it renders."
      >
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {DATA_CLASSES.map((d) => (
            <div key={d.title} className="rounded-2xl border border-[var(--app-line)] p-4.5 transition-colors hover:border-[var(--app-gold)]" style={{ background: "var(--app-raise)" }}>
              <div className="flex items-center gap-2.5">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl" style={{ background: "var(--app-card)", color: "var(--app-gold)" }}>
                  <d.icon size={15} strokeWidth={2} />
                </span>
                <div className="min-w-0">
                  <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{d.title}</p>
                  <p className="font-inter cosmic-text-2xs text-[var(--app-faint)]">{d.where}</p>
                </div>
              </div>
              <div className="mt-3.5 flex min-h-[52px] items-center">
                {d.visual}
              </div>
              <p className="mt-3 border-t border-[var(--app-line)] pt-2.5 font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">
                {d.desc}
              </p>
            </div>
          ))}
          <div className="rounded-2xl border border-[var(--app-line)] p-4.5" style={{ background: "var(--app-raise)" }}>
            <div className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl" style={{ background: "var(--app-card)", color: "var(--app-neg)" }}>
                <Megaphone size={15} strokeWidth={2} />
              </span>
              <div className="min-w-0">
                <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">Alerts</p>
                <p className="font-inter cosmic-text-2xs text-[var(--app-faint)]">Everywhere</p>
              </div>
            </div>
            <div className="mt-3.5 flex min-h-[52px] flex-col justify-center">
              <div className="flex items-start gap-2 rounded-xl border border-[var(--app-line)] p-2.5" style={{ background: "var(--app-card)" }}>
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: "var(--app-neg)" }} />
                <div className="min-w-0">
                  <p className="truncate font-inter cosmic-text-2xs font-semibold text-[var(--app-text)]">{ALERTS[0].zone} · {ALERTS[0].message}</p>
                  <p className="font-inter cosmic-text-2xs text-[var(--app-faint)]">Action: {ALERTS[0].action}</p>
                </div>
              </div>
            </div>
            <p className="mt-3 border-t border-[var(--app-line)] pt-2.5 font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">
              Severity-coloured, with the fix attached. It tells you what broke, what it costs, and how to repair it.
            </p>
          </div>
        </div>
      </Panel>

      {/* Timeline */}
      <Panel
        title="It grows with you"
        action={<Label>Day 1 → Month 1</Label>}
        info="Stays simple first, deepens as data accumulates."
      >
        <div className="grid gap-4 md:grid-cols-3">
          {TIMELINE.map((t, i) => (
            <div key={t.phase} className="relative rounded-2xl border border-[var(--app-line)] p-5" style={{ background: "var(--app-raise)" }}>
              <div className="flex items-center justify-between">
                <span className="font-mono cosmic-text-xs font-bold text-[var(--app-gold)]">{t.phase}</span>
                <span className="rounded-full px-2 py-0.5 font-inter cosmic-text-2xs font-bold" style={{ background: "color-mix(in srgb, var(--app-gold) 12%, transparent)", color: "var(--app-gold)" }}>
                  {t.chip}
                </span>
              </div>
              <ul className="mt-3.5 flex flex-col gap-2">
                {t.items.map((x) => (
                  <li key={x} className="flex items-start gap-2">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full" style={{ background: "var(--app-gold)" }} />
                    <span className="font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">{x}</span>
                  </li>
                ))}
              </ul>
              {i < TIMELINE.length - 1 && (
                <ArrowUpRight size={14} className="absolute -right-2 -top-2 rounded-full border border-[var(--app-line)] bg-[var(--app-card)] p-0.5 text-[var(--app-faint)]" />
              )}
            </div>
          ))}
        </div>
      </Panel>

      <p className="flex items-center gap-2 font-inter cosmic-text-xs text-[var(--app-faint)]">
        <ShieldCheck size={13} className="text-[var(--app-gold)]" />
        Hover every “?” in the product for context — nothing in here is a black box.
      </p>
    </div>
  )
}
