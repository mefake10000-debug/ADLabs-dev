import { ArrowRight, ArrowUpRight, TriangleAlert, Store } from "lucide-react"
import { Panel, Label, GradePill, DeltaPill, ScreenHeader } from "../ui"
import { Sparkline, AreaChart, HBars } from "../charts"
import { STORES, TRAFFIC_HOURS, ZONES, DEMOGRAPHICS } from "../../data/dashboard"

export function Stores({ onOpen }: { onOpen: (id: string) => void }) {
  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader
        icon={Store}
        eyebrow="Store network"
        title="Stores"
        sub="Composite grade = stop rate, capture and dwell versus the anonymised peer set."
      />

      <Panel
        pad={false}
        verified="Sample portfolio"
        info="Example store ranking · figures are sample data, not a live day view."
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead>
              <tr className="border-b border-[var(--app-line)]">
                {["Store", "Grade", "Footfall today", "Stop rate", "7-day trend", ""].map((h) => (
                  <th key={h} className="px-5 py-3.5">
                    <Label>{h}</Label>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {STORES.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => onOpen(s.id)}
                  className="cursor-pointer border-b border-[var(--app-line)] transition-colors last:border-0 hover:bg-[var(--app-card)]"
                >
                  <td className="px-5 py-4">
                    <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{s.name}</p>
                    <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{s.city}</p>
                  </td>
                  <td className="px-5 py-4">
                    <GradePill grade={s.grade} />
                  </td>
                  <td className="px-5 py-4 font-inter cosmic-text-sm font-semibold font-num text-[var(--app-text)]">
                    {s.footfallToday.toLocaleString("en-US")}
                  </td>
                  <td className="px-5 py-4">
                    <span className="font-inter cosmic-text-sm font-semibold font-num text-[var(--app-text)]">
                      {s.stopRate}
                    </span>
                    {s.flag && (
                      <span
                        className="ml-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-inter cosmic-text-2xs font-semibold"
                        style={{ background: "color-mix(in srgb, var(--app-neg) 12%, transparent)", color: "var(--app-neg)" }}
                      >
                        <TriangleAlert size={10} strokeWidth={2.4} />
                        flag
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-4">
                    <Sparkline data={s.spark} tone={s.trend === "up" ? "pos" : s.trend === "down" ? "neg" : "gold"} />
                  </td>
                  <td className="px-5 py-4 text-right text-[var(--app-faint)]">
                    <ArrowRight size={16} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">
        Adding your next location takes one sensor and under two hours on site.
      </p>
    </div>
  )
}

export function StoreDetail({ storeId }: { storeId: string }) {
  const s = STORES.find((x) => x.id === storeId) ?? STORES[0]
  const topZones = ZONES.slice(0, 4).map((z) => ({ label: z.name, pct: z.traffic }))

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-inter cosmic-text-xl font-bold tracking-[-0.01em] text-[var(--app-text)]">{s.name}</h1>
          <p className="mt-0.5 font-inter cosmic-text-xs text-[var(--app-faint)]">
            {s.city} · Sample day view · no edge connection
          </p>
        </div>
        <GradePill grade={s.grade} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        <Panel title="Today's curve" action={<Label>PEAK 15:00 – 17:00</Label>}>
          <AreaChart data={TRAFFIC_HOURS} peaks={[{ from: "15", to: "17" }]} height={190} />
          <div className="mt-4 flex flex-wrap gap-2">
            <DeltaPill delta="+6.2%" tone="pos" note="vs yesterday" />
            <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">
              Peak markers land inside the shaded band — staff accordingly.
            </span>
          </div>
        </Panel>

        <Panel title="Cohorts · anonymised">
          <HBars items={DEMOGRAPHICS.ages.map((a) => ({ label: a.band, pct: a.pct }))} />
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[var(--app-line)] p-3">
              <Label>Solo</Label>
              <p className="mt-1 font-inter cosmic-text-lg font-bold font-num text-[var(--app-text)]">
                {DEMOGRAPHICS.dynamics.solo}%
              </p>
            </div>
            <div className="rounded-xl border border-[var(--app-line)] p-3">
              <Label>Pair</Label>
              <p className="mt-1 font-inter cosmic-text-lg font-bold font-num text-[var(--app-text)]">
                {DEMOGRAPHICS.dynamics.pair}%
              </p>
            </div>
          </div>
          <p className="mt-3 font-inter cosmic-text-2xs text-[var(--app-faint)]">{DEMOGRAPHICS.note}</p>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Zone attention share">
          <HBars items={topZones} />
        </Panel>
        <Panel
          title="Flag"
          action={
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-inter cosmic-text-2xs font-bold"
              style={{ background: "color-mix(in srgb, var(--app-neg) 10%, transparent)", color: "var(--app-neg)" }}
            >
              <TriangleAlert size={11} strokeWidth={2.4} />
              Needs attention
            </span>
          }
        >
          <p className="font-inter cosmic-text-sm font-medium leading-relaxed text-[var(--app-text)]">
            {s.flag ?? "No flags today. Stop rate, dwell and staffing all inside the peer band."}
          </p>
          <p className="mt-3 font-inter cosmic-text-xs text-[var(--app-sub)]">
            Suggested move: rotate Vitrine West and re-measure over a 7-day A/B window.
          </p>
          <button
            className="mt-5 inline-flex items-center gap-2 rounded-full px-4 py-2 font-inter cosmic-text-xs font-semibold transition-transform hover:-translate-y-0.5"
            style={{ background: "var(--app-text)", color: "var(--app-card)" }}
          >
            Open in Weekly Brief <ArrowUpRight size={13} strokeWidth={2.5} />
          </button>
        </Panel>
      </div>
    </div>
  )
}
