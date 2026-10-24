import { Eye, ShieldCheck, Target, ArrowRight, Zap, Users, Award } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { Section } from "../components/Section"
import { SectionHeader } from "../components/SectionHeader"
import { FlipCard, AnswerPanel } from "../components/FlipCard"
import { MISSION } from "../data/site"

const PRINCIPLE_ICONS = [Eye, ShieldCheck, Target]

export function Mission() {
  const m = MISSION
  return (
    <Section id="mission" className="site-scope scroll-mt-24" bg="#0c0c14">
      <div className="mx-auto max-w-[1320px] px-6">
        <SectionHeader index={m.index} kicker={m.kicker} sub={m.sub}>
          {m.h2}
        </SectionHeader>

        <Reveal delay={0.1}>
          <div className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <figure className="group relative min-h-[420px] overflow-hidden rounded-2xl border border-white/10 shadow-xl transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
              <img
                src={m.image}
                alt="A luxury storefront at dusk with passers-by"
                loading="lazy"
                className="absolute inset-0 h-full w-full object-cover transition-transform duration-1000 ease-out group-hover:scale-[1.02]"
              />
              <div aria-hidden className="pointer-events-none absolute inset-0" style={{ background: "linear-gradient(rgba(20,16,34,0.10), transparent 55%, rgba(20,16,34,0.12))", mixBlendMode: "overlay" }} />
              <div aria-hidden className="absolute inset-0" style={{ background: "linear-gradient(160deg, rgba(30,18,58,0.38) 0%, rgba(8,11,30,0.58) 55%, rgba(7,9,26,0.82) 100%)" }} />
              <div aria-hidden className="absolute inset-0" style={{ background: "radial-gradient(600px 280px at 50% 96%, rgba(255,148,60,0.28), transparent 65%)" }} />
              <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
                <div className="absolute -inset-x-8 h-16 animate-scanline bg-gradient-to-b from-transparent via-[#8B7CF6]/15 to-transparent" />
              </div>

              <div className="absolute left-5 top-5 flex items-center gap-2 rounded-full bg-black/65 px-4 py-2 font-mono cosmic-text-2xs tracking-[0.16em] text-white backdrop-blur-sm">
                <Target size={12} strokeWidth={2.2} />
                WHY WE BUILD
              </div>

              <div className="absolute right-5 top-5 flex items-center gap-2 rounded-full border border-white/12 bg-black/55 px-4 py-2.5 font-mono backdrop-blur-sm">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping-soft rounded-full bg-[#8B7CF6] opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[#8B7CF6]" />
                </span>
                <span className="cosmic-text-2xs font-bold tracking-[0.14em] text-white/90">STOP SIGNAL · 21.0% · LIVE</span>
                <svg viewBox="0 0 42 14" className="h-3.5 w-10 ml-2" aria-hidden>
                  <polyline
                    points="0,11 8,8 16,9 24,5 30,6 36,3 42,4"
                    fill="none"
                    stroke="#8B7CF6"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>

              <div className="absolute bottom-6 left-6 right-6 flex items-end justify-between gap-4">
                <div>
                  <p className="font-mono cosmic-text-4xl font-bold text-[#8B7CF6] sm:cosmic-text-5xl">
                    {m.stat.value}
                    {m.stat.suffix}
                  </p>
                  <p className="mt-1.5 max-w-[240px] cosmic-text-xs leading-snug text-white/85">{m.stat.label}</p>
                </div>
                <span className="rounded-full bg-[#8B7CF6] px-5 py-2.5 font-mono cosmic-text-xs font-bold tracking-[0.08em] text-[#05050a]">
                  MADE FOR INDIAN RETAIL
                </span>
              </div>
            </figure>

            <div className="flex flex-col gap-4">
              {m.principles.map((p, i) => {
                const Icon = PRINCIPLE_ICONS[i % PRINCIPLE_ICONS.length]
                return (
                  <Reveal key={p.title} delay={0.05 * i} fade>
                    <FlipCard
                      back={<AnswerPanel eyebrow="IN PRACTICE" chips={p.chips} note={p.answer} />}
                      front={
                        <article className="group rounded-2xl border border-white/12 bg-[#1a1a24]/80 p-7 shadow-lg transition-all duration-300 hover:-translate-y-1 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
                          <div className="flex items-center gap-4">
                            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[rgba(139,124,246,0.12)] text-[#8B7CF6] transition-transform duration-300 group-hover:scale-110">
                              <Icon size={20} strokeWidth={1.9} />
                            </span>
                            <h3 className="font-semibold cosmic-text-xl leading-tight text-[#f5f5f7]">{p.title}</h3>
                            <ArrowRight size={16} className="ml-auto shrink-0 text-[#8B7CF6] opacity-0 transition-all duration-300 group-hover:translate-x-1 group-hover:opacity-100" />
                          </div>
                          <p className="mt-2.5 cosmic-text-sm text-[#a1a1aa]">{p.desc}</p>
                        </article>
                      }
                    />
                  </Reveal>
                )
              })}
            </div>
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="mt-8 rounded-2xl border border-white/10 bg-[#1a1a24]/80 p-8 shadow-lg transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)] sm:p-10 lg:p-14">
            <div className="text-center mb-10">
              <span className="cosmic-text-xs font-semibold uppercase tracking-[0.1em] text-[#8B7CF6]">THE IMPACT</span>
              <h3 className="mt-3 font-semibold cosmic-text-2xl text-[#f5f5f7] sm:cosmic-text-4xl">What Changes When the Storefront Stops Guessing</h3>
              <p className="mt-4 max-w-2xl mx-auto cosmic-text-base text-[#a1a1aa]">Three shifts that compound into a fundamentally different business.</p>
              <p className="mt-4 max-w-2xl mx-auto cosmic-text-xs leading-relaxed text-[#86868b]">
                {m.context}
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {[
                {
                  icon: Users,
                  title: "Staffing Follows the Street",
                  desc: "No more calendar-based rotas. Coverage mirrors the attention curve — peak hours covered, quiet hours lean. Conversion per labor hour rises.",
                  metric: "expected +18% labor efficiency",
                },
                {
                  icon: Zap,
                  title: "Creative Gets Its Verdict",
                  desc: "Every window reset, hero swap, and campaign ships a keep-or-kill verdict. The street decides. Opinion exits. Evidence enters.",
                  metric: "expected +14.6% stop-rate uplift",
                },
                {
                  icon: Award,
                  title: "The Store Learns Itself",
                  desc: "Baselines are store-specific. Anomalies surface before they cost. The Monday Brief writes itself — three actions, fifteen minutes.",
                  metric: "founding cohort · 10 seats",
                },
              ].map((item, i) => (
                <Reveal key={item.title} delay={0.08 * i}>
                  <div className="rounded-2xl border border-white/10 bg-[#12121a] p-6 transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
                    <div className="flex items-center gap-3.5 mb-4">
                      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[rgba(139,124,246,0.12)] text-[#8B7CF6]">
                        <item.icon size={20} strokeWidth={1.9} />
                      </span>
                      <h4 className="font-semibold cosmic-text-xl leading-tight text-[#f5f5f7]">{item.title}</h4>
                    </div>
                    <p className="cosmic-text-sm text-[#a1a1aa] mb-3">{item.desc}</p>
                    <div className="pt-4 border-t border-white/10 flex items-center justify-between">
                      <span className="font-mono cosmic-text-2xs tracking-[0.12em] text-[#8B7CF6]">ILLUSTRATIVE EXPECTATION</span>
                      <span className="font-mono cosmic-text-sm font-bold text-[#8B7CF6]">{item.metric}</span>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </Section>
  )
}
