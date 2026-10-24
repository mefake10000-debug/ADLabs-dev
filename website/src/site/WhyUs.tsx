"use client"

import Link from "next/link"
import { ArrowRight, Plug, ShieldCheck, SearchCheck, GraduationCap, Sparkles } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { SectionHeader } from "../components/SectionHeader"
import { WHY_US } from "../data/site"
import type { LucideIcon } from "lucide-react"

const PILLAR_ICONS: Record<string, LucideIcon> = {
  plug: Plug,
  shield: ShieldCheck,
  verdict: SearchCheck,
  learn: GraduationCap,
}

export function WhyUs() {
  const w = WHY_US
  return (
    <section id="why" className="scroll-mt-24 py-12 sm:py-16 lg:py-20" style={{ background: "#05050a" }}>
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader index={w.index} kicker={w.kicker} sub={w.sub}>
          {w.h2a} {w.h2b}
        </SectionHeader>

        <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {w.purpose.beats.map((b, i) => (
            <Reveal key={b.t} delay={i * 0.06}>
              <article className="site-card site-card-glare h-full p-6">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#8B7CF6]/12 text-[#8B7CF6]">
                  <Sparkles size={18} strokeWidth={2} />
                </span>
                <h3 className="mt-4 cosmic-text-base font-semibold leading-snug text-[#f5f5f7]">{b.t}</h3>
                <p className="mt-2 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{b.d}</p>
              </article>
            </Reveal>
          ))}
        </div>

        <div className="mt-12 flex items-center gap-3">
          <span className="cosmic-text-xs font-semibold uppercase tracking-[0.16em] text-[#8B7CF6]">The four differentiators</span>
          <span className="h-px flex-1 bg-white/8" />
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {w.pillars.map((p, i) => {
            const Icon = PILLAR_ICONS[p.icon] ?? Plug
            return (
              <Reveal key={p.k} delay={i * 0.06}>
                <article className="site-card h-full p-6">
                  <div className="flex items-center justify-between">
                    <Icon size={20} strokeWidth={2} className="text-[#8B7CF6]" />
                    <span className="font-mono cosmic-text-xs text-[#86868b]">{p.k}</span>
                  </div>
                  <h3 className="mt-4 cosmic-text-base font-semibold leading-snug text-[#f5f5f7]">{p.title}</h3>
                  <p className="mt-2 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{p.desc}</p>
                  <p className="mt-3 border-t border-white/8 pt-3 cosmic-text-xs leading-relaxed text-[#86868b]">{p.answer}</p>
                </article>
              </Reveal>
            )
          })}
        </div>

        <Reveal delay={0.15}>
          <div className="mt-12 rounded-3xl border border-white/10 bg-[#12121a] p-7 lg:p-9">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-md">
                <h3 className="cosmic-text-xl font-bold leading-tight tracking-[-0.02em] text-[#f5f5f7]">{w.kpi.title}</h3>
                <p className="mt-2 cosmic-text-sm text-[#a1a1aa]">Measured on-device, verified before it prints. No slide-deck maths.</p>
              </div>
              <div className="grid flex-1 grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                {w.kpi.strip.map((k) => (
                  <div key={k.label} className="rounded-2xl border border-white/8 bg-white/4 p-4 text-center">
                    <span className="block cosmic-text-2xl font-bold tracking-[-0.03em] text-[#f5f5f7]">{k.value}</span>
                    <span className="mt-1 block cosmic-text-2xs leading-snug text-[#86868b]">{k.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="mt-8 flex flex-col gap-5 rounded-3xl border border-white/10 p-7 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h3 className="cosmic-text-base font-semibold text-[#f5f5f7]">{w.ip.title}</h3>
              <div className="mt-4 flex flex-wrap gap-2">
                {w.ip.chips.map((c) => (
                  <span key={c.t} className="rounded-full border border-[#8B7CF6]/25 bg-[#8B7CF6]/8 px-3.5 py-1.5 cosmic-text-xs font-medium text-[#c4c4cc]">
                    {c.t}
                  </span>
                ))}
              </div>
            </div>
            <Link
              href="/discover"
              className="inline-flex shrink-0 items-center gap-2 rounded-full bg-[#8B7CF6] px-6 py-3 cosmic-text-sm font-semibold text-[#05050a] transition-all duration-200 hover:bg-[#6E5CE6] hover:-translate-y-0.5 active:scale-[0.98]"
            >
              See what we can prove for your store
              <ArrowRight size={15} strokeWidth={2.4} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
