import { REVENUE_KPIS } from "../data/instrument"

function tone(col: string): string {
  // k.delta encodes directional intent (kept simple: + = positive)
  if (col.includes("×") || col.includes("healthy") || col.startsWith("+")) return "var(--app-pos)"
  return "var(--app-sub)"
}

export function RevenueKpis() {
  const r = REVENUE_KPIS
  return (
    <div className="rounded-2xl border border-[var(--app-line)] p-5" style={{ background: "var(--app-card)" }}>
      <div className="flex items-center justify-between">
        <div>
          <p className="font-inter cosmic-text-xs font-bold uppercase tracking-[0.14em] text-[var(--app-faint)]">Revenue grade</p>
          <p className="mt-1 font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{r.title}</p>
        </div>
        <span className="rounded-full px-2.5 py-1 font-inter cosmic-text-2xs font-bold tracking-[0.08em]" style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>
          INTERNAL
        </span>
      </div>
      <p className="mt-1.5 font-inter cosmic-text-xs leading-snug text-[var(--app-sub)]">{r.sub}</p>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {r.items.map((k) => (
          <div key={k.key} className="rounded-xl border border-[var(--app-line)] p-3.5" style={{ background: "color-mix(in srgb, var(--app-bg) 60%, transparent)" }}>
            <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.12em] text-[var(--app-faint)]">{k.label}</p>
            <p className="mt-1 font-num cosmic-text-xl font-bold leading-none text-[var(--app-text)]">{k.value}</p>
            <p className="mt-1 font-inter cosmic-text-2xs font-semibold" style={{ color: tone(k.delta) }}>
              {k.delta} · <span style={{ fontWeight: 400, color: "var(--app-faint)" }}>{k.note}</span>
            </p>
          </div>
        ))}
      </div>

      <p className="mt-3 font-inter cosmic-text-2xs italic text-[var(--app-faint)]">{r.note}</p>
    </div>
  )
}
