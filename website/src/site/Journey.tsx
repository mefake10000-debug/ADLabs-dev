import { Reveal } from "../components/Reveal"
import { SectionHeader } from "../components/SectionHeader"
import { JOURNEY } from "../data/site"
import { Footprints, Eye, DoorOpen, Radar, Hand } from "lucide-react"
import { motion, useReducedMotion } from "framer-motion"

const STEP_ICONS = [Footprints, Eye, DoorOpen, Radar, Hand]

const EASE = [0.25, 1, 0.5, 1] as const

export function Journey() {
  const reduce = useReducedMotion()
  const j = JOURNEY
  const max = Math.max(...j.bars.map((b) => b.value))
  const rates = j.steps.map((s) => s.rate)
  return (
    <section id="journey" className="scroll-mt-24 border-y border-white/8 bg-[#12121a] py-12 sm:py-16 lg:py-20">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="grid items-end gap-6 lg:grid-cols-[1fr_1fr]">
          <SectionHeader index={j.index} kicker={j.kicker} sub={j.sub}>
            {j.h2}
          </SectionHeader>
          <Reveal delay={0.1}>
            <div className="site-card p-8">
              <div className="flex items-center justify-between mb-6">
                <p className="cosmic-text-xs font-semibold uppercase tracking-normal text-[#a1a1aa]">
                  {j.funnelLabel}
                </p>
                <span className="rounded-full bg-[#8B7CF6]/10 px-3 py-1 cosmic-text-2xs font-semibold uppercase tracking-wide text-[#8B7CF6]">
                  1 day · live
                </span>
              </div>
              <p className="cosmic-text-xs font-medium text-[#86868b] mb-6">{j.funnelSub}</p>
              <div className="flex flex-col gap-4">
                {j.bars.map((b, i) => (
                  <div key={b.label} className="flex items-center gap-4">
                    <div className="w-14 shrink-0">
                      <span className="block text-right cosmic-text-xs font-semibold uppercase tracking-normal text-[#a1a1aa]">
                        {b.label}
                      </span>
                      {i > 0 && (
                        <span className="mt-0.5 block text-right cosmic-text-2xs font-semibold tracking-wide text-[#8B7CF6]/80">
                          {rates[i]}
                        </span>
                      )}
                    </div>
                    <div className="h-8 flex-1 overflow-hidden rounded-xl bg-white/5">
                      <motion.div
                        className="flex h-full items-center justify-end rounded-xl pr-3"
                        initial={reduce ? false : { width: "6%" }}
                        whileInView={{ width: `${Math.max((b.value / max) * 100, 8)}%` }}
                        viewport={{ once: true, margin: "-40px" }}
                        transition={{ duration: 1, ease: EASE, delay: i * 0.08 }}
                        style={{
                          background: i === j.bars.length - 1
                            ? "linear-gradient(90deg, #8B7CF6, #6E5CE6)"
                            : `rgba(139,124,246,${0.4 + i * 0.12})`,
                        }}
                      >
                        <span className="cosmic-text-xs font-bold text-[#05050a]">
                          {b.value.toLocaleString("en-US")}
                        </span>
                      </motion.div>
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-5 border-t border-white/8 pt-4 cosmic-text-2xs font-medium tracking-wide text-[#86868b]">
                Rate = conversion from the stage above · pass → stop → enter → explore → engage
              </p>
            </div>
          </Reveal>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {j.steps.map((s, i) => {
            const StepIcon = STEP_ICONS[i]
            return (
            <Reveal key={s.step} delay={i * 0.08}>
              <article className="site-card site-card-glare group flex h-full min-h-[280px] flex-col p-6">
                <div className="flex items-center justify-between">
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-[#8B7CF6]/10 text-[#8B7CF6] transition-all duration-300 group-hover:scale-110">
                    {StepIcon && <StepIcon size={19} strokeWidth={1.9} />}
                  </span>
                  <span className="cosmic-text-xs font-semibold text-[#86868b]">{s.step}</span>
                </div>
                <div className="mt-4 flex items-baseline justify-between">
                  <h3 className="cosmic-text-xl font-bold text-[#f5f5f7]">{s.name}</h3>
                </div>
                <p className="mt-1 cosmic-text-xs font-medium uppercase tracking-normal text-[#a1a1aa]">
                  {s.countLabel}
                </p>
                <p className="mt-3 flex-1 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{s.desc}</p>
                <div className="mt-5 pt-4 border-t border-white/8">
                  <p className="cosmic-text-xl font-bold font-num text-[#8B7CF6]">{s.count.toLocaleString("en-US")}</p>
                  <p className="mt-0.5 cosmic-text-sm font-semibold text-[#f5f5f7]">{s.rate} · {s.rateLabel}</p>
                  {s.metrics.map((m) => (
                    <p key={m} className="mt-2 cosmic-text-xs text-[#86868b]">
                      {m}
                    </p>
                  ))}
                </div>
              </article>
            </Reveal>
            )
          })}
        </div>
      <p className="mt-6 max-w-2xl cosmic-text-xs leading-relaxed text-[#86868b]">
          <span className="mr-2 inline-block h-3 w-px translate-y-0.5 bg-[#8B7CF6]/60" />
          {j.demoNote}
        </p>
      </div>
    </section>
  )
}
