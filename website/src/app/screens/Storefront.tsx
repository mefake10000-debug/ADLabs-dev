import { ArrowUpRight, ArrowDownRight, Clock } from "lucide-react"
import { Panel, Label, DeltaPill, Chip } from "../ui"
import { LineChart, DonutChart, FunnelBars } from "../charts"
import {
  KPIS, FUNNEL, PREDICTIONS, WEEKLY_PLAN, INSIGHTS,
  WINDOW_ENGAGEMENT, WEEKLY_HISTORY,
  SIMULATED_NOTE, TENANT, PEER_NOTE,
} from "../../data/dashboard"

const trendData = WEEKLY_HISTORY.map((w) => ({ week: w.week, value: w.stopRate }))

export function Storefront() {
  const kpis = KPIS.week
  const funnel = FUNNEL.week

  return (
    <div className="flex flex-col gap-5">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl border border-[var(--app-line)]" style={{ boxShadow: "var(--app-shadow)" }}>
        <img src="/images/hero-storefront.jpg" alt="Madison Avenue Flagship storefront" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0" style={{ background: "linear-gradient(to right, rgba(18,18,18,0.85) 0%, rgba(18,18,18,0.5) 55%, rgba(18,18,18,0.15) 100%)" }} />
        <div className="relative flex min-h-[260px] flex-col justify-between p-7 sm:p-10">
          <div className="flex items-center gap-2">
            <Chip tone="gold">Sample preview</Chip>
            <Chip tone="gold">{SIMULATED_NOTE}</Chip>
          </div>
          <div>
            <p className="eyebrow uppercase tracking-[0.16em] text-white/60">
              Storefront analytics · {TENANT.store}
            </p>
            <h1 className="mt-3 font-serif tracking-[-0.01em] cosmic-text-4xl leading-[1.02] text-white sm:cosmic-text-5xl">The window is the store</h1>
          </div>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {kpis.map((k) => (
          <Panel key={k.id} className="group">
            <div className="flex items-start justify-between gap-2">
              <Label>{k.label}</Label>
              {k.peer && <span className="font-inter cosmic-text-2xs font-medium text-[var(--app-faint)]">peer {k.peer}</span>}
            </div>
            <p className="mt-2.5 font-inter cosmic-text-2xl font-bold font-num leading-none tracking-[-0.01em] text-[var(--app-text)]">
              {k.value}
            </p>
            <div className="mt-2.5 flex items-center gap-2">
              <DeltaPill delta={k.delta} tone={k.deltaTone} note={k.deltaNote} />
            </div>
            <p className="mt-2.5 border-t border-[var(--app-line)] pt-2.5 font-inter cosmic-text-xs leading-snug text-[var(--app-sub)]">
              {k.hint}
            </p>
          </Panel>
        ))}
      </div>

      {/* Stop rate trend with prediction */}
      <Panel
        title="Stop rate · W1 → Wk 16 (predicted)"
        action={<Chip tone="gold">Prediction</Chip>}
        verified="Illustrative sample"
        info="Example weekly series · dashed = illustrative projection, band = example range."
      >
        <LineChart
          data={trendData}
          prediction={{
            startIdx: 11,
            points: [
              { week: "Wk 13", value: 11.8 },
              { week: "Wk 14", value: 11.9 },
              { week: "Wk 15", value: 12.0 },
              { week: "Wk 16", value: 12.0 },
            ],
          }}
          height={200}
        />
        <div className="mt-4 flex flex-wrap gap-3">
          <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">Example trend: 9.2% → 11.4% across 12 sample weeks</span>
          <span className="font-inter cosmic-text-xs font-semibold font-num" style={{ color: "var(--app-pos)" }}>Projected 12.0% by Wk 16</span>
        </div>
      </Panel>

      {/* Funnel + Window engagement */}
      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Panel
          title="Continuous physical funnel"
          action={<Label>Wk 12</Label>}
          info="Pass → stop → enter → explore → engage. Rate = conversion out of previous stage."
        >
          <FunnelBars stages={funnel} />
        </Panel>
        <Panel
          title="Window engagement"
          info="Glance (< 2s) · deep attention (> 4s) · immediate turn inside."
        >
          <DonutChart data={WINDOW_ENGAGEMENT} size={150} />
          <p className="mt-4 font-inter cosmic-text-xs text-[var(--app-faint)]">{PEER_NOTE}</p>
        </Panel>
      </div>

      {/* Predictions + Plan */}
      <div className="grid gap-5 xl:grid-cols-[1fr_1.3fr]">
        <Panel title="Predictions" action={<Chip tone="gold">3 ahead</Chip>}>
          <div className="flex flex-col gap-3">
            {PREDICTIONS.map((p) => (
              <div key={p.metric} className="rounded-xl border border-[var(--app-line)] p-3.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{p.metric}</span>
                  <span
                    className="grid h-5 w-5 place-items-center rounded-full"
                    style={{ background: p.direction === "up" ? "color-mix(in srgb, var(--app-pos) 12%, transparent)" : p.direction === "down" ? "color-mix(in srgb, var(--app-neg) 12%, transparent)" : "color-mix(in srgb, var(--app-gold) 12%, transparent)", color: p.direction === "up" ? "var(--app-pos)" : p.direction === "down" ? "var(--app-neg)" : "var(--app-gold)" }}
                  >
                    {p.direction === "up" ? <ArrowUpRight size={12} strokeWidth={2.4} /> : p.direction === "down" ? <ArrowDownRight size={12} strokeWidth={2.4} /> : <Clock size={12} strokeWidth={2.4} />}
                  </span>
                </div>
                <div className="mt-2 flex items-baseline gap-2 font-inter cosmic-text-xs">
                  <span className="font-num font-semibold text-[var(--app-text)]">{p.current}</span>
                  <span className="text-[var(--app-faint)]">→</span>
                  <span className="font-num font-semibold" style={{ color: "var(--app-gold)" }}>{p.projected}</span>
                  <span className="text-[var(--app-faint)]">{p.timeframe}</span>
                </div>
                <p className="mt-1 font-inter cosmic-text-2xs text-[var(--app-faint)]">{p.basis} · {p.confidence} confidence</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Next week's plan" action={<Label>{WEEKLY_PLAN.week}</Label>}>
          <div className="flex flex-col gap-3">
            {WEEKLY_PLAN.actions.map((a, i) => (
              <div key={a.title} className="flex items-start gap-3.5 rounded-xl border border-[var(--app-line)] p-3.5">
                <span
                  className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full font-inter cosmic-text-xs font-bold"
                  style={{ background: a.priority === "high" ? "color-mix(in srgb, var(--app-gold) 12%, transparent)" : "color-mix(in srgb, var(--app-raise), transparent)", color: a.priority === "high" ? "var(--app-gold)" : "var(--app-sub)" }}
                >
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{a.title}</p>
                    <span className="rounded-full px-2 py-0.5 font-inter cosmic-text-2xs font-bold uppercase tracking-[0.08em]" style={{ background: "color-mix(in srgb, var(--app-raise), transparent)", color: "var(--app-faint)" }}>{a.category}</span>
                  </div>
                  <p className="mt-1 font-inter cosmic-text-xs text-[var(--app-sub)]">{a.impact}</p>
                </div>
                <span className="rounded-full px-2 py-0.5 font-inter cosmic-text-2xs font-bold" style={{ background: a.cost === "free" ? "color-mix(in srgb, var(--app-pos) 12%, transparent)" : a.cost === "low" ? "color-mix(in srgb, var(--app-gold) 12%, transparent)" : "color-mix(in srgb, var(--app-neg) 12%, transparent)", color: a.cost === "free" ? "var(--app-pos)" : a.cost === "low" ? "var(--app-gold)" : "var(--app-neg)" }}>
                  {a.cost}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Insights */}
      <Panel title="Insights from the edge" action={<Chip tone="gold">{INSIGHTS.length} items</Chip>}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {INSIGHTS.map((ins) => (
            <div key={ins.id} className="rounded-xl border border-[var(--app-line)] p-4">
              <div className="flex items-center gap-2">
                <span
                  className="rounded-full px-2 py-0.5 font-inter cosmic-text-2xs font-bold uppercase tracking-[0.08em]"
                  style={{ background: ins.type === "prediction" ? "color-mix(in srgb, var(--app-gold) 12%, transparent)" : ins.type === "anomaly" ? "color-mix(in srgb, var(--app-neg) 12%, transparent)" : ins.type === "opportunity" ? "color-mix(in srgb, var(--app-pos) 12%, transparent)" : "color-mix(in srgb, var(--app-raise), transparent)", color: ins.type === "prediction" ? "var(--app-gold)" : ins.type === "anomaly" ? "var(--app-neg)" : ins.type === "opportunity" ? "var(--app-pos)" : "var(--app-sub)" }}
                >
                  {ins.type}
                </span>
                <span className="rounded-full px-2 py-0.5 font-inter cosmic-text-2xs font-bold" style={{ background: "color-mix(in srgb, var(--app-raise), transparent)", color: "var(--app-faint)" }}>{ins.confidence}</span>
              </div>
              <h3 className="mt-3 font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{ins.title}</h3>
              <p className="mt-2 font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">{ins.action}</p>
            </div>
          ))}
        </div>
      </Panel>

      <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{SIMULATED_NOTE} · {PEER_NOTE}</p>
    </div>
  )
}
