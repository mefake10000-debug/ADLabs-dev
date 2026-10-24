export function Sparkline({ data, tone = "gold" }: { data: number[]; tone?: "gold" | "pos" | "neg" }) {
  const w = 120
  const h = 34
  const min = Math.min(...data)
  const max = Math.max(...data)
  const span = max - min || 1
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - 3 - ((d - min) / span) * (h - 6)
    return { x: +x.toFixed(1), y: +y.toFixed(1) }
  })
  const color = tone === "pos" ? "var(--app-pos)" : tone === "neg" ? "var(--app-neg)" : "var(--app-gold)"
  const gradId = `spark-${tone}-${data.length}`
  const last = pts[pts.length - 1]
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible" aria-hidden>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.18} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polygon
        points={pts.map((p) => `${p.x},${p.y}`).join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={0}
      />
      <path
        d={`M ${pts.map((p) => `${p.x},${p.y}`).join(" L ")} L ${last.x},${h} L ${pts[0].x},${h} Z`}
        fill={`url(#${gradId})`}
      />
      <polyline
        points={pts.map((p) => `${p.x},${p.y}`).join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={last.x} cy={last.y} r={2.6} fill={color} />
    </svg>
  )
}

export function AreaChart({
  data,
  peaks,
  height = 210,
}: {
  data: { h: string; v: number }[]
  peaks?: { from: string; to: string }[]
  height?: number
}) {
  const w = 660
  const h = height
  const padB = 26
  const max = Math.max(...data.map((d) => d.v)) * 1.15
  const x = (i: number) => (i / (data.length - 1)) * w
  const y = (v: number) => h - padB - (v / max) * (h - padB - 12)

  const pts = data.map((d, i) => [x(i), y(d.v)] as const)
  let path = `M ${pts[0][0]},${pts[0][1]}`
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i]
    const [x1, y1] = pts[i + 1]
    const mx = (x0 + x1) / 2
    path += ` C ${mx},${y0} ${mx},${y1} ${x1},${y1}`
  }
  const area = `${path} L ${w},${h - padB} L 0,${h - padB} Z`

  const peakRects = (peaks ?? []).map((p) => {
    const i0 = data.findIndex((d) => d.h === p.from)
    const i1 = data.findIndex((d) => d.h === p.to)
    if (i0 < 0 || i1 < 0) return null
    return (
      <rect
        key={p.from + p.to}
        x={x(i0)}
        y={10}
        width={x(i1) - x(i0)}
        height={h - padB - 10}
        fill="var(--app-gold-soft)"
      />
    )
  })

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="h-auto w-full"
      role="img"
      aria-label="Street footfall by hour"
    >
      <defs>
        <linearGradient id="areaGold" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--app-gold)" stopOpacity={0.28} />
          <stop offset="80%" stopColor="var(--app-gold)" stopOpacity={0.04} />
          <stop offset="100%" stopColor="var(--app-gold)" stopOpacity={0} />
        </linearGradient>
        <filter id="areaBlur" x="-5%" y="-5%" width="110%" height="110%">
          <feGaussianBlur stdDeviation="2" />
        </filter>
      </defs>
      {[0.25, 0.5, 0.75].map((f) => (
        <line
          key={f}
          x1={0}
          x2={w}
          y1={10 + f * (h - padB - 10)}
          y2={10 + f * (h - padB - 10)}
          stroke="var(--app-grid)"
          strokeWidth={0.8}
          vectorEffect="non-scaling-stroke"
          opacity={0.7}
        />
      ))}
      {peakRects}
      <path d={area} fill="url(#areaGold)" />
      <path
        d={path}
        fill="none"
        stroke="var(--app-gold)"
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      {data.map((d, i) => (
        <g key={d.h}>
          <circle cx={x(i)} cy={y(d.v)} r={3} fill="var(--app-card)" stroke="var(--app-gold)" strokeWidth={1.6} />
          <circle cx={x(i)} cy={y(d.v)} r={1.2} fill="var(--app-gold)" />
          <title>{`${d.h}:00 — ${d.v.toLocaleString("en-US")} passers-by`}</title>
        </g>
      ))}
      {[0, 3, 6, 9, 12].map((i) => (
        <text
          key={i}
          x={x(i)}
          y={h - 8}
          textAnchor={i === 0 ? "start" : i === 12 ? "end" : "middle"}
          fontSize={10}
          fill="var(--app-faint)"
          className="font-inter"
        >
          {data[i].h}:00
        </text>
      ))}
    </svg>
  )
}

