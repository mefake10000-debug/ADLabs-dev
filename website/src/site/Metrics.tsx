import { Reveal } from "../components/Reveal"
import { SectionHeader } from "../components/SectionHeader"
import { METRICS } from "../data/site"

/* ------------------------------------------------------------
   Tiny sparkline primitives
------------------------------------------------------------ */
function SparkPath({ data, stroke, fill, height = 56 }: { data: number[]; stroke: string; fill?: string; height?: number }) {
  const w = 100
  const max = Math.max(...data) * 1.15
  const min = Math.min(...data) * 0.85
  const pts = data.map((d, i) => `${(i / (data.length - 1)) * w},${height - ((d - min) / (max - min)) * (height - 6) - 3}`)
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" style={{ height }} aria-hidden>
      {fill && (
        <polygon points={`0,${height} ${pts.join(" ")} ${w},${height}`} fill={fill} opacity="0.08" />
      )}
      <polyline points={pts.join(" ")} fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function MiniBars({ data, stroke }: { data: number[]; stroke: string }) {
  const max = Math.max(...data)
  const w = 100
  const h = 56
  const bw = w / data.length
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: h }} aria-hidden>
      {data.map((d, i) => (
        <rect key={i} x={i * bw + 2} y={(1 - d / max) * h} width={bw - 4} height={(d / max) * h} rx={2} fill={stroke} opacity={0.35 + 0.5 * (i / (data.length - 1))} />
      ))}
    </svg>
  )
}

