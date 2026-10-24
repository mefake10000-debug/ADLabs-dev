import { ArrowRight, BarChart3 } from "lucide-react"
import { Panel, Label, GradePill, Chip, PeerDot, ScreenHeader } from "../ui"
import { BarChart, Sparkline } from "../charts"
import { STORES, DEMOGRAPHICS, SIMULATED_NOTE, PEER_NOTE } from "../../data/dashboard"

const COHORT_STOP = 8.9

export function Compare() {
  const ranked = [...STORES].sort((a, b) => parseFloat(b.stopRate) - parseFloat(a.stopRate))

  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader
        icon={BarChart3}
        eyebrow="Peer cohort"
        title="Compare"
        sub={`Stores ranked by stop rate versus the anonymised luxury cohort (peer ${COHORT_STOP}%).`}
      >
        <Chip tone="gold">{SIMULATED_NOTE}</Chip>
        <PeerDot peer={COHORT_STOP.toString()} />
      </ScreenHeader>

      {/* Ranking table */}
      <Panel
        pad={false}
        info="Ranked by stop rate · 'Vs cohort' = gap to the 8.9% peer median. ≥2pp below = flagged for audit."
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead>
              <tr className="border-b border-[var(--app-line)]">
                {["Rank", "Store", "City", "Stop rate", "vs cohort", "Trend", ""].map((h) => (
                  <th key={h} className="px-5 py-3.5">
                    <Label>{h}</Label>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ranked.map((s, i) => (
                <tr key={s.id} className="border-b border-[var(--app-line)] transition-colors hover:bg-[var(--app-card)]">
                  <td className="px-5 py-4 font-inter cosmic-text-sm font-bold font-num text-[var(--app-faint)]">#{i + 1}</td>
                  <td className="px-5 py-4">
                    <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{s.name}</p>
                    <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{s.city}</p>
                  </td>
                  <td className="px-5 py-4"><GradePill grade={s.grade} /></td>
                  <td className="px-5 py-4 font-inter cosmic-text-sm font-semibold font-num text-[var(--app-text)]">{s.stopRate}</td>
                  <td className="px-5 py-4">
                    {i === 0 ? (
                      <span className="font-inter cosmic-text-xs font-semibold font-num" style={{ color: "var(--app-pos)" }}>+2.5pp</span>
                    ) : i === 1 ? (
                      <span className="font-inter cosmic-text-xs font-semibold font-num" style={{ color: "var(--app-neg)" }}>−2.7pp</span>
                    ) : (
                      <span className="font-inter cosmic-text-xs font-semibold font-num" style={{ color: "var(--app-neg)" }}>−4.8pp</span>
                    )}
                  </td>
                  <td className="px-5 py-4">
                    <Sparkline data={s.spark} tone={s.trend === "up" ? "pos" : s.trend === "down" ? "neg" : "gold"} />
                  </td>
                  <td className="px-5 py-4 text-right text-[var(--app-faint)]"><ArrowRight size={16} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Grouped bar chart: current vs cohort */}
      <Panel
        title="Stop rate comparison"
        action={<Label>vs {COHORT_STOP}% cohort</Label>}
        info="Bar = stop rate vs the 8.9% cohort line (anonymised, 37 stores)."
      >
        <BarChart
          data={[
            { label: "Maison Étoile", value: 11.4 },
            { label: "Beverly Hills", value: 6.2 },
            { label: "Mayfair", value: 4.1 },
            { label: "Cohort", value: COHORT_STOP },
          ]}
          height={200}
          horizontal
        />
      </Panel>

      {/* Demographics comparison */}
      <div className="grid gap-5 xl:grid-cols-[1fr_1.4fr]">
        <Panel title="Cohort ages">
          <div className="flex flex-col gap-2">
            {DEMOGRAPHICS.ages.map((a) => (
              <div key={a.band}>
                <div className="mb-1 flex items-baseline justify-between gap-3">
                  <span className="font-inter cosmic-text-xs text-[var(--app-text)]">{a.band}</span>
                  <span className="font-inter cosmic-text-xs font-semibold font-num text-[var(--app-text)]">{a.pct}%</span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: "var(--app-grid)" }}>
                  <div className="h-full rounded-full" style={{ width: `${a.pct}%`, background: "var(--app-gold)" }} />
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 font-inter cosmic-text-2xs text-[var(--app-faint)]">{DEMOGRAPHICS.note}</p>
        </Panel>
        <Panel title="Store snapshots">
          <div className="flex flex-col gap-4">
            {STORES.map((s) => (
              <div key={s.id} className="rounded-xl border border-[var(--app-line)] p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{s.name}</p>
                    <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{s.city} · Grade {s.grade}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-inter cosmic-text-lg font-bold font-num text-[var(--app-text)]">{s.stopRate}</p>
                    <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">stop rate</p>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-3">
                  <span className="font-inter cosmic-text-xs text-[var(--app-text)]">Footfall {s.footfallToday.toLocaleString("en-US")}</span>
                  <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">·</span>
                  <span className="font-inter cosmic-text-xs text-[var(--app-text)]">Trend {s.trend}</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{SIMULATED_NOTE} · {PEER_NOTE}</p>
    </div>
  )
}
