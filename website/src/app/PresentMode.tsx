import { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight, X } from "lucide-react"
import { KPIS, FUNNEL, CAMPAIGN_VERDICT, BRIEF, ZONES, SIMULATED_NOTE, WEEKLY_HISTORY, DEMOGRAPHICS } from "../data/dashboard"
import { FunnelBars, HeatGrid, LineChart, DonutChart, HBars } from "./charts"
import { Label } from "./ui"

const SLIDES = ["The five numbers", "The funnel", "Did it work?", "Monday Brief", "The floor", "Storefront", "Compare", "History", "Demographics"] as const

export function PresentMode({ theme, onClose }: { theme: "light" | "dark"; onClose: () => void }) {
  const [i, setI] = useState(0)
  const [auto, setAuto] = useState(true)

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
      if (e.key === "ArrowRight") { setI((v) => Math.min(v + 1, SLIDES.length - 1)); setAuto(false) }
      if (e.key === "ArrowLeft") { setI((v) => Math.max(v - 1, 0)); setAuto(false) }
    }
    document.addEventListener("keydown", key)
    return () => document.removeEventListener("keydown", key)
  }, [onClose])

  useEffect(() => {
    if (!auto) return
    const t = setInterval(() => setI((v) => (v + 1) % SLIDES.length), 8000)
    return () => clearInterval(t)
  }, [auto])

  return (
    <div className="app-scope fixed inset-0 z-50 flex flex-col" data-theme={theme} style={{ background: "var(--app-bg)" }}>
      <header className="flex items-center justify-between border-b border-[var(--app-line)] px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="grid h-8 w-8 place-items-center rounded-xl font-inter cosmic-text-sm font-extrabold" style={{ background: theme === "dark" ? "#f5f5f7" : "#16161f", color: theme === "dark" ? "#16161f" : "#fff" }}>
            Ad
          </span>
          <span className="font-inter cosmic-text-sm font-bold text-[var(--app-text)]">AD Labs · Present</span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className="rounded-full px-3 py-1 font-inter cosmic-text-2xs font-bold tracking-[0.08em]"
            style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}
          >
            {SIMULATED_NOTE.toUpperCase()}
          </span>
          <button
            onClick={onClose}
            aria-label="Exit present mode"
            className="grid h-9 w-9 place-items-center rounded-full border border-[var(--app-line)] text-[var(--app-sub)] transition-colors hover:text-[var(--app-text)]"
          >
            <X size={16} />
          </button>
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-14">
        <div className="w-full max-w-5xl">
          {i === 0 && (
            <div>
              <Label>{SLIDES[0]}</Label>
              <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-5">
                {KPIS.week.map((k) => (
                  <div key={k.id} className="rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-5" style={{ boxShadow: "var(--app-shadow)" }}>
                    <Label>{k.label}</Label>
                    <p className="kpi-value mt-2 text-[var(--app-text)]">{k.value}</p>
                    <p className="mt-2 font-inter cosmic-text-xs font-semibold font-num" style={{ color: "var(--app-pos)" }}>{k.delta} · {k.deltaNote}</p>
                  </div>
                ))}
              </div>
              <p className="mt-6 font-inter cosmic-text-sm text-[var(--app-faint)]">{KPIS.week[1].hint}</p>
            </div>
          )}

          {i === 1 && (
            <div>
              <Label>{SLIDES[1]}</Label>
              <div className="mt-6 rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-6 sm:p-8" style={{ boxShadow: "var(--app-shadow)" }}>
                <FunnelBars stages={FUNNEL.week} />
              </div>
              <p className="mt-6 font-inter cosmic-text-sm text-[var(--app-faint)]">
                Example journey only — pass, stop, enter, explore, engage. These values are not measured from a connected store.
              </p>
            </div>
          )}

          {i === 2 && (
            <div>
              <Label>{SLIDES[2]}</Label>
              <p className="mt-6 max-w-3xl font-inter cosmic-text-xl font-semibold leading-snug text-[var(--app-text)] sm:cosmic-text-2xl">
                "{CAMPAIGN_VERDICT}"
              </p>
              <div className="mt-8 flex gap-3">
                <span className="rounded-full px-4 py-2 font-inter cosmic-text-xs font-bold font-num" style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>6.4% → 7.3% capture</span>
                <span className="rounded-full px-4 py-2 font-inter cosmic-text-xs font-bold font-num" style={{ background: "color-mix(in srgb, var(--app-pos) 12%, transparent)", color: "var(--app-pos)" }}>+14.6% example uplift · sample A/B</span>
              </div>
            </div>
          )}

          {i === 3 && (
            <div>
              <Label>{SLIDES[3]} · {BRIEF.week}</Label>
              <p className="mt-6 max-w-3xl font-inter cosmic-text-lg leading-relaxed text-[var(--app-text)] sm:cosmic-text-xl">{BRIEF.verdict}</p>
              <ol className="mt-8 flex flex-col gap-3">
                {BRIEF.actions.map((a, idx) => (
                  <li key={a.title} className="flex items-start gap-4 rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-4">
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full font-inter cosmic-text-xs font-bold" style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>{idx + 1}</span>
                    <div>
                      <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{a.title}</p>
                      <p className="mt-1 font-inter cosmic-text-xs text-[var(--app-faint)]">{a.priority} · {a.tag}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {i === 4 && (
            <div>
              <Label>{SLIDES[4]}</Label>
              <div className="mt-6 rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-6 sm:p-8" style={{ boxShadow: "var(--app-shadow)" }}>
                <HeatGrid zones={ZONES} />
              </div>
              <p className="mt-6 font-inter cosmic-text-sm text-[var(--app-faint)]">
                Ten zones · traffic share · red dot = flagged for attention this week.
              </p>
            </div>
          )}

          {i === 5 && (
            <div>
              <Label>{SLIDES[5]}</Label>
              <p className="mt-6 max-w-3xl font-inter cosmic-text-base leading-relaxed text-[var(--app-text)] sm:cosmic-text-xl">
                Capture rate is tracking toward 12.0% by Wk 16, powered by the Wk 4 rotation and the hero sash. Zone F1 remains the weakest link.
              </p>
              <div className="mt-6 rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-6 sm:p-8" style={{ boxShadow: "var(--app-shadow)" }}>
                <LineChart
                  data={WEEKLY_HISTORY.map((w) => ({ week: w.week, value: w.stopRate }))}
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
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3">
                <div className="rounded-xl border border-[var(--app-line)] bg-[var(--app-card)] p-4">
                  <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">Stop rate</p>
                  <p className="mt-1 font-inter cosmic-text-xl font-bold font-num text-[var(--app-text)]">11.4%</p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] bg-[var(--app-card)] p-4">
                  <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">Walk-ins</p>
                  <p className="mt-1 font-inter cosmic-text-xl font-bold font-num text-[var(--app-text)]">391</p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] bg-[var(--app-card)] p-4">
                  <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">Dwell</p>
                  <p className="mt-1 font-inter cosmic-text-xl font-bold font-num text-[var(--app-text)]">6m 12s</p>
                </div>
              </div>
            </div>
          )}

          {i === 6 && (
            <div>
              <Label>{SLIDES[6]}</Label>
              <p className="mt-6 max-w-3xl font-inter cosmic-text-base leading-relaxed text-[var(--app-text)] sm:cosmic-text-xl">
                Maison Étoile leads the cohort at 11.4% stop rate — 2.5pp above the luxury benchmark. Mayfair Salon at 4.1% needs intervention.
              </p>
              <div className="mt-6 rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-6 sm:p-8" style={{ boxShadow: "var(--app-shadow)" }}>
                <HBars items={[
                  { label: "Maison Étoile", pct: 11.4, sub: "Grade A · New York" },
                  { label: "Beverly Hills Boutique", pct: 6.2, sub: "Grade B · Los Angeles" },
                  { label: "Mayfair Salon", pct: 4.1, sub: "Grade C · London" },
                  { label: "Cohort median", pct: 8.9, sub: "Anonymised luxury" },
                ]} />
              </div>
              <div className="mt-4 rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-4">
                <p className="font-inter cosmic-text-xs text-[var(--app-sub)]">3 stores · Grade A/B/C · peer {8.9}% cohort benchmark</p>
              </div>
            </div>
          )}

          {i === 7 && (
            <div>
              <Label>{SLIDES[7]}</Label>
              <p className="mt-6 max-w-3xl font-inter cosmic-text-base leading-relaxed text-[var(--app-text)] sm:cosmic-text-xl">
                Stop rate climbed from 9.2% (W1) to 11.4% (Wk 12). Two window events drove step changes — and the trend continues upward.
              </p>
              <div className="mt-6 rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-6 sm:p-8" style={{ boxShadow: "var(--app-shadow)" }}>
                <LineChart
                  data={WEEKLY_HISTORY.map((w) => ({ week: w.week, value: w.stopRate }))}
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
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-[var(--app-line)] bg-[var(--app-card)] p-4">
                  <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">Wk 4 event</p>
                  <p className="mt-1 font-inter cosmic-text-base font-bold font-num text-[var(--app-gold)]">Winter Rotation</p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] bg-[var(--app-card)] p-4">
                  <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">Wk 8 event</p>
                  <p className="mt-1 font-inter cosmic-text-base font-bold font-num text-[var(--app-gold)]">Hero Sash</p>
                </div>
              </div>
            </div>
          )}

          {i === 8 && (
            <div>
              <Label>{SLIDES[8]}</Label>
              <p className="mt-6 max-w-3xl font-inter cosmic-text-base leading-relaxed text-[var(--app-text)] sm:cosmic-text-xl">
                28–44 year-olds drive 62% of attention. Solo visitors (58%) outpace pairs. Peak window is 16:30–18:45 across all days.
              </p>
              <div className="mt-6 grid gap-5 xl:grid-cols-[1fr_1fr]">
                <div className="rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-6 sm:p-8" style={{ boxShadow: "var(--app-shadow)" }}>
                  <DonutChart
                    data={[
                      { label: "Solo", pct: DEMOGRAPHICS.dynamics.solo },
                      { label: "Pair", pct: DEMOGRAPHICS.dynamics.pair },
                    ]}
                    size={140}
                  />
                  <p className="mt-4 font-inter cosmic-text-xs text-[var(--app-faint)]">Group composition</p>
                </div>
                <div className="rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-6 sm:p-8" style={{ boxShadow: "var(--app-shadow)" }}>
                  <HBars items={DEMOGRAPHICS.ages.map((a) => ({ label: a.band, pct: a.pct }))} />
                  <p className="mt-4 font-inter cosmic-text-xs text-[var(--app-faint)]">{DEMOGRAPHICS.note}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <footer className="flex items-center justify-between border-t border-[var(--app-line)] px-6 py-4">
        <div className="flex items-center gap-2">
          {SLIDES.map((s, idx) => (
            <button
              key={s}
              onClick={() => { setI(idx); setAuto(false) }}
              aria-label={`Slide ${idx + 1}: ${s}`}
              className="h-1.5 rounded-full transition-all duration-200"
              style={{
                width: idx === i ? 28 : 10,
                background: idx === i ? "var(--app-gold)" : "var(--app-line-strong)",
              }}
            />
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="mr-2 font-inter cosmic-text-xs font-medium font-num text-[var(--app-faint)]">
            {i + 1} / {SLIDES.length} {auto ? "· auto" : ""}
          </span>
          <button
            onClick={() => { setI((v) => Math.max(v - 1, 0)); setAuto(false) }}
            aria-label="Previous slide"
            className="grid h-9 w-9 place-items-center rounded-full border border-[var(--app-line)] text-[var(--app-sub)] transition-colors hover:text-[var(--app-text)]"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => { setI((v) => Math.min(v + 1, SLIDES.length - 1)); setAuto(false) }}
            aria-label="Next slide"
            className="grid h-9 w-9 place-items-center rounded-full border border-[var(--app-line)] text-[var(--app-sub)] transition-colors hover:text-[var(--app-text)]"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </footer>
    </div>
  )
}