export function LineChart({
  data,
  height = 200,
  peaks,
  prediction,
  showConfidence = true,
}: {
  data: { week: string; value: number }[]
  height?: number
  peaks?: { week: string; label: string }[]
  prediction?: { startIdx: number; points: { week: string; value: number }[] }
  showConfidence?: boolean
}) {
  const w = 660
  const h = height
  const padB = 28
  const padL = 52
  const padR = 16
  const plotW = w - padL - padR
  const allVals = [...data.map((d) => d.value)]
  if (prediction) {
    prediction.points.forEach((p) => allVals.push(p.value))
  }
  const max = Math.max(...allVals) * 1.12
  const min = Math.min(...allVals) * 0.88
  const range = max - min || 1
  const x = (i: number) => padL + (i / (data.length - 1)) * plotW
  const y = (v: number) => h - padB - ((v - min) / range) * (h - padB - 12)

  const pts = data.map((d, i) => `${x(i).toFixed(1)},${y(d.value).toFixed(1)}`)
  const path = `M ${pts.join(" L ")}`
  const area = `${path} L ${x(data.length - 1).toFixed(1)},${h - padB} L ${padL},${h - padB} Z`

  const predictionPts = prediction?.points.map((p, i) => {
    const idx = data.length + i
    return `${x(idx).toFixed(1)},${y(p.value).toFixed(1)}`
  }) ?? []
  const predPath = predictionPts.length > 0 ? `M ${predictionPts[0]} L ${predictionPts.slice(1).join(" L ")}` : ""

  const confidenceBand =
    showConfidence && prediction
      ? prediction.points.map((p, i) => {
          const idx = data.length + i
          const spread = (max - min) * 0.08 * (1 - i / prediction.points.length)
          return `${x(idx).toFixed(1)},${y(p.value + spread).toFixed(1)} ${x(idx).toFixed(1)},${y(p.value - spread).toFixed(1)}`
        }).join(" ")
      : ""

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-auto w-full" role="img" aria-label="Trend line chart">
      {[0.25, 0.5, 0.75].map((f) => {
        const val = min + f * range
        return (
          <g key={f}>
            <line
              x1={padL}
              x2={w - padR}
              y1={y(val)}
              y2={y(val)}
              stroke="var(--app-grid)"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
            <text
              x={padL - 6}
              y={y(val) + 4}
              textAnchor="end"
              fontSize={9}
              fill="var(--app-faint)"
              className="font-mono"
            >
              {val.toFixed(1)}
            </text>
          </g>
        )
      })}
      {data.map((d, i) => (
        <text
          key={d.week}
          x={x(i)}
          y={h - 10}
          textAnchor="middle"
          fontSize={9}
          fill="var(--app-faint)"
          className="font-mono"
        >
          {d.week}
        </text>
      ))}
      <defs>
        <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--app-gold)" stopOpacity={0.18} />
          <stop offset="100%" stopColor="var(--app-gold)" stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#lineGrad)" />
      <path d={path} fill="none" stroke="var(--app-gold)" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
      {prediction && predPath && (
        <>
          <path d={predPath} fill="none" stroke="var(--app-gold)" strokeWidth={2.4} strokeDasharray="6 4" strokeLinecap="round" strokeLinejoin="round" opacity={0.7} />
          {showConfidence && confidenceBand && (
            <polygon
              points={`${padL},${y(min)} ${confidenceBand} ${padL},${y(max)}`}
              fill="var(--app-gold)"
              opacity={0.06}
            />
          )}
          {prediction.points.map((p, i) => {
            const idx = data.length + i
            return (
              <circle key={p.week} cx={x(idx)} cy={y(p.value)} r={3} fill="var(--app-gold)" opacity={0.5} />
            )
          })}
        </>
      )}
      {data.map((d, i) => (
        <circle key={d.week} cx={x(i)} cy={y(d.value)} r={2.8} fill="var(--app-card)" stroke="var(--app-gold)" strokeWidth={1.6} />
      ))}
      {peaks?.map((p) => {
        const idx = data.findIndex((d) => d.week === p.week)
        if (idx < 0) return null
        return (
          <g key={p.week}>
            <line
              x1={x(idx)}
              x2={x(idx)}
              y1={10}
              y2={h - padB}
              stroke="var(--app-line-strong)"
              strokeDasharray="3 4"
              vectorEffect="non-scaling-stroke"
            />
            <rect x={x(idx) - 22} y={4} width={44} height={14} rx={7} fill="var(--app-gold-soft)" />
            <text x={x(idx)} y={14.5} textAnchor="middle" fontSize={8} fill="var(--app-gold)" className="font-mono" fontWeight={700}>
              {p.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export function DonutChart({
  data,
  size = 160,
  showCenter = true,
}: {
  data: { label: string; pct: number; color?: string }[]
  size?: number
  showCenter?: boolean
}) {
  const cx = size / 2
  const cy = size / 2
  const r = size / 2 - 16
  const inner = r * 0.62
  const total = data.reduce((s, d) => s + d.pct, 0)
  const colors = ["var(--app-gold)", "var(--app-pos)", "var(--app-neg)", "#6e6e73", "#8B7CF6", "#6E5CE6"]

  const slices = data.reduce<{ el: React.ReactNode; angle: number }[]>((acc, d, i) => {
    const prevAngle = i === 0 ? -90 : acc[i - 1].angle
    const sweep = (d.pct / total) * 360
    const startAngle = prevAngle
    const endAngle = prevAngle + sweep
    const startRad = (startAngle * Math.PI) / 180
    const endRad = (endAngle * Math.PI) / 180
    const x1 = cx + r * Math.cos(startRad)
    const y1 = cy + r * Math.sin(startRad)
    const x2 = cx + r * Math.cos(endRad)
    const y2 = cy + r * Math.sin(endRad)
    const ix1 = cx + inner * Math.cos(startRad)
    const iy1 = cy + inner * Math.sin(startRad)
    const ix2 = cx + inner * Math.cos(endRad)
    const iy2 = cy + inner * Math.sin(endRad)
    const large = sweep > 180 ? 1 : 0
    const path = `M ${ix1} ${iy1} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} L ${ix2} ${iy2} A ${inner} ${inner} 0 ${large} 0 ${ix1} ${iy1} Z`
    acc.push({
      el: (
        <path
          key={d.label}
          d={path}
          fill={colors[i % colors.length]}
          stroke="var(--app-card)"
          strokeWidth={2}
          className="transition-opacity duration-300"
          style={{ opacity: 0.92 }}
        />
      ),
      angle: endAngle,
    })
    return acc
  }, []).map((s) => s.el)

  return (
    <div className="inline-flex items-center gap-5">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0" role="img" aria-label="Donut chart">
        <defs>
          <filter id="donutShadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="1" stdDeviation="2" floodColor="var(--app-gold)" floodOpacity="0.15" />
          </filter>
        </defs>
        <g filter="url(#donutShadow)">
          {slices}
        </g>
        {showCenter && (
          <>
            <circle cx={cx} cy={cy} r={inner - 2} fill="var(--app-card)" />
            <text x={cx} y={cy - 2} textAnchor="middle" fontSize={size * 0.18} fontWeight={700} fill="var(--app-text)" className="font-mono font-num">
              {total}%
            </text>
            <text x={cx} y={cy + size * 0.1} textAnchor="middle" fontSize={size * 0.08} fill="var(--app-faint)" className="font-inter">
              total
            </text>
          </>
        )}
      </svg>
      <div className="flex flex-col gap-2">
        {data.map((d, i) => (
          <div key={d.label} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: colors[i % colors.length] }} />
            <span className="font-inter cosmic-text-xs text-[var(--app-text)]">{d.label}</span>
            <span className="font-inter cosmic-text-xs font-semibold font-num text-[var(--app-text)]">{d.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

 export function BarChart({
  data,
  height = 180,
  horizontal = false,
  group = false,
  prediction = false,
}: {
  data: { label: string; value: number; compare?: number }[]
  height?: number
  horizontal?: boolean
  group?: boolean
  prediction?: boolean
}) {
  const w = 660
  const h = height
  const padB = 28
  const padL = 52
  const padR = 16
  const plotW = w - padL - padR
  const plotH = h - padB - 12
  const max = Math.max(...data.map((d) => d.compare ?? d.value)) * 1.15

  if (horizontal) {
    const barH = Math.min(28, (plotH - barGap(data.length - 1)) / data.length)
    const totalH = data.length * (barH + 8)
    const offset = (plotH - totalH) / 2
    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="h-auto w-full" role="img" aria-label="Horizontal bar chart">
        {data.map((d, i) => {
          const cy = offset + i * (barH + 8) + 12
          const bw = (d.value / max) * plotW
          const bw2 = d.compare != null ? (d.compare / max) * plotW : 0
          return (
            <g key={d.label}>
              <text x={padL - 6} y={cy + barH / 2 + 4} textAnchor="end" fontSize={10} fill="var(--app-faint)" className="font-inter">
                {d.label}
              </text>
              {d.compare != null && (
                <rect x={padL} y={cy} width={bw2} height={barH} rx={4} fill="var(--app-grid)" opacity={0.5} />
              )}
              <rect x={padL + (d.compare != null ? bw2 + 4 : 0)} y={cy} width={bw} height={barH} rx={4} fill={prediction ? "var(--app-gold)" : "var(--app-gold-soft)"} opacity={prediction ? 0.5 : 1} stroke={prediction ? "var(--app-gold)" : "none"} strokeDasharray={prediction ? "4 3" : "none"} strokeWidth={1.5} />
              <text x={padL + bw + 6} y={cy + barH / 2 + 4} fontSize={10} fill="var(--app-text)" className="font-mono font-num font-semibold">
                {d.value.toLocaleString()}
              </text>
            </g>
          )
        })}
      </svg>
    )
  }

  const barW = group ? (plotW / data.length) * 0.35 : (plotW / data.length) * 0.6
  const gap = group ? (plotW / data.length) * 0.35 : (plotW / data.length) * 0.15
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-auto w-full" role="img" aria-label="Bar chart">
      <defs>
        <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--app-gold)" stopOpacity={1} />
          <stop offset="100%" stopColor="var(--app-gold)" stopOpacity={0.7} />
        </linearGradient>
      </defs>
      {data.map((d, i) => {
        const bx = padL + i * (barW * 2 + gap) + gap
        const bw = group ? barW * 0.85 : barW
        const bh = (d.value / max) * plotH
        const by = h - padB - bh
        return (
          <g key={d.label}>
            <rect x={bx} y={by} width={bw} height={bh} rx={4} fill={prediction ? "var(--app-gold)" : "url(#barGrad)"} opacity={prediction ? 0.5 : 1} stroke={prediction ? "var(--app-gold)" : "none"} strokeDasharray={prediction ? "4 3" : "none"} strokeWidth={1.5} />
            <text x={bx + bw / 2} y={by - 6} textAnchor="middle" fontSize={10} fill="var(--app-text)" className="font-mono font-num font-semibold">
              {d.value.toLocaleString()}
            </text>
            <text x={bx + bw / 2} y={h - 8} textAnchor="middle" fontSize={9} fill="var(--app-faint)" className="font-inter">
              {d.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function barGap(n: number) {
  return n * 8
}

export function DayHourHeatmap({
  data,
  days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  hours = ["09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"],
}: {
  data: number[][]
  days?: string[]
  hours?: string[]
}) {
  const w = 660
  const h = 200
  const padL = 44
  const padB = 24
  const padR = 8
  const padT = 8
  const cellW = (w - padL - padR) / hours.length
  const cellH = (h - padT - padB) / days.length

  const maxVal = Math.max(...data.flat())
  const minVal = Math.min(...data.flat())
  const range = maxVal - minVal || 1

  const getColor = (v: number) => {
    const t = (v - minVal) / range
    if (t < 0.2) return "rgba(169, 121, 43, 0.06)"
    if (t < 0.4) return "rgba(169, 121, 43, 0.15)"
    if (t < 0.6) return "rgba(169, 121, 43, 0.32)"
    if (t < 0.75) return "rgba(169, 121, 43, 0.52)"
    if (t < 0.9) return "rgba(169, 121, 43, 0.72)"
    return "rgba(169, 121, 43, 0.88)"
  }

  const getStroke = (v: number) => {
    const t = (v - minVal) / range
    if (t >= 0.75) return "rgba(169, 121, 43, 0.5)"
    return "transparent"
  }

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-auto w-full" role="img" aria-label="Day-hour heatmap">
      <defs>
        <filter id="heatGlow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      {days.map((d, i) => (
        <text key={d} x={padL - 6} y={padT + i * cellH + cellH / 2 + 4} textAnchor="end" fontSize={10} fill="var(--app-faint)" className="font-inter">
          {d}
        </text>
      ))}
      {hours.map((hr, i) => (
        <text key={hr} x={padL + i * cellW + cellW / 2} y={h - 6} textAnchor="middle" fontSize={9} fill="var(--app-faint)" className="font-mono">
          {hr}
        </text>
      ))}
      {data.map((row, di) =>
        row.map((val, hi) => (
          <g key={`${di}-${hi}`}>
            {val >= maxVal * 0.9 && (
              <rect
                x={padL + hi * cellW - 1}
                y={padT + di * cellH - 1}
                width={cellW + 2}
                height={cellH + 2}
                rx={5}
                fill={getColor(val)}
                filter="url(#heatGlow)"
                opacity={0.3}
              />
            )}
            <rect
              x={padL + hi * cellW + 1}
              y={padT + di * cellH + 1}
              width={cellW - 2}
              height={cellH - 2}
              rx={3.5}
              fill={getColor(val)}
              stroke={getStroke(val)}
              strokeWidth={1}
            />
            <title>{`${days[di]} ${hours[hi]}:00 — ${val}% attention`}</title>
          </g>
        ))
      )}
    </svg>
  )
}

export function FunnelBars({
  stages,
}: {
  stages: { stage: string; value: number; rate: string; label: string }[]
}) {
  const max = stages[0].value
  return (
    <div className="flex flex-col gap-2.5">
      {stages.map((s, i) => {
        const w = Math.max((s.value / max) * 100, 6)
        const isTop = i < 2
        return (
          <div key={s.stage} className="group">
            <div className="mb-1 flex items-baseline justify-between gap-2">
              <span className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">
                {s.stage}
                <span className="ml-2 font-normal text-[var(--app-faint)]">{s.label}</span>
              </span>
              <span className="font-inter cosmic-text-xs font-semibold font-num text-[var(--app-text)]">
                {s.value.toLocaleString("en-US")}
                <span className="ml-2 text-[var(--app-faint)]">{s.rate}</span>
              </span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full" style={{ background: "var(--app-grid)" }}>
              <div
                className="h-full rounded-full transition-[width] duration-700 ease-out"
                style={{
                  width: `${w}%`,
                  background: isTop
                    ? `linear-gradient(90deg, var(--app-gold) 0%, color-mix(in srgb, var(--app-gold) 70%, white) 100%)`
                    : `color-mix(in srgb, var(--app-gold) ${100 - i * 14}%, var(--app-card))`,
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function HBars({
  items,
}: {
  items: { label: string; pct: number; sub?: string }[]
}) {
  const max = Math.max(...items.map((i) => i.pct))
  return (
    <div className="flex flex-col gap-3.5">
      {items.map((i) => (
        <div key={i.label}>
          <div className="mb-1.5 flex items-baseline justify-between gap-3">
            <span className="font-inter cosmic-text-xs text-[var(--app-text)]">{i.label}</span>
            <span className="font-inter cosmic-text-xs font-semibold font-num text-[var(--app-text)]">{i.pct}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: "var(--app-grid)" }}>
            <div
              className="h-full rounded-full transition-[width] duration-500 ease-out"
              style={{
                width: `${(i.pct / max) * 100}%`,
                background: `linear-gradient(90deg, var(--app-gold) 0%, color-mix(in srgb, var(--app-gold) 65%, white) 100%)`,
              }}
            />
          </div>
          {i.sub && (
            <p className="mt-1 font-inter cosmic-text-2xs text-[var(--app-faint)]">{i.sub}</p>
          )}
        </div>
      ))}
    </div>
  )
}

export function HeatGrid({
  zones,
}: {
  zones: { code: string; name: string; traffic: number; dwell: string; heat: number; note?: string; flag?: string }[]
}) {
  return (
    <div className="grid grid-cols-5 gap-2.5">
      {zones.map((z) => {
        const intensity = Math.round(z.heat * 72)
        return (
          <div
            key={z.code}
            title={`${z.name} — ${z.traffic}% traffic · dwell ${z.dwell}${z.note ? ` · ${z.note}` : ""}${
              z.flag ? ` · ⚠ ${z.flag}` : ""
            }`}
            className={`group relative aspect-square cursor-default rounded-xl border p-2.5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg ${
              z.flag ? "border-[var(--app-neg)]/40" : "border-[var(--app-line)]"
            }`}
            style={{
              background: `linear-gradient(135deg, color-mix(in srgb, var(--app-gold) ${intensity}%, var(--app-card)) 0%, color-mix(in srgb, var(--app-gold) ${Math.max(intensity - 15, 0)}%, var(--app-card)) 100%)`,
              boxShadow: z.heat > 0.7 ? `0 0 20px color-mix(in srgb, var(--app-gold) ${Math.round(z.heat * 18)}%, transparent)` : undefined,
            }}
          >
            <span className="font-mono cosmic-text-2xs tracking-[0.08em] text-[var(--app-sub)]">{z.code}</span>
            <div className="mt-1.5 font-inter cosmic-text-base font-bold font-num leading-none text-[var(--app-text)]">
              {z.traffic}%
            </div>
            {z.flag && (
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: "var(--app-neg)" }} />
            )}
          </div>
        )
      })}
    </div>
  )
}
