import { History as HistoryIcon } from "lucide-react"
import { Panel, Label, Chip, ScreenHeader } from "../ui"
import { LineChart, FunnelBars } from "../charts"
import { WEEKLY_HISTORY, FUNNEL_HISTORY, SIMULATED_NOTE, PEER_NOTE } from "../../data/dashboard"

export function History() {
  const lineData = WEEKLY_HISTORY.map((w) => ({ week: w.week, value: w.stopRate }))
  const calcPeak = (k: "footfall" | "stopRate" | "walkins") => {
    const p = WEEKLY_HISTORY.reduce((a, b) => ((b[k] as number) > (a[k] as number) ? b : a))
    return { value: k === "stopRate" ? `${p[k]}%` : (p[k] as number).toLocaleString("en-IN"), note: p.week }
  }
  const peakFootfall = calcPeak("footfall")
  const peakStop = calcPeak("stopRate")
  const peakWalkins = calcPeak("walkins")
  const peakDwell = WEEKLY_HISTORY.reduce((a, b) => {
    const secs = (w: string) => parseInt(w.replace(/[^0-9]/g, ""), 10)
    return secs(b.dwell) > secs(a.dwell) ? b : a
  })

  const funnelStages = (key: "baseline" | "wk4" | "wk8" | "wk12") => {
    const data = FUNNEL_HISTORY[key]
    if (Array.isArray(data)) return data
    return Object.entries(data).map(([stage, value]) => ({ stage, value, rate: "", label: "" }))
  }

  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader
        icon={HistoryIcon}
        eyebrow="Store intelligence"
        title="History"
        sub="12-week trend with forward projection — stop rate, walk-ins, and dwell."
      />

      {/* Weekly KPI cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Peak stop rate", value: peakStop.value, note: peakStop.note, tone: "pos" as const },
          { label: "Peak footfall", value: peakFootfall.value, note: peakFootfall.note, tone: "pos" as const },
          { label: "Peak walk-ins", value: peakWalkins.value, note: peakWalkins.note, tone: "pos" as const },
          { label: "Peak dwell", value: peakDwell.dwell, note: peakDwell.week, tone: "pos" as const },
        ].map((k) => (
          <Panel key={k.label}>
            <Label>{k.label}</Label>
            <p className="mt-2.5 font-inter cosmic-text-xl font-bold font-num leading-none text-[var(--app-text)]">{k.value}</p>
            <p className="mt-2 font-inter cosmic-text-xs font-semibold font-num" style={{ color: "var(--app-pos)" }}>{k.note}</p>
          </Panel>
        ))}
      </div>

      {/* Stop rate trend with prediction */}
      <Panel
        title="Stop rate · W1 → Wk 16 (predicted)"
        action={<Chip tone="gold">Prediction</Chip>}
        verified="Illustrative sample"
        info="Each dot = one week's average stop rate. Dashed line = 8-week forecast."
      >
        <LineChart
          data={lineData}
          prediction={{
            startIdx: 11,
            points: [
              { week: "Wk 13", value: 11.8 },
              { week: "Wk 14", value: 11.9 },
              { week: "Wk 15", value: 12.0 },
              { week: "Wk 16", value: 12.0 },
            ],
          }}
          height={220}
        />
        <p className="mt-4 font-inter cosmic-text-xs text-[var(--app-faint)]">
          Linear projection at the 8-week trend. Dashed line = forecast, shaded band = confidence.
        </p>
      </Panel>

      {/* Funnel history */}
      <Panel
        title="Funnel evolution"
        action={<Label>Baseline → Wk 12</Label>}
        info="Four snapshots of the same journey — baseline, Wk 4, Wk 8, today."
      >
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {(["baseline", "wk4", "wk8", "wk12"] as const).map((key) => (
            <div key={key}>
              <p className="font-inter cosmic-text-xs font-semibold uppercase tracking-[0.1em] text-[var(--app-faint)]">
                {key === "baseline" ? "Baseline" : key === "wk4" ? "Wk 4" : key === "wk8" ? "Wk 8" : "Wk 12"}
              </p>
              <FunnelBars stages={funnelStages(key)} />
            </div>
          ))}
        </div>
      </Panel>

      {/* Weekly data table */}
      <Panel pad={false} title="Weekly detail">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead>
              <tr className="border-b border-[var(--app-line)]">
                {["Week", "Footfall", "Stop rate", "Walk-ins", "Dwell", "Event"].map((h) => (
                  <th key={h} className="px-5 py-3.5"><Label>{h}</Label></th>
                ))}
              </tr>
            </thead>
            <tbody>
              {WEEKLY_HISTORY.map((w) => (
                <tr key={w.week} className="border-b border-[var(--app-line)] transition-colors hover:bg-[var(--app-card)]">
                  <td className="px-5 py-3.5 font-inter cosmic-text-sm font-semibold font-num text-[var(--app-text)]">{w.week}</td>
                  <td className="px-5 py-3.5 font-inter cosmic-text-sm font-num text-[var(--app-text)]">{w.footfall.toLocaleString("en-US")}</td>
                  <td className="px-5 py-3.5 font-inter cosmic-text-sm font-num text-[var(--app-text)]">{w.stopRate}%</td>
                  <td className="px-5 py-3.5 font-inter cosmic-text-sm font-num text-[var(--app-text)]">{w.walkins}</td>
                  <td className="px-5 py-3.5 font-inter cosmic-text-sm font-num text-[var(--app-text)]">{w.dwell}</td>
                  <td className="px-5 py-3.5 font-inter cosmic-text-xs text-[var(--app-faint)]">{w.event ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{SIMULATED_NOTE} · {PEER_NOTE}</p>
    </div>
  )
}