function MiniDonut({ value, stroke, label }: { value: number; stroke: string; label: string }) {
  const r = 26
  const c = 2 * Math.PI * r
  const pct = Math.min(value, 100)
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 72 72" style={{ width: 56, height: 56 }} aria-hidden>
        <circle cx="36" cy="36" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="7" />
        <circle
          cx="36" cy="36" r={r} fill="none" stroke={stroke} strokeWidth="7" strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * c} ${c}`} transform="rotate(-90 36 36)"
        />
      </svg>
      <div>
        <p className="cosmic-text-xl font-bold leading-none text-[#f5f5f7]">{value}%</p>
        <p className="mt-1 cosmic-text-xs text-[#86868b]">{label}</p>
      </div>
    </div>
  )
}

function MiniGauge({ value, max, stroke }: { value: number; max: number; stroke: string }) {
  const pct = Math.min((value / max) * 100, 100)
  const r = 26
  const c = 2 * Math.PI * r
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 72 72" style={{ width: 56, height: 56 }} aria-hidden>
        <circle cx="36" cy="36" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="7" />
        <circle
          cx="36" cy="36" r={r} fill="none" stroke={stroke} strokeWidth="7" strokeLinecap="round" strokeDasharray={`${(pct / 100) * c} ${c}`} transform="rotate(-90 36 36)"
        />
        <text x="36" y="40" textAnchor="middle" fontSize="15" fontWeight="700" fill="#f5f5f7">{value} m/s</text>
      </svg>
      <p className="cosmic-text-xs text-[#86868b]">deceleration<br />floor {max} m/s</p>
    </div>
  )
}

function MiniSplit({ parts, stroke }: { parts: { label: string; value: number }[]; stroke: string }) {
  const total = parts.reduce((a, b) => a + b.value, 0)
  return (
    <div className="flex items-end gap-4">
      <div className="h-[60px] w-[60px] overflow-hidden rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
        {parts.map((p) => (
          <div key={p.label} style={{ width: `${(p.value / total) * 100}%`, height: "100%", display: "inline-block", background: stroke, opacity: 0.4 + (p.value / total) }} />
        ))}
      </div>
      <div>
        {parts.map((p) => (
          <p key={p.label} className="cosmic-text-xs text-[#a1a1aa]">
            <span className="font-bold text-[#f5f5f7]">{p.value}%</span> {p.label}
          </p>
        ))}
      </div>
    </div>
  )
}

function MiniHours({ hours, stroke }: { hours: number[]; stroke: string }) {
  const max = Math.max(...hours)
  return (
    <div className="flex h-[60px] items-end gap-[3px]">
      {hours.map((h, i) => (
        <div key={i} className="flex-1 rounded-sm" style={{ height: `${(h / max) * 100}%`, background: stroke, opacity: 0.25 + 0.65 * (h / max) }} />
      ))}
    </div>
  )
}

/* ------------------------------------------------------------
   Metric card — renders the full data that already exists
------------------------------------------------------------ */
function MetricCard({ it }: { it: (typeof METRICS.items)[number] }) {
  const accent = "#8B7CF6"
  const viz = (() => {
    switch (it.viz) {
      case "donut":
        return <MiniDonut value={it.value ?? 0} stroke={accent} label={it.title} />
      case "gauge":
        return <MiniGauge value={it.value ?? 0} max={it.max ?? 1} stroke={accent} />
      case "area":
        return <SparkPath data={it.spark} stroke={accent} fill={accent} />
      case "bars":
        return <MiniBars data={it.spark} stroke={accent} />
      case "split":
        return <MiniSplit parts={it.parts ?? []} stroke={accent} />
      case "hours":
        return <MiniHours hours={it.hours ?? []} stroke={accent} />
      default:
        return <SparkPath data={it.spark} stroke={accent} />
    }
  })()

  return (
    <article className="site-card group relative flex min-h-[240px] flex-col p-6">
      <div className="flex items-baseline justify-between">
        <h3 className="cosmic-text-lg font-semibold leading-tight text-[#f5f5f7]">{it.title}</h3>
        <span className="cosmic-text-xs font-medium text-[#86868b]">{it.stat}</span>
      </div>
      <p className="mt-2 flex-1 cosmic-text-xs leading-relaxed text-[#a1a1aa]">{it.desc}</p>
      <div className="mt-4">{viz}</div>
      <div className="mt-4 flex items-center justify-between border-t border-white/8 pt-3">
        <span className={`cosmic-text-xs font-semibold ${it.deltaTone === "pos" ? "text-[#8B7CF6]" : it.deltaTone === "neg" ? "text-[#ff453a]" : "text-[#86868b]"}`}>
          {it.delta}
        </span>
        <span className="cosmic-text-2xs text-[#86868b]">{it.hint}</span>
      </div>

      {/* Hover reveal — the "why" */}
      <div className="absolute inset-0 z-10 flex flex-col justify-center bg-[#12121a]/95 p-6 opacity-0 backdrop-blur-sm transition-all duration-400 group-hover:opacity-100">
        <span className="font-mono cosmic-text-2xs uppercase tracking-[0.2em] text-[#8B7CF6]">Why it matters</span>
        <p className="mt-3 cosmic-text-sm leading-relaxed text-[#f5f5f7]">{it.why}</p>
      </div>
    </article>
  )
}

export function Metrics() {
  const m = METRICS
  return (
    <section id="metrics" className="relative scroll-mt-24 overflow-hidden bg-[#0c0c14] py-12 sm:py-16 lg:py-20">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <img src="/images/sector-beauty.jpg" alt="" className="w-full h-full object-cover opacity-[0.05]" />
        <div className="absolute inset-0" style={{ background: "var(--cosmic-gradient-void)" }} />
      </div>
      <div className="relative z-10 mx-auto max-w-[1200px] px-6">
        <SectionHeader index={m.index} kicker={m.kicker} sub={m.sub}>
          {m.h2}
        </SectionHeader>

        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {m.items.map((it, i) => (
            <Reveal key={it.title} delay={Math.min(i * 0.04, 0.3)}>
              <MetricCard it={it} />
            </Reveal>
          ))}
        </div>

        <p className="mt-6 max-w-2xl cosmic-text-xs leading-relaxed text-[#86868b]">
          <span className="mr-2 inline-block h-3 w-px translate-y-0.5 bg-[#8B7CF6]/60" />
          {m.note}
        </p>
      </div>
    </section>
  )
}
