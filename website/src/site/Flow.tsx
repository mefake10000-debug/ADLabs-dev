"use client"

import { motion } from "framer-motion"
import { Plug, Brain, TrendingUp, RefreshCcw, Lightbulb } from "lucide-react"
import { Reveal } from "../components/Reveal"

const EASE = [0.22, 1, 0.36, 1] as const

const LOOP = [
  {
    icon: Plug,
    t: "1 · Sense",
    d: "The sensor reads the physical street: who passed, who paused, who entered, and how long they stayed.",
    tag: "on-device",
    color: "#8B7CF6",
  },
  {
    icon: Brain,
    t: "2 · Learn",
    d: "The engine builds a model of your store's normal — your footfall curve, your stop rate, your dead zones.",
    tag: "your store's rhythm",
    color: "#5ac8fa",
  },
  {
    icon: TrendingUp,
    t: "3 · Predict",
    d: "Before you act, the model forecasts: this window rotation should lift stop rate; this relight should fix Zone F1.",
    tag: "evidence-backed",
    color: "#3ECF8E",
  },
  {
    icon: Lightbulb,
    t: "4 · Act",
    d: "The Monday Brief delivers the action: three decisions with the numbers behind each one.",
    tag: "verdict-grade",
    color: "#8B7CF6",
  },
  {
    icon: RefreshCcw,
    t: "5 · Reinforce",
    d: "Every action feeds back into the model. The next prediction is smarter. The sensor learns your store the way your staff would — only faster.",
    tag: "getting sharper every week",
    color: "#f5726e",
  },
]

function Arrow({ color = "#8B7CF6" }: { color?: string }) {
  return (
    <div className="flex items-center px-1 text-[#86868b]/40">
      <svg viewBox="0 0 48 12" className="h-3 w-8" aria-hidden>
        <motion.line
          x1="0" y1="6" x2="40" y2="6"
          stroke={color}
          strokeWidth="1.5"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          transition={{ duration: 0.6, ease: EASE }}
          viewport={{ once: true }}
        />
        <motion.polygon
          points="40,2 48,6 40,10"
          fill={color}
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.3 }}
          viewport={{ once: true }}
        />
      </svg>
    </div>
  )
}

export function Flow() {
  return (
    <section id="flow" className="relative scroll-mt-24 py-12 sm:py-16 lg:py-20 overflow-hidden" style={{ background: "#05050a" }}>
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <img src="/images/in-store-zones.jpg" alt="" className="w-full h-full object-cover opacity-[0.06]" />
        <div className="absolute inset-0" style={{ background: "var(--cosmic-gradient-void)" }} />
      </div>
      <div className="relative z-10 mx-auto max-w-[1200px] px-6">
        <Reveal>
          <div className="max-w-2xl">
            <p className="cosmic-text-xs font-semibold uppercase tracking-[0.16em] text-[#8B7CF6]">The Intelligence Loop</p>
            <h2 className="mt-2 cosmic-text-3xl font-bold leading-[1.08] tracking-[-0.025em] text-[#f5f5f7] sm:cosmic-text-4xl">
              This is how the sensor gets smarter — every week.
            </h2>
            <p className="mt-3 max-w-xl cosmic-text-base leading-relaxed text-[#a1a1aa]">
              A sensor that only counts is useful. A sensor that learns, predicts, and recommends is a business partner. Here is how the loop works.
            </p>
          </div>
        </Reveal>

        <div className="mt-10 hidden gap-0 lg:flex">
          {LOOP.map((step, i) => {
            const Icon = step.icon
            return (
              <div key={step.t} className="flex items-center">
                <Reveal delay={i * 0.08} className="flex-1 min-w-0">
                  <div className="relative h-full rounded-2xl border border-white/10 bg-[#12121a] p-5 transition-colors hover:border-[#8B7CF6]/30">
                    <span className="absolute left-5 top-5 grid h-9 w-9 place-items-center rounded-xl" style={{ background: `${step.color}18` }}>
                      <Icon size={17} strokeWidth={2.2} style={{ color: step.color }} />
                    </span>
                    <span className="mt-11 block cosmic-text-xs font-semibold text-[#86868b]">{step.t}</span>
                    <h3 className="mt-1.5 cosmic-text-sm font-semibold leading-snug text-[#f5f5f7]">{step.d}</h3>
                    <span className="mt-2 inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/4 px-2.5 py-0.5 cosmic-text-2xs font-medium text-[#86868b]">{step.tag}</span>
                  </div>
                </Reveal>
                {i < LOOP.length - 1 && <Arrow color={step.color} />}
              </div>
            )
          })}
        </div>

        <div className="mt-8 space-y-3 lg:hidden">
          {LOOP.map((step, i) => {
            const Icon = step.icon
            return (
              <Reveal key={step.t} delay={i * 0.06}>
                <div className="flex gap-4 rounded-2xl border border-white/10 bg-[#12121a] p-5">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl" style={{ background: `${step.color}18` }}>
                    <Icon size={17} strokeWidth={2.2} style={{ color: step.color }} />
                  </span>
                  <div>
                    <span className="block cosmic-text-xs font-semibold text-[#86868b]">{step.t}</span>
                    <h3 className="mt-1 cosmic-text-sm font-semibold leading-snug text-[#f5f5f7]">{step.d}</h3>
                    <span className="mt-1.5 inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/4 px-2.5 py-0.5 cosmic-text-2xs font-medium text-[#86868b]">{step.tag}</span>
                  </div>
                </div>
              </Reveal>
            )
          })}
        </div>

        <Reveal delay={0.3}>
          <div className="mt-10 flex flex-col items-center justify-center gap-3 rounded-2xl border border-[#8B7CF6]/15 bg-[#8B7CF6]/5 p-6 text-center sm:flex-row sm:text-left">
            <div className="flex -space-x-1.5">
              {["#8B7CF6", "#5ac8fa", "#3ECF8E"].map((c) => (
                <span key={c} className="h-7 w-7 rounded-full border-2 border-[#05050a]" style={{ background: c }} />
              ))}
            </div>
            <div>
              <p className="cosmic-text-sm font-semibold text-[#f5f5f7]">Every week, the loop tightens.</p>
              <p className="cosmic-text-xs text-[#86868b]">The more your store is measured, the sharper the next prediction becomes. This is how offline retail starts to learn — for the first time.</p>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
