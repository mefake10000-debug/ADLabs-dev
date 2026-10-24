import { ShieldCheck, Lock, Eye, Database, WifiOff, Zap } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { Section } from "../components/Section"
import { SectionHeader } from "../components/SectionHeader"
import { FlipCard, AnswerPanel } from "../components/FlipCard"
import { PRIVACY } from "../data/site"

const PRINCIPLE_ICONS = [Lock, Eye, Database]

export function Privacy() {
  const p = PRIVACY

  return (
    <Section id="privacy" className="site-scope scroll-mt-24" bg="var(--cosmic-deep)">
      <div className="mx-auto max-w-[1200px] px-6 relative z-10">
        <div className="max-w-2xl">
          <SectionHeader index={p.index} kicker={p.kicker} sub={p.sub}>
            {p.h2}
          </SectionHeader>
        </div>

        <Reveal delay={0.1}>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {p.principles.map((pr, i) => {
              const Icon = PRINCIPLE_ICONS[i]
              return (
                <FlipCard
                  key={pr.num}
                  back={
                    <AnswerPanel
                      eyebrow="IN PRACTICE"
                      chips={pr.chips}
                      note={pr.answer}
                    />
                  }
                  front={
                    <article className="cosmic-card group flex h-full flex-col rounded-2xl p-7 transition-all duration-300 hover:-translate-y-1 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
                      <div className="flex items-start justify-between mb-6">
                        <span className="grid h-14 w-14 place-items-center rounded-2xl cosmic-gradient-violet/10 cosmic-border text-[#8B7CF6] transition-transform duration-500 group-hover:scale-110 group-hover:rotate-3">
                          <Icon size={24} strokeWidth={1.8} />
                        </span>
                        <span className="cosmic-text-xs font-semibold" style={{ color: "var(--cosmic-text-muted)" }}>{pr.num}</span>
                      </div>
                      <h3 className="cosmic-text-xl font-semibold cosmic-text mb-3">{pr.title}</h3>
                      <p className="cosmic-text-base leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>{pr.desc}</p>
                      <div className="mt-6 flex items-center gap-2 cosmic-text-xs font-medium" style={{ color: "var(--cosmic-violet)" }}>
                        <span>Tap to reveal</span>
                      </div>
                    </article>
                  }
                  className="min-h-[280px]"
                />
              )
            })}
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            {[
              { icon: ShieldCheck, label: "DPDP 2023 COMPLIANT", color: "#8B7CF6" },
              { icon: Database, label: "GDPR-ALIGNED", color: "#8B7CF6" },
              { icon: Eye, label: "ZERO BIOMETRICS", color: "#ff3b30" },
              { icon: WifiOff, label: "OFFLINE-CAPABLE", color: "#8B7CF6" },
              { icon: Zap, label: "12W EDGE", color: "#8B7CF6" },
            ].map((badge) => (
              <span
                key={badge.label}
                className="inline-flex items-center gap-2 rounded-full cosmic-border px-5 py-2.5 cosmic-text-xs font-semibold transition-all duration-300"
                style={{
                  borderColor: `${badge.color}30`,
                  background: "var(--cosmic-gradient-card)",
                  color: badge.color,
                }}
              >
                <badge.icon size={14} strokeWidth={2} />
                {badge.label}
              </span>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.25}>
          <div className="mx-auto mt-10 max-w-3xl cosmic-card-glow p-6 sm:p-8">
            <p className="cosmic-text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--cosmic-violet)" }}>{p.dpdp.title}</p>
            <p className="mt-3 cosmic-text-base leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>{p.dpdp.body}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {p.dpdp.chips.map((c) => (
                <span key={c} className="rounded-full cosmic-gradient-violet/10 cosmic-border px-4 py-2 cosmic-text-xs font-semibold" style={{ color: "var(--cosmic-violet)" }}>
                  {c}
                </span>
              ))}
            </div>
            <p className="mt-4 cosmic-text-xs" style={{ color: "var(--cosmic-text-muted)" }}>{p.dpdp.source}</p>
          </div>
        </Reveal>
      </div>
    </Section>
  )
}
