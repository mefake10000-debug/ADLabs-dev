import { useState } from "react"
import { Package } from "lucide-react"
import { Panel, Label, Chip, InfoTip, ScreenHeader } from "../ui"
import { Sparkline } from "../charts"
import { INDUSTRY_SECTORS, INDUSTRY_OVERVIEW, PEER_NOTE, SIMULATED_NOTE } from "../../data/dashboard"

export function Product() {
  const [sector, setSector] = useState("fashion")
  const sectorData = INDUSTRY_SECTORS.find((s) => s.id === sector) ?? INDUSTRY_SECTORS[0]

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <ScreenHeader
        icon={Package}
        eyebrow="Industry intelligence"
        title="Industry Intelligence"
        sub={`Fixture-level gaze and touch across ${INDUSTRY_OVERVIEW.totalSectors} sectors · benchmarks, trends, and conversion signals.`}
      >
        <Chip tone="gold">{SIMULATED_NOTE}</Chip>
        <span className="rounded-full px-2.5 py-1 font-inter cosmic-text-2xs font-bold tracking-[0.08em]" style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>
          {INDUSTRY_OVERVIEW.totalSectors} SECTORS
        </span>
      </ScreenHeader>

      {/* Industry KPI strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {([
          { label: "Avg stop rate", value: INDUSTRY_OVERVIEW.avgStopRate, delta: "+0.8pp", tone: "pos" as const },
          { label: "Avg conversion", value: INDUSTRY_OVERVIEW.avgConversion, delta: "+2.1pp", tone: "pos" as const },
          { label: "Top performer", value: "Fashion", delta: INDUSTRY_OVERVIEW.topPerformer, tone: "pos" as const },
          { label: "Sectors shown", value: `${INDUSTRY_OVERVIEW.totalSectors}`, delta: "sample data", tone: "flat" as const },
        ] as { label: string; value: string; delta: string; tone: "pos" | "neg" | "flat" }[]).map((k) => (
          <div key={k.label} className="rounded-xl border border-[var(--app-line)] p-3.5" style={{ background: "color-mix(in srgb, var(--app-card) 100%, transparent)" }}>
            <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.12em] text-[var(--app-faint)]">{k.label}</p>
            <p className="mt-1.5 font-num cosmic-text-xl font-bold leading-none text-[var(--app-text)]">{k.value}</p>
            <p className="mt-1 font-inter cosmic-text-2xs font-semibold" style={{ color: k.tone === "pos" ? "var(--app-pos)" : k.tone === "neg" ? "var(--app-neg)" : "var(--app-sub)" }}>
              {k.delta}
            </p>
          </div>
        ))}
      </div>

      {/* Key insight */}
      <div className="rounded-2xl border border-[var(--app-line)] p-5" style={{ background: "color-mix(in srgb, var(--app-card) 100%, transparent)" }}>
        <div className="flex items-center gap-2">
          <span className="rounded-full px-2 py-0.5 font-inter cosmic-text-2xs font-bold uppercase tracking-[0.08em]" style={{ background: "color-mix(in srgb, var(--app-gold) 12%, transparent)", color: "var(--app-gold)" }}>
            Key Insight
          </span>
          <InfoTip text="Derived from fixture-level gaze and touch data across all 8 sectors." />
        </div>
        <p className="mt-3 font-inter cosmic-text-sm font-medium leading-relaxed text-[var(--app-text)]">
          {INDUSTRY_OVERVIEW.bestInsight}
        </p>
      </div>

      {/* Sector tabs */}
      <div className="flex gap-2 flex-wrap">
        {INDUSTRY_SECTORS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSector(s.id)}
            className={`flex items-center gap-1.5 rounded-full px-3.5 py-2 font-inter cosmic-text-xs font-semibold transition-all duration-200 ${
              sector === s.id
                ? "text-[var(--app-card)] shadow-sm"
                : "text-[var(--app-sub)] border border-[var(--app-line)] hover:text-[var(--app-text)] hover:border-[var(--app-line-strong)]"
            }`}
            style={sector === s.id ? { background: "var(--app-text)", color: "var(--app-card)" } : undefined}
          >
            <span>{s.icon}</span>
            {s.label}
          </button>
        ))}
      </div>

      {/* Selected sector detail */}
      {sectorData && (
        <>
          {/* Sector hero */}
          <div className="grid gap-5 xl:grid-cols-[1fr_1.6fr]">
            <div className="flex flex-col gap-4">
              <div className="rounded-2xl border border-[var(--app-line)] overflow-hidden" style={{ boxShadow: "var(--app-shadow)" }}>
                <div className="relative aspect-[16/9] overflow-hidden">
                  <img
                    src={sectorData.image}
                    alt={sectorData.label}
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                  <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, transparent 40%, rgba(0,0,0,0.6) 100%)" }} />
                  <div className="absolute bottom-4 left-4 right-4">
                    <span className="cosmic-text-2xl">{sectorData.icon}</span>
                    <p className="mt-1 font-inter cosmic-text-lg font-bold text-white">{sectorData.label}</p>
                  </div>
                </div>
                <div className="p-5">
                  <p className="font-inter cosmic-text-sm leading-relaxed text-[var(--app-sub)]">{sectorData.description}</p>
                </div>
              </div>

              {/* Sector KPIs */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-[var(--app-line)] p-3.5">
                  <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.12em] text-[var(--app-faint)]">Market size</p>
                  <p className="mt-1 font-num cosmic-text-lg font-bold text-[var(--app-text)]">{sectorData.marketSize}</p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] p-3.5">
                  <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.12em] text-[var(--app-faint)]">Benchmark</p>
                  <p className="mt-1 font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">{sectorData.benchmark}</p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] p-3.5">
                  <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.12em] text-[var(--app-faint)]">Avg dwell</p>
                  <p className="mt-1 font-num cosmic-text-lg font-bold text-[var(--app-text)]">{sectorData.avgDwell}</p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] p-3.5">
                  <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.12em] text-[var(--app-faint)]">Conversion</p>
                  <p className="mt-1 font-num cosmic-text-lg font-bold" style={{ color: "var(--app-pos)" }}>{sectorData.avgConversion}</p>
                </div>
              </div>

              {/* Key insight */}
              <div className="rounded-xl border border-[var(--app-gold)]/20 p-4" style={{ background: "color-mix(in srgb, var(--app-gold) 6%, transparent)" }}>
                <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.12em]" style={{ color: "var(--app-gold)" }}>Sector insight</p>
                <p className="mt-2 font-inter cosmic-text-sm leading-relaxed text-[var(--app-text)]">{sectorData.keyInsight}</p>
              </div>
            </div>

            {/* Fixture detail panel */}
            <Panel
              title={`${sectorData.label} — fixture breakdown`}
              action={<Label>{sectorData.items.length} fixtures</Label>}
              info="Gaze = average attention duration · touch = interaction rate · trend = 4-week trajectory."
            >
              <div className="flex flex-col gap-3">
                {sectorData.items.map((item, i) => (
                  <div key={item.name} className="group rounded-xl border border-[var(--app-line)] p-4 transition-colors hover:border-[var(--app-gold)]/30">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span
                            className="grid h-5 w-5 shrink-0 place-items-center rounded-full font-inter cosmic-text-2xs font-bold"
                            style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}
                          >
                            {i + 1}
                          </span>
                          <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{item.name}</p>
                        </div>
                        {item.note && (
                          <p className="mt-1 ml-7 font-inter cosmic-text-xs text-[var(--app-faint)]">{item.note}</p>
                        )}
                      </div>
                      <Sparkline data={item.trend} tone="pos" />
                    </div>
                    <div className="mt-3 ml-7 grid grid-cols-3 gap-3">
                      <div>
                        <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.1em] text-[var(--app-faint)]">Gaze</p>
                        <p className="mt-0.5 font-num cosmic-text-sm font-bold text-[var(--app-text)]">{item.gaze}</p>
                      </div>
                      <div>
                        <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.1em] text-[var(--app-faint)]">Touch</p>
                        <p className="mt-0.5 font-num cosmic-text-sm font-bold text-[var(--app-text)]">{item.touch}</p>
                      </div>
                      {item.conversion && (
                        <div>
                          <p className="font-inter cosmic-text-2xs font-bold uppercase tracking-[0.1em] text-[var(--app-faint)]">Conversion</p>
                          <p className="mt-0.5 font-num cosmic-text-sm font-bold" style={{ color: "var(--app-pos)" }}>{item.conversion}</p>
                        </div>
                      )}
                    </div>
                    {/* Touch bar */}
                    <div className="mt-3 ml-7">
                      <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: "var(--app-grid)" }}>
                        <div
                          className="h-full rounded-full transition-[width] duration-500 ease-out"
                          style={{
                            width: `${parseFloat(item.touch) * 1.1}%`,
                            background: `linear-gradient(90deg, var(--app-gold) 0%, color-mix(in srgb, var(--app-gold) 60%, white) 100%)`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          {/* Cross-sector comparison */}
          <Panel
            title="Cross-sector benchmark"
            action={<Label>8 industries</Label>}
            info="Average dwell time and conversion rate compared across all tracked sectors."
          >
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {INDUSTRY_SECTORS.map((s) => {
                const isActive = s.id === sector
                return (
                  <button
                    key={s.id}
                    onClick={() => setSector(s.id)}
                    className={`rounded-xl border p-4 text-left transition-all duration-200 ${
                      isActive ? "border-[var(--app-gold)] shadow-sm" : "border-[var(--app-line)] hover:border-[var(--app-gold)]/30"
                    }`}
                    style={isActive ? { background: "color-mix(in srgb, var(--app-gold) 5%, var(--app-card))" } : undefined}
                  >
                    <div className="flex items-center gap-2">
                      <span className="cosmic-text-base">{s.icon}</span>
                      <p className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">{s.label}</p>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <div>
                        <p className="font-inter cosmic-text-2xs font-bold uppercase text-[var(--app-faint)]">Dwell</p>
                        <p className="font-num cosmic-text-sm font-bold text-[var(--app-text)]">{s.avgDwell}</p>
                      </div>
                      <div>
                        <p className="font-inter cosmic-text-2xs font-bold uppercase text-[var(--app-faint)]">Conv.</p>
                        <p className="font-num cosmic-text-sm font-bold" style={{ color: "var(--app-pos)" }}>{s.avgConversion}</p>
                      </div>
                    </div>
                    <div className="mt-2.5 h-1 w-full overflow-hidden rounded-full" style={{ background: "var(--app-grid)" }}>
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${(parseFloat(s.avgConversion) / 48) * 100}%`,
                          background: isActive ? "var(--app-gold)" : "var(--app-sub)",
                          opacity: isActive ? 1 : 0.4,
                        }}
                      />
                    </div>
                  </button>
                )
              })}
            </div>
          </Panel>
        </>
      )}

      <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{SIMULATED_NOTE} · {PEER_NOTE}</p>
    </div>
  )
}
