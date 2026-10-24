import { Wallet, ShoppingBag, Percent, Megaphone, IndianRupee, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react"
import { BUSINESS_KPIS, OCCUPANCY } from "../data/dashboard"
import { Panel, Label } from "./ui"

const ICONS: Record<string, typeof Wallet> = {
  yield: Wallet,
  basket: ShoppingBag,
  pos: Percent,
  megaphone: Megaphone,
  currency: IndianRupee,
}

export function BusinessKpis() {
  return (
    <Panel title="Business on the floor" action={<Label>Sample figures</Label>} verified="Illustrative only">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
        {BUSINESS_KPIS.map((k) => {
          const Icon = ICONS[k.iconHint] ?? Wallet
          const up = k.tone === "pos"
          const flat = k.tone === "flat"
          return (
            <div key={k.label} className="relative overflow-hidden rounded-xl border border-[var(--app-line)] p-3.5" style={{ background: "color-mix(in srgb, var(--app-bg) 55%, transparent)" }}>
              <div className="flex items-center justify-between">
                <span className="grid h-7 w-7 place-items-center rounded-lg" style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>
                  <Icon size={14} strokeWidth={2.2} />
                </span>
              </div>
              <p className="mt-3 font-num cosmic-text-xl font-bold leading-none tracking-[-0.01em] text-[var(--app-text)]">{k.value}</p>
              <p className="mt-1.5 font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">{k.label}</p>
              <p className="mt-1 flex items-center gap-1 font-inter cosmic-text-2xs" style={{ color: up ? "var(--app-pos)" : flat ? "var(--app-faint)" : "var(--app-neg)" }}>
                {up ? <ArrowUpRight size={11} /> : flat ? <Minus size={11} /> : <ArrowDownRight size={11} />}
                <span className="font-num">{k.delta}</span>
                <span className="font-normal text-[var(--app-faint)]">{k.note}</span>
              </p>
            </div>
          )
        })}
      </div>
    </Panel>
  )
}

export function OccupancyGauge({ compact = false }: { compact?: boolean }) {
  const o = OCCUPANCY
  const pct = Math.min((o.now / o.capacity) * 100, 100)
  const r = 42
  const c = 2 * Math.PI * r
  const filled = (pct / 100) * c
  const tone = o.level >= 80 ? "var(--app-neg)" : o.level >= 55 ? "var(--app-gold)" : "var(--app-pos)"

  if (compact) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-[var(--app-line)] p-3.5">
        <div className="grid h-9 w-9 place-items-center rounded-full bg-[var(--app-gold-soft)] text-[var(--app-gold)]">
          <span className="font-num cosmic-text-sm font-bold">{o.now}</span>
        </div>
        <div className="min-w-0">
          <p className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">Occupancy</p>
          <p className="font-inter cosmic-text-2xs text-[var(--app-faint)]">{o.now} of {o.capacity} capacity</p>
        </div>
      </div>
    )
  }

  return (
    <Panel title="Sample occupancy" action={<Label>{o.level}% · example</Label>}>
      <div className="flex flex-col items-center py-2">
        <svg width="120" height="120" viewBox="0 0 100 100" className="-rotate-90">
          <circle cx="50" cy="50" r={r} fill="none" stroke="var(--app-grid)" strokeWidth="9" />
          <circle
            cx="50" cy="50" r={r} fill="none"
            stroke={tone} strokeWidth="9" strokeLinecap="round"
            strokeDasharray={`${filled} ${c}`}
            style={{ transition: "stroke-dasharray 0.6s cubic-bezier(0.16,1,0.3,1)" }}
          />
        </svg>
        <div className="-mt-[84px] text-center">
          <p className="font-num cosmic-text-2xl font-bold text-[var(--app-text)]">{o.now}<span className="text-[var(--app-faint)] cosmic-text-sm">/{o.capacity}</span></p>
          <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.1em]" style={{ color: tone }}>In store</p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <div className="rounded-lg border border-[var(--app-line)] p-2 text-center">
          <p className="font-num cosmic-text-sm font-bold text-[var(--app-text)]">{o.queue}</p>
          <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.08em] text-[var(--app-faint)]">Queue</p>
        </div>
        <div className="rounded-lg border border-[var(--app-line)] p-2 text-center">
          <p className="font-num cosmic-text-sm font-bold text-[var(--app-text)]">{o.avgWait}</p>
          <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.08em] text-[var(--app-faint)]">Wait ∅</p>
        </div>
        <div className="rounded-lg border border-[var(--app-line)] p-2 text-center">
          <p className="font-num cosmic-text-xs font-bold text-[var(--app-gold)]">{o.peakWindow}</p>
          <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.08em] text-[var(--app-faint)]">Peak</p>
        </div>
      </div>
      <label className="mt-3 flex items-center justify-between font-inter cosmic-text-2xs text-[var(--app-faint)]">
        <span>Occupancy last 2 hours</span>
        <span className="font-num">{o.trend[o.trend.length - 1]}</span>
      </label>
    </Panel>
  )
}
