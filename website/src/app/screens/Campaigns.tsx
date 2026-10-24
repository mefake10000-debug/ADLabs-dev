import { BadgeCheck, ShieldCheck, Target } from "lucide-react"
import { Panel, Label, Chip, ScreenHeader } from "../ui"
import { CAMPAIGNS, CAMPAIGN_TIMELINE, CAMPAIGN_VERDICT } from "../../data/dashboard"

export function Campaigns() {
  const w = 640
  const h = 200
  const padB = 26
  const vals = CAMPAIGN_TIMELINE.map((d) => d.stop)
  const min = Math.min(...vals) - 0.6
  const max = Math.max(...vals) + 0.4
  const x = (i: number) => (i / (CAMPAIGN_TIMELINE.length - 1)) * w
  const y = (v: number) => h - padB - ((v - min) / (max - min)) * (h - padB - 14)
  const pts = CAMPAIGN_TIMELINE.map((d, i) => `${x(i).toFixed(1)},${y(d.stop).toFixed(1)}`)
  const path = `M ${pts.join(" L ")}`

  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader icon={Target} eyebrow="Physical A/B" title="Campaigns" sub="Physical A/B: what you changed in the window — and what the street did next.">
        <Chip tone="gold">Sample scenario · 12 weeks</Chip>
      </ScreenHeader>

      <Panel title="Stop rate · W1 → W12" action={<Label>WINDOW EVENTS MARKED</Label>}>
        <svg viewBox={`0 0 ${w} ${h}`} className="h-auto w-full" role="img" aria-label="Stop rate across 12 weeks">
          {[0.25, 0.5, 0.75].map((f) => (
            <line
              key={f}
              x1={0}
              x2={w}
              y1={14 + f * (h - padB - 14)}
              y2={14 + f * (h - padB - 14)}
              stroke="var(--app-grid)"
              vectorEffect="non-scaling-stroke"
            />
          ))}
          <path d={path} fill="none" stroke="var(--app-gold)" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
          {CAMPAIGN_TIMELINE.map((d, i) => {
            const ev = d.event ? (
              <g key={d.week}>
                <line
                  x1={x(i)}
                  x2={x(i)}
                  y1={14}
                  y2={h - padB}
                  stroke="var(--app-line-strong)"
                  strokeDasharray="3 4"
                  vectorEffect="non-scaling-stroke"
                />
                <rect x={x(i) - 26} y={2} width={52} height={16} rx={8} fill="var(--app-gold-soft)" />
                <text x={x(i)} y={13.5} textAnchor="middle" fontSize={8.5} fill="var(--app-gold)" className="font-inter" fontWeight={700}>
                  {d.week}
                </text>
              </g>
            ) : null
            return (
              <g key={d.week}>
                {ev}
                <circle cx={x(i)} cy={y(d.stop)} r={d.event ? 4.4 : 2.8} fill={d.event ? "var(--app-gold)" : "var(--app-card)"} stroke="var(--app-gold)" strokeWidth={d.event ? 0 : 1.6} />
                <title>{`${d.week} — stop rate ${d.stop}%${d.event ? ` · ${d.event}` : ""}`}</title>
              </g>
            )
          })}
          {CAMPAIGN_TIMELINE.map((d, i) =>
            i % 2 === 0 ? (
              <text key={d.week} x={x(i)} y={h - 8} textAnchor="middle" fontSize={10} fill="var(--app-faint)" className="font-inter">
                {d.week}
              </text>
            ) : null,
          )}
        </svg>
      </Panel>

      {/* Explain intended flow without implying this sample is connected to a camera. */}
      <Panel title="Example video-to-measurement flow" action={<Label>Illustrative · not connected</Label>}>
        <div className="grid gap-3 sm:grid-cols-4">
          {[
            { step: "01", title: "Select a source", desc: "An operator chooses an authorized camera or video for a processing session." },
            { step: "02", title: "Measure on the edge", desc: "The configured pipeline can produce supported counts and zone events while processing is running." },
            { step: "03", title: "Check the evidence", desc: "Review the real session, camera, timestamp, model health, and data freshness before interpreting metrics." },
            { step: "04", title: "Use a sample result", desc: "The percentages and campaign figures on this page are illustrative examples, not results from a connected store." },
          ].map((s) => (
            <div key={s.step} className="relative rounded-2xl border border-[var(--app-line)] p-4">
              <span className="font-mono cosmic-text-xs font-bold text-[var(--app-gold)]">{s.step}</span>
              <h3 className="mt-1.5 font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{s.title}</h3>
              <p className="mt-1 font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">{s.desc}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-2.5 rounded-xl border border-[var(--app-line)] p-3.5">
          <ShieldCheck size={14} className="shrink-0 text-[var(--app-gold)]" strokeWidth={2.2} />
          <p className="font-inter cosmic-text-xs leading-snug text-[var(--app-sub)]">
            This page is a static product preview. It is not connected to camera footage, POS data, or an edge device.
          </p>
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        {CAMPAIGNS.map((c) => (
          <Panel key={c.id} pad={false}>
            <div className="flex items-center justify-between gap-3 p-5 pb-0 sm:p-6 sm:pb-0">
              <div>
                <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{c.name}</p>
                <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">
                  {c.week} · {c.type} · {c.window}
                </p>
              </div>
              {c.verified && (
                <span
                  className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-inter cosmic-text-2xs font-bold"
                  style={{ background: "color-mix(in srgb, var(--app-pos) 12%, transparent)", color: "var(--app-pos)" }}
                >
                  <BadgeCheck size={11} strokeWidth={2.6} />
                  SAMPLE
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-px p-5 sm:p-6" style={{ background: "var(--app-line)" }}>
              <figure className="rounded-xl border border-[var(--app-line)]" style={{ background: "var(--app-card)" }}>
                <img src={c.imageBefore} alt={`${c.name} before`} loading="lazy" className="aspect-[4/3] w-full rounded-t-xl object-cover grayscale-[30%]" />
                <figcaption className="p-3.5">
                  <Label>Before</Label>
                  <p className="mt-1 font-inter text-xl font-bold font-num text-[var(--app-sub)]">{c.before}</p>
                </figcaption>
              </figure>
              <figure className="rounded-xl border border-[var(--app-line-strong)]" style={{ background: "var(--app-card)" }}>
                <img src={c.imageAfter} alt={`${c.name} after`} loading="lazy" className="aspect-[4/3] w-full rounded-t-xl object-cover" />
                <figcaption className="p-3.5">
                  <Label>After</Label>
                  <p className="mt-1 font-inter text-xl font-bold font-num text-[var(--app-text)]">{c.after}</p>
                </figcaption>
              </figure>
            </div>
            <div className="flex items-center justify-between gap-3 border-t border-[var(--app-line)] p-5 sm:p-6">
              <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">{c.metricLabel}</span>
              <span className="font-inter cosmic-text-sm font-bold font-num" style={{ color: "var(--app-pos)" }}>
                {c.uplift}
              </span>
            </div>
          </Panel>
        ))}
      </div>

      <Panel
        title="Verdict"
        action={
          <span
            className="rounded-full px-2.5 py-1 font-inter cosmic-text-2xs font-bold"
            style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}
          >
            EXAMPLE RECOMMENDATION
          </span>
        }
      >
        <p className="font-inter cosmic-text-base leading-relaxed text-[var(--app-text)]">{CAMPAIGN_VERDICT}</p>
      </Panel>
    </div>
  )
}
