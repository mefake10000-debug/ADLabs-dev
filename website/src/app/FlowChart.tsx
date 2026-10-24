import { VISITOR_FLOW } from "../data/dashboard"

// Fixed layout positions for the flow nodes (0-100 canvas).
const POS: Record<string, { x: number; y: number }> = {
  E0: { x: 8, y: 50 },
  A1: { x: 30, y: 22 },
  L2: { x: 34, y: 72 },
  S5: { x: 58, y: 84 },
  H3: { x: 56, y: 46 },
  R6: { x: 82, y: 30 },
  T8: { x: 88, y: 74 },
}

// Edge curve path between two node centres.
function edgePath(a: { x: number; y: number }, b: { x: number; y: number }) {
  const mx = (a.x + b.x) / 2
  return `M${a.x} ${a.y} C${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`
}

export function VisitorFlow() {
  const { nodes, edges, title, sub } = VISITOR_FLOW
  const maxPct = Math.max(...edges.map((e) => e.pct), 1)

  return (
    <div>
      <p className="mb-1 font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{title}</p>
      <p className="mb-4 font-inter cosmic-text-xs text-[var(--app-sub)]">{sub}</p>

      <div className="relative rounded-2xl border border-[var(--app-line)] p-3" style={{ background: "color-mix(in srgb, var(--app-bg) 55%, transparent)" }}>
        <svg viewBox="0 0 100 100" className="w-full" style={{ maxHeight: 340 }} role="img" aria-label={title}>
          <defs>
            <filter id="flowGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="1.2" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>
          {/* Edges */}
          {edges.map((e) => {
            const a = POS[e.from]
            const b = POS[e.to]
            const w = 0.6 + (e.pct / maxPct) * 3.4
            const intensity = e.pct / maxPct
            return (
              <g key={`${e.from}-${e.to}`}>
                <path d={edgePath(a, b)} fill="none" stroke="var(--app-line)" strokeWidth={w + 0.8} strokeLinecap="round" opacity={0.3} />
                <path d={edgePath(a, b)} fill="none" stroke="var(--app-gold)" strokeWidth={w} strokeLinecap="round" opacity={0.4 + intensity * 0.5} filter={intensity > 0.8 ? "url(#flowGlow)" : undefined} />
              </g>
            )
          })}
          {/* Nodes */}
          {nodes.map((n) => {
            const p = POS[n.id]
            const inEdges = edges.filter((e) => e.to === n.id).reduce((s, e) => s + e.pct, 0)
            const isActive = inEdges > 0
            return (
              <g key={n.id}>
                <circle cx={p.x} cy={p.y} r={5} fill="var(--app-card)" stroke="var(--app-gold)" strokeWidth="1.4" />
                <circle cx={p.x} cy={p.y} r={2} fill="var(--app-gold)" opacity={isActive ? 1 : 0.4} />
                {isActive && (
                  <text x={p.x + 6} y={p.y + 4} fill="var(--app-faint)" fontSize="3.2" fontFamily="ui-monospace, monospace">
                    ·{Math.round(inEdges)}%
                  </text>
                )}
              </g>
            )
          })}
        </svg>

        <div className="mt-2.5 flex flex-wrap gap-2">
          {nodes.map((n) => {
            const inEdges = edges.filter((e) => e.to === n.id).reduce((s, e) => s + e.pct, 0)
            return (
              <span key={n.id} className="flex items-center gap-1.5 rounded-full px-2 py-1 font-inter cosmic-text-2xs font-medium text-[var(--app-sub)] transition-colors duration-150 hover:text-[var(--app-text)]" style={{ background: "var(--app-raise)" }}>
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--app-gold)", opacity: inEdges > 0 ? 1 : 0.4 }} />
                {n.id} {n.name}
              </span>
            )
          })}
        </div>
      </div>
    </div>
  )
}
