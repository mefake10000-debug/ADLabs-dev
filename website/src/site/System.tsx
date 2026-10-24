"use client"

import Link from "next/link"
import { ArrowRight, TrendingUp } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { SectionHeader } from "../components/SectionHeader"
import { SYSTEM } from "../data/site"
import { TRAFFIC_HOURS } from "../data/dashboard"

function MiniTrend() {
  const w = 260
  const h = 56
  const max = Math.max(...TRAFFIC_HOURS.map((d) => d.v)) * 1.1
  const pts = TRAFFIC_HOURS.map(
    (d, i) => `${(i / (TRAFFIC_HOURS.length - 1)) * w},${h - (d.v / max) * h}`,
  )
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-14 w-full" aria-hidden>
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke="#8B7CF6"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function System() {
  const s = SYSTEM
  const itf = s.interface
  return (
    <section id="system" className="scroll-mt-24 py-12 sm:py-16 lg:py-20" style={{ background: "#05050a" }}>
      <div className="mx-auto max-w-[1200px] px-6">
      <SectionHeader index={s.index} kicker={s.kicker} sub={s.sub}>
        {s.h2}
      </SectionHeader>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {s.trio.map((t, i) => (
          <Reveal key={t.k} delay={i * 0.1}>
            <article className="site-card site-card-glare h-full p-7">
              <span className="font-mono cosmic-text-xs text-[#86868b]">{t.k}</span>
              <h3 className="mt-3 font-semibold cosmic-text-2xl leading-tight text-[#f5f5f7]">{t.title}</h3>
              <p className="mt-3 cosmic-text-base leading-relaxed text-[#a1a1aa]">{t.desc}</p>
            </article>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.15}>
        <div className="mt-8 grid items-center gap-8 lg:grid-cols-[1fr_1.1fr]">
          <div>
            <span className="cosmic-text-xs font-semibold uppercase tracking-[0.1em] text-[#a1a1aa]">{itf.kicker}</span>
            <h3 className="mt-4 font-semibold cosmic-text-4xl leading-[1.05] tracking-[-0.02em] text-[#f5f5f7] sm:cosmic-text-5xl">
              {itf.h2}
            </h3>
            <p className="mt-5 max-w-sm cosmic-text-base leading-relaxed text-[#a1a1aa]">{itf.sub}</p>
            <Link
              href="/dashboard"
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-[#8B7CF6] px-6 py-3 cosmic-text-sm font-semibold text-[#05050a] shadow-lg transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#6E5CE6]"
            >
              {itf.cta}
              <ArrowRight size={16} strokeWidth={2.4} />
            </Link>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#12121a] p-6 shadow-lg sm:p-8 transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="cosmic-text-sm font-semibold text-[#f5f5f7]">{itf.store}</p>
                <p className="mt-0.5 flex items-center gap-1.5 font-mono cosmic-text-2xs tracking-[0.14em] text-[#a1a1aa]">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-pulse-ring absolute inline-flex h-full w-full rounded-full bg-[#8B7CF6]" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#8B7CF6]" />
                  </span>
                  {itf.live}
                </p>
              </div>
              <span className="font-mono cosmic-text-2xs tracking-[0.1em] text-[#86868b]">{itf.hours}</span>
            </div>

            <div className="mt-6 grid grid-cols-3 gap-4">
              {itf.stats.map((st) => (
                <div key={st.label} className="rounded-2xl border border-white/8 bg-[#1a1a24]/80 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all duration-200 hover:border-[#8B7CF6]/40 hover:shadow-[0_4px_12px_rgba(139,124,246,0.1)]">
                  <p className="font-inter cosmic-text-xl font-bold font-num text-[#f5f5f7]">
                    {typeof st.value === "number" ? st.value.toLocaleString("en-US") : st.value}
                    {st.suffix ?? ""}
                  </p>
                  <p className="mt-1 cosmic-text-2xs font-medium uppercase tracking-[0.1em] text-[#86868b]">
                    {st.label}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-2xl border border-white/8 bg-[#1a1a24]/80 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all duration-200 hover:border-[#8B7CF6]/40 hover:shadow-[0_4px_12px_rgba(139,124,246,0.1)]">
              <div className="flex items-center justify-between">
                <p className="font-mono cosmic-text-2xs tracking-[0.16em] text-[#86868b]">{itf.trend}</p>
                <p className="flex items-center gap-1 font-inter cosmic-text-xs font-bold font-num text-[#8B7CF6]">
                  <TrendingUp size={13} strokeWidth={2.5} />
                  {itf.trendDelta}
                </p>
              </div>
              <MiniTrend />
            </div>
          </div>
        </div>
      </Reveal>
      </div>
    </section>
  )
}
