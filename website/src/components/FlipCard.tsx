import { useState, type CSSProperties, type KeyboardEvent, type ReactNode } from "react"
import type { MiniViz } from "../data/site"

export function FlipCard({
  front,
  back,
  className = "",
  style,
}: {
  front: ReactNode
  back: ReactNode
  className?: string
  style?: CSSProperties
}) {
  const [flipped, setFlipped] = useState(false)

  const onKey = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      setFlipped((v) => !v)
    }
  }

  return (
    <article
      className={`flip-card group relative h-full min-h-[280px] ${className}`}
      style={style}
      role="button"
      aria-pressed={flipped}
      tabIndex={0}
      data-flipped={flipped}
      onClick={() => {
        if (typeof window !== "undefined" && window.matchMedia("(hover: none)").matches) {
          setFlipped((v) => !v)
        }
      }}
      onKeyDown={onKey}
    >
      <div className="flip-inner relative h-full w-full" style={{ transformStyle: "preserve-3d" }}>
        <div className="flip-face flip-front">{front}</div>
        <div className="flip-face flip-back">{back}</div>
      </div>
    </article>
  )
}

function SignalBit({ viz }: { viz: MiniViz }) {
  if (viz.kind === "donut") {
    const v = viz.value ?? 50
    return (
      <svg viewBox="0 0 100 34" className="h-7 w-full" aria-hidden>
        <circle
          cx={50}
          cy={17}
          r={11}
          fill="none"
          stroke="rgba(0,0,0,0.08)"
          strokeWidth={6}
          strokeLinecap="round"
          pathLength={100}
          strokeDasharray={100}
        />
        <circle
          cx={50}
          cy={17}
          r={11}
          fill="none"
          stroke="#8B7CF6"
          strokeWidth={6}
          strokeLinecap="round"
          pathLength={100}
          strokeDasharray={100}
          className="ring-in"
          style={{ "--ring-end": `${100 - v}`, strokeDashoffset: 100 } as CSSProperties}
        />
        <text x="66" y="21" fontSize="7" fontFamily="monospace" letterSpacing="0.14em" fill="#86868b">
          {v > 50 ? "HIGH" : "MEASURED"}
        </text>
      </svg>
    )
  }
  if (viz.kind === "bars") {
    const d = viz.data ?? []
    const max = Math.max(...d, 1)
    return (
      <div className="flex h-7 w-full items-end gap-[3px]">
        {d.map((v, i) => (
          <div
            key={i}
            className="grow-y flex-1 rounded-t-[2px]"
            style={
              {
                height: `${(v / max) * 100}%`,
                background: i === d.length - 1 ? "#8B7CF6" : "rgba(139,124,246,0.25)",
                animationDelay: `${i * 40}ms`,
              } as CSSProperties
            }
          />
        ))}
      </div>
    )
  }
  const d = viz.data ?? [1, 2, 3]
  const w = 96
  const h = 30
  const min = Math.min(...d)
  const max = Math.max(...d)
  const span = max - min || 1
  const pts = d
    .map(
      (v, i) =>
        `${((i / (d.length - 1)) * w).toFixed(1)},${(h - 4 - ((v - min) / span) * (h - 8)).toFixed(1)}`,
    )
    .join(" ")
  const line = (
    <polyline
      points={pts}
      fill="none"
      stroke="#8B7CF6"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeDasharray="999"
      className="animate-draw-line"
      style={{ strokeDashoffset: 999 }}
    />
  )
  if (viz.kind === "area") {
    const area = `${w},${h} ${pts} 0,${h}`
    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="h-7 w-full" aria-hidden>
        <polygon points={area} fill="rgba(139,124,246,0.15)" />
        {line}
      </svg>
    )
  }
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-7 w-full" aria-hidden>
      {line}
    </svg>
  )
}

export function AnswerPanel({
  eyebrow,
  stats,
  viz,
  chips,
  note,
}: {
  eyebrow: string
  stats?: { value: string; label: string }[]
  viz?: MiniViz
  chips?: string[]
  note: string
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col p-6 bg-[#1a1a24] border border-white/10 rounded-3xl">
      <div className="flex items-center justify-between">
        <span className="cosmic-text-2xs font-semibold uppercase tracking-[0.08em] text-[#8B7CF6]">{eyebrow}</span>
        <span className="h-1.5 w-1.5 rounded-full bg-[#8B7CF6]" />
      </div>
      {stats && (
        <div className="mt-4 flex flex-wrap items-baseline gap-x-4 gap-y-1">
          {stats.map((s) => (
            <div key={s.label}>
              <span className="cosmic-text-2xl font-bold leading-none text-[#f5f5f7]">{s.value}</span>
              <span className="ml-1.5 cosmic-text-2xs font-medium uppercase tracking-normal text-[#86868b]">
                {s.label}
              </span>
            </div>
          ))}
        </div>
      )}
      {viz && (
        <div className="mt-4 flex min-h-0 flex-1 flex-col justify-center">
          <SignalBit viz={viz} />
        </div>
      )}
      {chips && (
        <div className="mb-3 mt-4 flex flex-wrap gap-2">
          {chips.map((c) => (
            <span
              key={c}
              className="rounded-full border border-[#8B7CF6]/30 bg-[rgba(139,124,246,0.08)] px-3 py-1 cosmic-text-2xs font-semibold tracking-normal text-[#8B7CF6]"
            >
              {c}
            </span>
          ))}
        </div>
      )}
      <p className="border-t border-white/10 pt-4 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{note}</p>
    </div>
  )
}
