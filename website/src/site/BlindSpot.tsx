import { Reveal } from "../components/Reveal"
import { BLINDSPOT } from "../data/site"
import { Eye, Users, DoorOpen } from "lucide-react"
import { FlipCard, AnswerPanel } from "../components/FlipCard"

export function BlindSpot() {
  const b = BLINDSPOT

  const cards = [
    {
      icon: Users,
      metric: "Example",
      label: "PASS-BY SIGNAL",
      desc: "People moving past a store can be invisible to its point-of-sale system.",
      color: "#8B7CF6",
      img: "/images/blindspot-pass.jpg",
      insight: "Pass-by traffic can show how many people had a chance to notice the storefront.",
      chips: ["Pass-by count", "Peak hour breakdown", "Directional flow"]
    },
    {
      icon: Eye,
      metric: "Example",
      label: "WINDOW STOP",
      desc: "A pause near a display can be measured when the camera view and zone are calibrated.",
      color: "#3ECF8E",
      img: "/images/blindspot-stop.jpg",
      insight: "A stop is an observed pause, not proof of a purchase or a person's intent.",
      chips: ["Dwell time", "Gaze heatmap", "Return rate"]
    },
    {
      icon: DoorOpen,
      metric: "Example",
      label: "STORE ENTRY",
      desc: "An entrance line can count crossings when it is placed and checked against the footage.",
      color: "#5ac8fa",
      img: "/images/blindspot-enter.jpg",
      insight: "An entry count describes a line crossing. It does not establish exploration, intent, or a sale.",
      chips: ["Conversion rate", "Zone paths", "Basket size proxy"]
    },
  ]

  return (
    <section id="blindspot" className="relative py-24 section-cosmic cosmic-bg" style={{ scrollMarginTop: "4rem" }}>
      <div className="relative z-10 mx-auto max-w-[1200px] px-6">
        {/* Hook */}
        <Reveal>
          <div className="text-center mb-16">
            <span className="badge-cosmic">The Problem</span>
            <span className="ml-3 inline-flex rounded-full border border-white/15 px-3 py-1 font-mono text-[10px] tracking-[0.14em] text-white/55">
              ILLUSTRATIVE EXAMPLE · NOT A STORE REPORT
            </span>
            <h2 className="mt-6 visual-headline">
              {b.h2a}
              <br />
              <span style={{ color: "var(--cosmic-violet)" }}>{b.h2b}</span>
            </h2>
            <p className="mt-4 visual-sub max-w-[600px] mx-auto">
              Every store counts who walked in. Almost no one knows who walked past. That's the blind spot.
            </p>
          </div>
        </Reveal>

        {/* Visual cards with background images + flip cards */}
        <div className="grid gap-6 md:grid-cols-3">
          {cards.map((card, i) => (
            <Reveal key={card.label} delay={i * 0.1}>
              <FlipCard
                back={
                  <AnswerPanel
                    eyebrow="THE INSIGHT"
                    chips={card.chips}
                    note={card.insight}
                  />
                }
                front={
                  <div className="cosmic-card-glow overflow-hidden text-center h-full">
                    <div className="relative h-40 overflow-hidden">
                      <img src={card.img} alt="" className="img-grade absolute inset-0 w-full h-full object-cover opacity-25" />
                      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[var(--cosmic-surface)]" />
                      <card.icon size={32} style={{ color: card.color }} className="absolute top-6 left-1/2 -translate-x-1/2" />
                    </div>
                    <div className="p-6 -mt-8 relative flex flex-col h-[calc(100%-40px)]">
                      <div className="cosmic-text-4xl font-bold mb-1" style={{ color: card.color }}>
                        {card.metric}
                      </div>
                      <div className="mt-2 cosmic-text-xs font-semibold tracking-[0.2em]" style={{ color: "rgba(255,255,255,0.5)" }}>
                        {card.label}
                      </div>
                      <p className="mt-4 cosmic-text-sm flex-1" style={{ color: "rgba(255,255,255,0.6)" }}>{card.desc}</p>
                      <div className="mt-4 pt-4 border-t border-white/10 text-center">
                        <span className="cosmic-text-2xs font-medium" style={{ color: "var(--cosmic-violet)" }}>
                          Hover or tap for insight →
                        </span>
                      </div>
                    </div>
                  </div>
                }
              />
            </Reveal>
          ))}
        </div>

        {/* Verdict */}
        <Reveal delay={0.3}>
          <div className="mt-16 max-w-[800px] mx-auto">
            <div className="cosmic-card-glow p-8">
              <p className="cosmic-text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--cosmic-violet)" }}>{b.verdictLabel}</p>
              <p className="mt-4 cosmic-text-lg leading-relaxed" style={{ color: "rgba(255,255,255,0.8)" }}>{b.verdict}</p>
              <ul className="mt-6 space-y-3">
                {b.context.map((c) => (
                  <li key={c} className="flex items-start gap-3 cosmic-text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: "var(--cosmic-violet)" }} />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
