import { ArrowUpRight, BadgeCheck } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { SectionHeader } from "../components/SectionHeader"
import { PROOF } from "../data/site"
import { FlipCard, AnswerPanel } from "../components/FlipCard"

export function Proof() {
  const p = PROOF
  return (
    <section id="proof" className="scroll-mt-24 py-12 sm:py-16 lg:py-20 cosmic-bg">
      <div className="mx-auto max-w-[1200px] px-6 relative z-10">
        <div className="mx-auto max-w-2xl text-center">
          <SectionHeader index={p.index} kicker={p.kicker} sub={p.sub} center>
            {p.h2}
          </SectionHeader>
          <Reveal delay={0.1}>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
              <span className="rounded-full cosmic-border px-4 py-2 cosmic-text-xs font-medium" style={{ color: "var(--cosmic-text-dim)" }}>
                {p.chip}
              </span>
              <span className="rounded-full cosmic-gradient-violet/10 cosmic-border px-4 py-2 cosmic-text-xs font-medium cosmic-text">
                {p.store}
              </span>
            </div>
          </Reveal>
        </div>

        <div className="relative mx-auto mt-8 grid max-w-4xl gap-6 md:grid-cols-[1fr_auto_1fr] md:items-center">
          <Reveal>
            <FlipCard
              back={
                <AnswerPanel
                  eyebrow="THE CHANGE"
                  chips={["Display rotated", "Peak hour focus", "Color theory applied"]}
                  note="Swapped seasonal for evergreen bestsellers. Moved high-margin to eye level. Removed clutter. Result: 47% more stops."
                />
              }
              front={
                <figure className="cosmic-card group overflow-hidden h-full">
                  <div className="relative aspect-[4/3] overflow-hidden">
                    <img
                      src={p.before.image}
                      alt="Window display before the change"
                      loading="lazy"
                      className="w-full h-full object-cover grayscale-[35%] transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[var(--cosmic-void)]/80 via-transparent to-transparent" />
                    <span className="absolute left-4 top-4 rounded-full bg-black/75 px-3 py-1.5 cosmic-text-xs font-medium text-white border border-white/10">
                      {p.before.label}
                    </span>
                  </div>
                  <figcaption className="p-6">
                    <p className="cosmic-text-4xl font-bold" style={{ color: "var(--cosmic-text-muted)" }}>{p.before.value}</p>
                    <p className="mt-1 cosmic-text-xs font-medium uppercase tracking-normal" style={{ color: "var(--cosmic-text-muted)" }}>
                      {p.before.metric}
                    </p>
                    <p className="mt-3 cosmic-text-base" style={{ color: "var(--cosmic-text-dim)" }}>{p.before.desc}</p>
                  </figcaption>
                </figure>
              }
            />
          </Reveal>

          <Reveal delay={0.1}>
            <div className="flex items-center justify-center">
              <span className="grid h-14 w-14 place-items-center rounded-full cosmic-gradient-violet text-[var(--cosmic-void)] font-bold transition-transform duration-300 hover:scale-110">
                <ArrowUpRight size={26} strokeWidth={2.5} />
              </span>
            </div>
          </Reveal>

          <Reveal delay={0.15}>
            <FlipCard
              back={
                <AnswerPanel
                  eyebrow="THE RESULT"
                  chips={["+47% stops", "+23% enter rate", "+18% revenue"]}
                  note="The new display held attention longer. More people stopped, more entered, more bought. The sensor measured every step."
                />
              }
              front={
                <figure className="cosmic-card-glow overflow-hidden h-full">
                  <div className="relative aspect-[4/3] overflow-hidden">
                    <img
                      src={p.after.image}
                      alt="Window display after the rotation"
                      loading="lazy"
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[var(--cosmic-void)]/60 via-transparent to-transparent" />
                    <span className="absolute left-4 top-4 rounded-full bg-black/75 px-3 py-1.5 cosmic-text-xs font-medium text-white border border-white/10">
                      {p.after.label}
                    </span>
                    <span className="absolute right-4 top-4 flex items-center gap-1.5 rounded-full cosmic-gradient-violet px-3 py-1.5 cosmic-text-xs font-bold" style={{ color: "var(--cosmic-void)" }}>
                      <BadgeCheck size={12} strokeWidth={2.5} />
                      {p.after.badges.join(" · ")}
                    </span>
                  </div>
                  <figcaption className="p-6">
                    <p className="cosmic-text-4xl font-bold cosmic-text">{p.after.value}</p>
                    <p className="mt-1 cosmic-text-xs font-medium uppercase tracking-normal" style={{ color: "var(--cosmic-violet)" }}>
                      {p.after.metric}
                    </p>
                    <p className="mt-3 cosmic-text-base" style={{ color: "var(--cosmic-text-dim)" }}>{p.after.desc}</p>
                  </figcaption>
                </figure>
              }
            />
          </Reveal>
        </div>

        <Reveal delay={0.2}>
          <p className="mt-12 text-center cosmic-text-xl font-bold cosmic-text">
            {p.uplift}
          </p>
        </Reveal>

        <Reveal delay={0.3}>
          <div className="mx-auto mt-8 max-w-3xl space-y-3 cosmic-card-glow p-6">
            <p className="cosmic-text-xs leading-relaxed" style={{ color: "var(--cosmic-text-muted)" }}>
              <span className="mr-2 inline-block h-3 w-px translate-y-0.5" style={{ background: "var(--cosmic-violet)" }} />
              {p.demoNote}
            </p>
            <p className="cosmic-text-xs leading-relaxed" style={{ color: "var(--cosmic-text-muted)" }}>
              <span className="mr-2 inline-block h-3 w-px translate-y-0.5" style={{ background: "var(--cosmic-violet)" }} />
              {p.benchmark}
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
