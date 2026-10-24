"use client"

import Link from "next/link"
import { ArrowRight, Sparkles, Gem, Leaf, Crown, Building2 } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { SectionHeader } from "../components/SectionHeader"
import { SECTORS } from "../data/site"

const SECTOR_ICONS = {
  fashion: Sparkles,
  beauty: Leaf,
  jewellery: Gem,
  premium: Crown,
}

const IMG_POS = ["center 32%", "center 24%", "center 38%", "center 28%"]

export function Sectors() {
  const s = SECTORS
  return (
    <section id="sectors" className="site-scope scroll-mt-24 border-t border-white/10 bg-[#05050a] py-12 sm:py-16 lg:py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader index={s.index} kicker={s.kicker}>
          {s.h2}
        </SectionHeader>

        <Reveal delay={0.1}>
          <p className="mt-6 mx-auto max-w-2xl text-center cosmic-text-xl leading-relaxed text-[#a1a1aa]">
            Impression is the currency of these spaces. We measure what the eye cannot articulate.
          </p>
        </Reveal>

        <Reveal delay={0.16}>
          <p className="mx-auto mt-6 max-w-3xl rounded-2xl border border-white/10 bg-[#12121a]/70 px-6 py-4 text-center cosmic-text-sm leading-relaxed text-[#a1a1aa]">
            {s.context}
          </p>
        </Reveal>

        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {s.cards.map((c, i) => {
            const Icon = SECTOR_ICONS[c.id as keyof typeof SECTOR_ICONS] ?? Building2
            return (
              <Reveal key={c.num} delay={i * 0.1}>
                <article className="site-card site-card-glare group flex h-full flex-col overflow-hidden">
                  <div className="relative aspect-[4/5] overflow-hidden xl:aspect-[3/4]">
                    <img
                      src={c.image}
                      alt={c.sub}
                      loading="lazy"
                      style={{ objectPosition: IMG_POS[i % IMG_POS.length] }}
                      className="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
                    />
                    <div className="pointer-events-none absolute inset-0" style={{
                      background: "linear-gradient(180deg, rgba(0,0,0,0.1) 0%, transparent 35%, rgba(0,0,0,0.5) 100%)"
                    }} />
                    <div className="pointer-events-none absolute inset-0 rounded-2xl" style={{
                      background: "linear-gradient(to top, rgba(0,0,0,0.65), transparent 45%)"
                    }} />

                    <div className="absolute top-5 left-5 flex items-center gap-2 rounded-full bg-black/65 px-3 py-1.5 cosmic-text-xs font-medium text-white backdrop-blur-sm border border-white/10">
                      <span className="grid h-5 w-5 place-items-center text-[#8B7CF6]">
                        <Icon size={12} strokeWidth={2.2} />
                      </span>
                      {c.tag}
                    </div>

                    <span className="absolute right-5 top-5 cosmic-text-xs font-medium text-white/60">{c.num}</span>

                    <div className="absolute inset-x-0 bottom-0 p-6">
                      <h3 className="cosmic-text-2xl font-semibold leading-none text-white mb-2">{c.title}</h3>
                      <p className="cosmic-text-sm text-white/75 max-w-[280px]">{c.sub}</p>
                    </div>
                  </div>

                  <div className="flex flex-1 flex-col p-6">
                    <p className="cosmic-text-xs font-medium uppercase tracking-normal text-[#8B7CF6]">Key Metrics We Track</p>
                    <ul className="mt-3 space-y-2">
                      {[
                        "Window stop rate by collection",
                        "Hero product gaze duration",
                        "Zone dwell & conversion",
                        "Peak hour staffing alignment",
                      ].map((m) => (
                        <li key={m} className="flex items-start gap-2 cosmic-text-sm text-[#a1a1aa]">
                          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#8B7CF6]" />
                          {m}
                        </li>
                      ))}
                    </ul>
                  </div>
                </article>
              </Reveal>
            )
          })}
        </div>

        <Reveal delay={0.3}>
          <div className="mt-8 text-center">
            <p className="cosmic-text-base text-[#a1a1aa] max-w-xl mx-auto mb-6">
              Your category not listed? The physics of attention is universal. The instrument adapts.
            </p>
            <Link
              href="/#contact"
              className="inline-flex items-center gap-2 cosmic-text-sm font-medium text-[#8B7CF6] underline-offset-4 transition-colors hover:text-[#6E5CE6]"
            >
              Discuss your flagship <ArrowRight size={14} strokeWidth={2.5} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
