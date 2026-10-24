import { useState } from "react"
import { TriangleAlert, ShieldAlert, ArrowRight } from "lucide-react"
import { Panel, Label, Chip, ScreenHeader } from "../ui"
import { ALERTS, SIMULATED_NOTE } from "../../data/dashboard"

export function Alerts() {
  const [filter, setFilter] = useState<"all" | "critical" | "high" | "medium" | "low">("all")

  const filtered = filter === "all" ? ALERTS : ALERTS.filter((a) => a.severity === filter)

  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader icon={ShieldAlert} eyebrow="Operations" title="Alerts" sub={`${ALERTS.length} active · sorted by severity.`}>
        <Chip tone="gold">Sample alerts</Chip>
      </ScreenHeader>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2">
        {(["all", "critical", "high", "medium", "low"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full px-3 py-1.5 font-inter cosmic-text-xs font-semibold transition-colors capitalize ${
              filter === f ? "text-[var(--app-card)]" : "text-[var(--app-sub)] border border-[var(--app-line)] hover:text-[var(--app-text)]"
            }`}
            style={filter === f ? { background: "var(--app-text)", color: "var(--app-card)" } : undefined}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        {[
          { label: "Critical", count: ALERTS.filter((a) => a.severity === "critical").length, color: "var(--app-neg)" },
          { label: "High", count: ALERTS.filter((a) => a.severity === "high").length, color: "var(--app-gold)" },
          { label: "Medium", count: ALERTS.filter((a) => a.severity === "medium").length, color: "var(--app-sub)" },
          { label: "Low", count: ALERTS.filter((a) => a.severity === "low").length, color: "var(--app-faint)" },
          { label: "Total", count: ALERTS.length, color: "var(--app-text)" },
        ].map((s) => (
          <Panel key={s.label}>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: s.color }} />
              <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">{s.label}</span>
            </div>
            <p className="mt-2 font-inter cosmic-text-2xl font-bold font-num text-[var(--app-text)]">{s.count}</p>
          </Panel>
        ))}
      </div>

      {/* Alert list */}
      <Panel
        title="Active alerts"
        action={<Label>{filtered.length} shown</Label>}
        info="Severity = revenue impact: critical → walk-ins, high → stop rate, medium/low → dwell."
      >
        <div className="flex flex-col gap-3">
          {filtered.map((a) => (
            <div key={a.id} className="rounded-xl border border-[var(--app-line)] p-4">
              <div className="flex items-start gap-3">
                <span
                  className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full"
                  style={{ background: a.severity === "critical" ? "color-mix(in srgb, var(--app-neg) 12%, transparent)" : a.severity === "high" ? "color-mix(in srgb, var(--app-gold) 12%, transparent)" : "color-mix(in srgb, var(--app-raise), transparent)", color: a.severity === "critical" ? "var(--app-neg)" : a.severity === "high" ? "var(--app-gold)" : "var(--app-sub)" }}
                >
                  <TriangleAlert size={15} strokeWidth={2.3} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{a.zone ?? a.store}</span>
                    <span className="rounded-full px-2 py-0.5 font-inter cosmic-text-2xs font-bold uppercase tracking-[0.08em]" style={{ background: a.severity === "critical" ? "color-mix(in srgb, var(--app-neg) 12%, transparent)" : a.severity === "high" ? "color-mix(in srgb, var(--app-gold) 12%, transparent)" : "color-mix(in srgb, var(--app-raise), transparent)", color: a.severity === "critical" ? "var(--app-neg)" : a.severity === "high" ? "var(--app-gold)" : "var(--app-sub)" }}>
                      {a.severity}
                    </span>
                    <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">{a.time}</span>
                  </div>
                  <p className="mt-1 font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">{a.message}</p>
                  <div className="mt-2 flex items-center gap-3">
                    <span className="font-inter cosmic-text-xs text-[var(--app-gold)]">Action: {a.action}</span>
                    <ArrowRight size={13} strokeWidth={2.1} style={{ color: "var(--app-faint)" }} />
                    <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">{a.screen}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{SIMULATED_NOTE}</p>
    </div>
  )
}
