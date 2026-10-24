import { useState } from "react"
import { Check, Users, ShieldCheck, Video, Clock, TriangleAlert, Flame, CalendarDays, ClipboardList } from "lucide-react"
import { Panel, Label, Chip, ScreenHeader } from "../ui"
import { AreaChart } from "../charts"
import { MANAGER, TRAFFIC_HOURS, ZONES, ALERTS, SIMULATED_NOTE, STAFFING_INTEL, STORE_PERFORMANCE } from "../../data/dashboard"

const LEVEL_STYLE: Record<string, { bg: string; color: string }> = {
  low: { bg: "color-mix(in srgb, var(--app-faint) 10%, transparent)", color: "var(--app-faint)" },
  medium: { bg: "var(--app-gold-soft)", color: "var(--app-gold)" },
  high: { bg: "color-mix(in srgb, var(--app-pos) 12%, transparent)", color: "var(--app-pos)" },
  peak: { bg: "color-mix(in srgb, var(--app-neg) 12%, transparent)", color: "var(--app-neg)" },
}

export function Manager() {
  const [done, setDone] = useState<number[]>([])
  const m = MANAGER
  const flagged = ZONES.filter((z) => z.flag)
  const activeAlerts = ALERTS.filter((a) => a.severity === "critical" || a.severity === "high")
  const sp = STORE_PERFORMANCE

  const toggle = (i: number) => setDone((d) => (d.includes(i) ? d.filter((x) => x !== i) : [...d, i]))

  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader icon={ClipboardList} eyebrow="Store manager view" title="Today" sub={`${m.store} · ${m.date}`}>
        <Chip tone="gold">Sample preview</Chip>
        <Chip tone="gold" title={SIMULATED_NOTE}>Demo</Chip>
      </ScreenHeader>

      {/* Alert banner */}
      <div
        className="flex items-start gap-3 rounded-2xl border p-4"
        style={{ background: "var(--app-gold-soft)", borderColor: "color-mix(in srgb, var(--app-gold) 30%, transparent)" }}
      >
        <Users size={16} className="mt-0.5 shrink-0" style={{ color: "var(--app-gold)" }} />
        <div>
          <p className="font-inter cosmic-text-sm leading-relaxed text-[var(--app-text)]">{m.alert}</p>
          <p className="mt-1 font-inter cosmic-text-xs text-[var(--app-faint)]">
            Example only · not verified on an edge device
          </p>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        {/* Today's curve */}
        <Panel title="Today's curve" action={<Label>PEAK 15:00 – 17:00</Label>}>
          <AreaChart data={TRAFFIC_HOURS} peaks={[{ from: "15", to: "17" }]} height={190} />
          <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--app-line)] pt-3">
            <span className="inline-flex items-center gap-1.5 font-inter cosmic-text-xs text-[var(--app-faint)]">
              <Video size={13} className="text-[var(--app-gold)]" /> Sample traffic series
            </span>
            <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">Counts anonymised · faces never leave device</span>
          </div>
        </Panel>

        {/* Staffing + alerts */}
        <div className="flex flex-col gap-5">
          <Panel title="Staffing plan">
            <div className="flex flex-col gap-3">
              {m.staffing.map((s) => (
                <div key={s.window} className="rounded-xl border border-[var(--app-line)] p-4">
                  <div className="flex items-baseline justify-between">
                    <span className="font-inter cosmic-text-sm font-semibold font-num text-[var(--app-text)]">{s.window}</span>
                    <span className="rounded-full px-2.5 py-0.5 font-inter cosmic-text-xs font-bold" style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>
                      {s.need}
                    </span>
                  </div>
                  <p className="mt-1 font-inter cosmic-text-xs text-[var(--app-faint)]">{s.note}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Active alerts" action={<Label>{activeAlerts.length}</Label>}>
            <div className="flex flex-col gap-2.5">
              {activeAlerts.map((a) => (
                <div key={a.id} className="flex items-start gap-2.5 rounded-xl border border-[var(--app-line)] p-3">
                  <TriangleAlert size={14} className="mt-0.5 shrink-0" style={{ color: "var(--app-neg)" }} />
                  <div className="min-w-0">
                    <p className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">
                      {a.zone ?? a.store} · {a.message}
                    </p>
                    <p className="mt-0.5 font-inter cosmic-text-2xs text-[var(--app-faint)]">Action: {a.action}</p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      {/* Zones image + flag */}
      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Panel title="Floor zones · sample" pad={false}>
          <img
            src="/images/in-store-zones.jpg"
            alt="In-store zones"
            loading="lazy"
            className="aspect-[16/9] w-full rounded-t-2xl object-cover"
          />
          <div className="flex flex-wrap items-center justify-between gap-2 p-5">
            <Label>{ZONES.length} zones tracked</Label>
            <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">
              Copy to keep in view before 15:00 peak
            </span>
          </div>
        </Panel>

        <Panel title="Flagged zones">
          <div className="flex flex-col gap-3">
            {flagged.map((z) => (
              <div key={z.code} className="flex items-start gap-3 rounded-xl border border-[var(--app-line)] p-3.5">
                <span
                  className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full"
                  style={{ background: "color-mix(in srgb, var(--app-neg) 12%, transparent)", color: "var(--app-neg)" }}
                >
                  <TriangleAlert size={13} strokeWidth={2.3} />
                </span>
                <div className="min-w-0">
                  <p className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">Zone {z.code} — {z.name}</p>
                  <p className="mt-0.5 font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">{z.flag}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-2.5 rounded-xl border border-[var(--app-line)] p-3.5">
            <ShieldCheck size={14} className="shrink-0 text-[var(--app-gold)]" strokeWidth={2.2} />
            <p className="font-inter cosmic-text-xs leading-snug text-[var(--app-sub)]">
              Zones data is anonymised aggregation — individual people are never shown, never stored.
            </p>
          </div>
        </Panel>
      </div>

      {/* Staffing intelligence */}
      <Panel
        title="Staffing intelligence · this week"
        action={<Label>1 STAFF / 800 PEAK HOUR</Label>}
        info="Illustrative staffing suggestion based on sample traffic values; not measured staff activity."
      >
        {/* Summary strip */}
        <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-2xl border border-[var(--app-line)] p-3.5">
            <Label>Week grade</Label>
            <div className="mt-2 flex items-baseline gap-2">
              <p className="kpi-value !cosmic-text-2xl text-[var(--app-text)]">{sp.weekGrade}</p>
              <span className="font-inter cosmic-text-xs font-semibold text-[var(--app-pos)]">score {sp.weekScore}/100</span>
            </div>
          </div>
          <div className="rounded-2xl border border-[var(--app-line)] p-3.5">
            <Label>Weekly footfall</Label>
            <p className="kpi-value mt-2 !cosmic-text-2xl text-[var(--app-text)]">{sp.weeklyFootfall.toLocaleString("en-IN")}</p>
          </div>
          <div className="rounded-2xl border border-[var(--app-line)] p-3.5">
            <Label>Revenue signal</Label>
            <p className="kpi-value mt-2 !cosmic-text-2xl" style={{ color: "var(--app-pos)" }}>{sp.revenueSignal}</p>
          </div>
          <div className="rounded-2xl border border-[var(--app-line)] p-3.5">
            <Label>Best day</Label>
            <p className="mt-2 font-inter cosmic-text-base font-bold text-[var(--app-text)]">{sp.bestDay.day}</p>
            <p className="font-inter cosmic-text-2xs text-[var(--app-faint)]">{sp.bestDay.footfall.toLocaleString("en-IN")} footfall</p>
          </div>
        </div>

        {/* Day × staff grid */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead>
              <tr className="border-b border-[var(--app-line)]">
                {["Day", "Footfall", "Staff needed", "Hot hours", "Peak", "Load"].map((h) => (
                  <th key={h} className="px-3 py-2.5"><Label>{h}</Label></th>
                ))}
              </tr>
            </thead>
            <tbody>
              {STAFFING_INTEL.days.map((d) => (
                <tr key={d.day} className="border-b border-[var(--app-line)] transition-colors last:border-0 hover:bg-[var(--app-raise)]">
                  <td className="px-3 py-3 font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{d.day}</td>
                  <td className="px-3 py-3 font-inter cosmic-text-sm font-num text-[var(--app-text)]">{d.footfall.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-3">
                    <span className={"inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-inter cosmic-text-xs font-bold " + (d.day === "Sat" ? "" : "")} style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>
                      <Users size={12} strokeWidth={2.4} />
                      {d.staff} on floor
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-1">
                      {d.hotHours.map((h) => (
                        <span key={h + d.day} className="rounded-full border border-[var(--app-line)] px-2 py-0.5 font-mono cosmic-text-2xs font-bold text-[var(--app-sub)]">{h}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-3 font-mono cosmic-text-xs font-bold text-[var(--app-text)]">{d.peak}</td>
                  <td className="px-3 py-3">
                    <span className="rounded-full px-2.5 py-1 font-inter cosmic-text-2xs font-bold uppercase tracking-[0.06em]" style={LEVEL_STYLE[d.level]}>
                      {d.level}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 flex items-center gap-1.5 font-inter cosmic-text-2xs text-[var(--app-faint)]">
          <Flame size={11} style={{ color: "var(--app-neg)" }} />
          {STAFFING_INTEL.rule}
        </p>
        <div className="mt-3 rounded-2xl border border-[var(--app-line)] p-3.5" style={{ background: "var(--app-gold-soft)" }}>
          <p className="flex items-start gap-2.5 font-inter cosmic-text-xs leading-relaxed text-[var(--app-text)]">
            <CalendarDays size={14} className="mt-0.5 shrink-0" style={{ color: "var(--app-gold)" }} />
            <span><strong>Owner move:</strong> {sp.move}</span>
          </p>
        </div>
      </Panel>

      {/* Checklist */}
      <Panel title="Opening checklist" action={<Label>{done.length}/{m.checklist.length} done</Label>}>
        <ul className="grid gap-2.5 sm:grid-cols-2">
          {m.checklist.map((c, i) => {
            const isDone = done.includes(i)
            return (
              <li key={c}>
                <button
                  onClick={() => toggle(i)}
                  className={`flex w-full items-center gap-3 rounded-xl border p-3.5 text-left transition-colors duration-150 ${
                    isDone ? "opacity-60" : "hover:bg-[var(--app-raise)]"
                  }`}
                  style={{ borderColor: "var(--app-line)" }}
                  aria-pressed={isDone}
                >
                  <span
                    className="grid h-5.5 w-5.5 shrink-0 place-items-center rounded-md border transition-colors duration-150"
                    style={{
                      borderColor: isDone ? "var(--app-gold)" : "var(--app-line-strong)",
                      background: isDone ? "var(--app-gold)" : "transparent",
                    }}
                  >
                    {isDone && <Check size={13} strokeWidth={3} style={{ color: "var(--app-card)" }} />}
                  </span>
                  <span className={`font-inter cosmic-text-sm ${isDone ? "line-through" : ""}`} style={{ color: "var(--app-text)" }}>
                    {c}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
        <p className="mt-4 flex items-center gap-1.5 border-t border-[var(--app-line)] pt-3 font-inter cosmic-text-2xs text-[var(--app-faint)]">
          <Clock size={11} /> Checklist logged locally · synced to Monday Brief at close
        </p>
      </Panel>
    </div>
  )
}
