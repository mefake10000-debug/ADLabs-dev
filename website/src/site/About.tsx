"use client"

import { useState } from "react"
import Link from "next/link"
import { ArrowRight, ArrowUpRight, Shield, Zap, Target, Database, Users, Award, BadgeCheck } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { FlipCard, AnswerPanel } from "../components/FlipCard"
import { Nav } from "./Nav"
import { Footer } from "./Footer"
import { PilotModal } from "./PilotModal"
import { ABOUT } from "../data/site"

export function About() {
  const a = ABOUT
  const [pilot, setPilot] = useState(false)
  const openPilot = () => setPilot(true)

  const principles = [
    { icon: Shield, title: "Privacy by Architecture", desc: "Not a policy. A constraint. The system literally cannot watch — it counts. Zero faces. Zero cloud video. Zero re-identification. By design." },
    { icon: Zap, title: "Evidence Over Opinion", desc: "Every feature ships with its proof chain. If a stat can't be reproduced by hand, it doesn't print. The Monday Brief is audited, not authored." },
    { icon: Target, title: "Verdicts, Not Dashboards", desc: "Numbers that end in a move. The A/B engine decides keep-or-kill. The Monday Brief delivers three actions. No dashboards to babysit." },
    { icon: Database, title: "Store-Specific Intelligence", desc: "Baselines are store-specific. Anomalies surface before they cost. Your Monday is compared to your own history, not a category average." },
    { icon: Users, title: "Built for the Floor", desc: "A 15-minute read for founders, a daily checklist for staff. Each role gets its own view of the same evidence." },
    { icon: Award, title: "Indian Retail First", desc: "Designed for Bandra, Indiranagar, Koregaon Park. Peak hours, festive surges, window realities. Attention is universal; context is local." },
  ]

return (
    <div className="site-scope page-in">
      <Nav onPilot={openPilot} />
      <main>
        {/* 01 — Hero */}
        <section className="relative overflow-hidden cosmic-bg pb-10 pt-24 text-[#f5f5f7] sm:pt-28">
          <div aria-hidden className="pointer-events-none absolute inset-0">
            <img src="/images/hero-storefront.jpg" alt="" className="w-full h-full object-cover opacity-[0.08]" />
            <div className="absolute inset-0" style={{ background: "var(--cosmic-gradient-void)" }} />
          </div>
          <div aria-hidden className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{
            backgroundImage: "linear-gradient(rgba(29,29,31,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(29,29,31,0.5) 1px, transparent 1px)",
            backgroundSize: "80px 80px"
          }} />

          <div className="relative mx-auto max-w-[1200px] px-6">
            <Reveal>
              <div className="flex items-center gap-3 mb-4">
                <span className="font-mono cosmic-text-2xs tracking-[0.18em] cosmic-text-muted">ABOUT</span>
                <span className="section-kicker" style={{ color: "var(--cosmic-violet)" }}>{a.hero.kicker}</span>
              </div>
              <h1 className="mt-4 font-serif headline cosmic-text">
                {a.hero.h2a} <em className="em-accent">{a.hero.h2b}</em>
              </h1>
              <p className="mt-7 max-w-2xl body-lg" style={{ color: "rgba(245,245,247,0.62)" }}>{a.hero.sub}</p>

              <div className="mt-10 flex flex-wrap gap-3">
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 rounded-full cosmic-gradient-violet px-7 py-4 cosmic-text-base font-semibold" style={{ color: "var(--cosmic-void)" }}
                >
                  Explore the live dashboard <ArrowUpRight size={16} strokeWidth={2.6} />
                </Link>
                <button
                  onClick={openPilot}
                  className="rounded-full cosmic-border px-7 py-4 cosmic-text-base font-semibold" style={{ color: "rgba(245,245,247,0.8)" }}
                >
                  Request a pilot seat <ArrowRight size={16} strokeWidth={2.4} />
                </button>
              </div>
            </Reveal>

            {/* Sourced context strip */}
            <Reveal delay={0.25}>
              <dl className="mt-10 grid grid-cols-1 gap-6 border-t border-white/10 pt-8 sm:grid-cols-3 sm:gap-8">
                {a.hero.stats.map((s) => (
                  <div key={s.label}>
                    <dd className="font-mono cosmic-text-3xl font-bold text-[#f5f5f7]">{s.value}</dd>
                    <dt className="mt-2 cosmic-text-xs leading-snug text-[#f5f5f7]/50">{s.label}</dt>
                  </div>
                ))}
              </dl>
            </Reveal>
          </div>
        </section>

        {/* 02 — Vision / Mission */}
        <section className="bg-[#05050a] py-12 sm:py-16 lg:py-20">
          <div className="mx-auto max-w-[1200px] px-6">
            <Reveal>
              <div className="grid gap-6 lg:grid-cols-2">
                <article className="site-card overflow-hidden rounded-3xl p-8 sm:p-10">
                  <div className="relative -mx-8 -mt-8 mb-6 overflow-hidden sm:-mx-10 sm:-mt-10 h-40">
                    <img src="/images/sector-beauty.jpg" alt="" className="img-grade w-full h-full object-cover opacity-35" />
                    <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, transparent, var(--cosmic-surface))" }} />
                  </div>
                  <span className="section-kicker text-[#8B7CF6]">VISION</span>
                  <h2 className="mt-4 cosmic-text-3xl font-semibold leading-tight tracking-[-0.01em] text-[#f5f5f7]">
                    {a.vision.title}
                  </h2>
                  <p className="mt-4 cosmic-text-base leading-relaxed text-[#a1a1aa]">{a.vision.body}</p>
                </article>

                <article className="site-card-featured overflow-hidden rounded-3xl p-8 sm:p-10">
                  <div className="relative -mx-8 -mt-8 mb-6 overflow-hidden sm:-mx-10 sm:-mt-10 h-40">
                    <img src="/images/sector-jewellery.jpg" alt="" className="img-grade w-full h-full object-cover opacity-35" />
                    <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, transparent, #16161f)" }} />
                  </div>
                  <span className="section-kicker text-[#8B7CF6]">MISSION</span>
                  <h2 className="mt-4 cosmic-text-3xl font-semibold leading-tight tracking-[-0.01em] text-[#f5f5f7]">
                    {a.mission.title}
                  </h2>
                  <p className="mt-4 cosmic-text-base leading-relaxed text-[#a1a1aa]">{a.mission.body}</p>
                </article>
              </div>
            </Reveal>

            <Reveal delay={0.15}>
              <div className="mt-8 grid gap-4 sm:grid-cols-3">
                {[
                  { img: "/images/in-store-zones.jpg", label: "The Instrument" },
                  { img: "/images/sector-fashion.jpg", label: "On-Device AI" },
                  { img: "/images/window-after.jpg", label: "Store-Ready" },
                ].map((c) => (
                  <div key={c.label} className="cosmic-card group overflow-hidden rounded-2xl">
                    <div className="relative h-36 overflow-hidden">
                      <img src={c.img} alt={c.label} className="img-grade w-full h-full object-cover opacity-40 transition-transform duration-500 group-hover:scale-105" />
                      <div className="absolute inset-0 flex items-end p-4">
                        <span className="cosmic-text-xs font-semibold tracking-[0.12em] uppercase cosmic-text">{c.label}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        {/* 03 — Problem / Solution */}
        <section className="cosmic-bg py-12 sm:py-16 lg:py-20">
          <div className="mx-auto max-w-[1200px] px-6 relative z-10">
            <div className="grid gap-6 lg:grid-cols-2">
              <Reveal>
                <article className="cosmic-card rounded-3xl p-8 sm:p-10 h-full">
                  <span className="section-kicker" style={{ color: "var(--cosmic-violet)" }}>THE PROBLEM</span>
                  <h2 className="mt-4 cosmic-text-2xl sm:cosmic-text-3xl font-semibold leading-tight tracking-[-0.01em] cosmic-text">
                    {a.problem.title} — {a.problem.lead}
                  </h2>
                  <ul className="mt-6 flex flex-col gap-4">
                    {a.problem.points.map((pt) => (
                      <li key={pt.num} className="flex items-start gap-3">
                        <span className="mt-0.5 shrink-0 font-mono cosmic-text-xs font-bold" style={{ color: "var(--cosmic-violet)" }}>{pt.num}</span>
                        <p className="cosmic-text-base leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>{pt.text}</p>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-8 border-t border-white/10 pt-6">
                    <p className="font-mono cosmic-text-4xl sm:cosmic-text-5xl font-bold" style={{ color: "var(--cosmic-violet)" }}>{a.problem.stat.value}</p>
                    <p className="mt-2 cosmic-text-xs leading-snug" style={{ color: "var(--cosmic-text-muted)" }}>{a.problem.stat.label}</p>
                  </div>
                </article>
              </Reveal>

              <Reveal delay={0.1}>
                <article className="cosmic-card-glow rounded-3xl p-8 sm:p-10 h-full">
                  <span className="section-kicker" style={{ color: "var(--cosmic-violet)" }}>THE SOLUTION</span>
                  <h2 className="mt-4 cosmic-text-2xl sm:cosmic-text-3xl font-semibold leading-tight tracking-[-0.01em] cosmic-text">
                    {a.solution.title}
                  </h2>
                  <p className="mt-3 cosmic-text-base leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>{a.solution.sub}</p>
                  <ul className="mt-6 flex flex-col gap-4">
                    {a.solution.points.map((pt) => (
                      <li key={pt.num} className="flex items-start gap-3">
                        <span className="mt-0.5 shrink-0 font-mono cosmic-text-xs font-bold" style={{ color: "var(--cosmic-violet)" }}>{pt.num}</span>
                        <p className="cosmic-text-base leading-relaxed" style={{ color: "var(--cosmic-text-secondary)" }}>{pt.text}</p>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-8 border-t border-white/10 pt-6">
                    <Link
                      href="/dashboard"
                      className="inline-flex items-center gap-2 font-mono cosmic-text-xs font-bold tracking-[0.08em] transition-colors" style={{ color: "var(--cosmic-violet)" }}
                    >
                      SEE IT LIVE IN THE DASHBOARD <ArrowUpRight size={15} />
                    </Link>
                  </div>
                </article>
              </Reveal>
            </div>
          </div>
        </section>

        {/* 04 — Why it's different */}
        <section className="cosmic-bg py-12 sm:py-16 lg:py-20">
          <div className="mx-auto max-w-[1200px] px-6 relative z-10">
            <Reveal>
              <div className="flex items-center gap-3 mb-4">
                <span className="font-mono cosmic-text-2xs tracking-[0.18em]" style={{ color: "rgba(245,245,247,0.5)" }}>{a.usp.index} /</span>
                <span className="section-kicker" style={{ color: "var(--cosmic-violet)" }}>{a.usp.kicker}</span>
              </div>
              <h2 className="cosmic-text-3xl sm:cosmic-text-4xl font-semibold tracking-[-0.02em] cosmic-text">{a.usp.title}</h2>
              <p className="mt-4 max-w-xl cosmic-text-lg leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>{a.usp.sub}</p>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {a.usp.cards.map((c, i) => (
                  <Reveal key={c.num} delay={i * 0.08} fade>
                    <FlipCard
                      back={<AnswerPanel eyebrow="THE BASIS" note={c.answer} />}
                      front={
                        <article className="cosmic-card group flex h-full flex-col rounded-2xl p-7 transition-all duration-300 hover:-translate-y-1 hover:border-[#8B7CF6]/40">
                          <span className="font-mono cosmic-text-xs font-bold" style={{ color: "var(--cosmic-violet)" }}>{c.num}</span>
                          <h3 className="mt-4 cosmic-text-xl font-semibold leading-tight cosmic-text">{c.title}</h3>
                          <p className="mt-3 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{c.desc}</p>
                        </article>
                      }
                    />
                  </Reveal>
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        {/* 05 — How we build */}
        <section className="bg-[#0c0c14] py-12 sm:py-16 lg:py-20">
          <div className="mx-auto max-w-[1200px] px-6">
            <Reveal>
              <div className="flex items-center gap-3 mb-4">
                <span className="font-mono cosmic-text-xs tracking-[0.18em] text-[#f5f5f7]/50">05 /</span>
                <span className="section-kicker text-[#8B7CF6]">HOW WE BUILD</span>
              </div>
              <h2 className="mt-3 cosmic-text-3xl font-semibold tracking-[-0.02em] text-[#f5f5f7]">Constraints We Design Into the Product</h2>
              <p className="mt-4 max-w-xl cosmic-text-base leading-relaxed text-[#a1a1aa]">Not values on a wall. Constraints we engineer into the system.</p>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                {principles.map((item, i) => (
                  <Reveal key={item.title} delay={i * 0.05}>
                    <div className="site-card group rounded-2xl p-7 transition-all duration-300 hover:-translate-y-1 hover:border-[#8B7CF6]/40">
                      <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[rgba(139,124,246,0.12)] text-[#8B7CF6] mb-4">
                        <item.icon size={20} strokeWidth={2} />
                      </span>
                      <h3 className="cosmic-text-xl font-semibold leading-tight text-[#f5f5f7] mb-3">{item.title}</h3>
                      <p className="cosmic-text-sm leading-relaxed text-[#a1a1aa]">{item.desc}</p>
                    </div>
                  </Reveal>
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        {/* 06 — What we own */}
        <section className="bg-[#05050a] py-12 sm:py-16 lg:py-20">
          <div className="mx-auto max-w-[1200px] px-6">
            <Reveal>
              <div className="flex items-center gap-3 mb-4">
                <span className="font-mono cosmic-text-xs tracking-[0.18em] text-[#f5f5f7]/50">{a.ip.index} /</span>
                <span className="section-kicker text-[#8B7CF6]">{a.ip.kicker}</span>
              </div>
              <h2 className="cosmic-text-3xl font-semibold tracking-[-0.02em] text-[#f5f5f7]">{a.ip.title}</h2>
              <p className="mt-4 max-w-xl cosmic-text-base leading-relaxed text-[#a1a1aa]">{a.ip.sub}</p>
            </Reveal>

            <Reveal delay={0.1}>
              <div className="mt-10 flex flex-col">
                {a.ip.points.map((p, i) => (
                  <Reveal key={p.num} delay={i * 0.05}>
                    <div className="flex flex-col gap-3 border-t border-white/10 py-6 last:border-b sm:flex-row sm:items-baseline sm:gap-8">
                      <span className="font-mono cosmic-text-xs font-bold text-[#8B7CF6]">{p.num}</span>
                      <div className="sm:flex-1">
                        <h3 className="cosmic-text-xl font-semibold leading-tight text-[#f5f5f7]">{p.title}</h3>
                        <p className="mt-1.5 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{p.desc}</p>
                      </div>
                    </div>
                  </Reveal>
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        {/* 07 — Where we are + Team */}
        <section className="bg-[#12121a] py-12 sm:py-16 lg:py-20">
          <div className="mx-auto max-w-[1200px] px-6">
            <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
              <Reveal>
                <article className="site-card-featured rounded-3xl p-8 sm:p-10 h-full">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="font-mono cosmic-text-xs tracking-[0.18em] text-[#f5f5f7]/50">{a.status.index} /</span>
                    <span className="section-kicker text-[#8B7CF6]">{a.status.kicker}</span>
                  </div>
                  <h2 className="cosmic-text-3xl font-semibold leading-tight tracking-[-0.01em] text-[#f5f5f7]">
                    {a.status.title}
                  </h2>
                  <p className="mt-4 max-w-xl cosmic-text-base leading-relaxed text-[#c4c4cc]">{a.status.body}</p>

                  <ul className="mt-6 flex flex-col gap-3">
                    {a.status.points.map((pt) => (
                      <li key={pt.num} className="flex items-center gap-3">
                        <BadgeCheck size={16} strokeWidth={2} className="shrink-0 text-[#8B7CF6]" />
                        <span className="cosmic-text-sm font-medium text-[#e4e4e7]">{pt.text}</span>
                      </li>
                    ))}
                  </ul>

                  <div className="mt-8 flex flex-wrap gap-3">
                    <button
                      onClick={openPilot}
                      className="inline-flex items-center gap-2 rounded-full bg-[#8B7CF6] px-7 py-3.5 cosmic-text-base font-semibold text-[#05050a] transition-all duration-300 hover:-translate-y-0.5 active:scale-[0.98]"
                    >
                      {a.status.cta} <ArrowRight size={16} strokeWidth={2.4} />
                    </button>
                  </div>
                </article>
              </Reveal>

              <Reveal delay={0.1}>
                <div className="site-card rounded-3xl p-8 sm:p-10 h-full flex flex-col">
                  <span className="section-kicker text-[#8B7CF6]">{a.team.kicker}</span>
                  <h2 className="mt-4 cosmic-text-3xl font-semibold leading-tight tracking-[-0.01em] text-[#f5f5f7]">
                    {a.team.title}
                  </h2>
                  <p className="mt-3 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{a.team.sub}</p>
                  <div className="mt-auto pt-8">
                    <Link
                      href="/#team"
                      className="inline-flex items-center gap-2 rounded-full border border-white/15 px-6 py-3.5 cosmic-text-sm font-semibold text-[#f5f5f7] transition-all duration-300 hover:border-white/40 hover:bg-[#05050a] hover:-translate-y-0.5"
                    >
                      Meet the founders <ArrowRight size={16} strokeWidth={2.4} />
                    </Link>
                    <p className="mt-4 cosmic-text-xs leading-relaxed text-[#86868b]">{a.demoNote}</p>
                  </div>
                </div>
              </Reveal>
            </div>
          </div>
        </section>
      </main>
      <Footer />
      <PilotModal open={pilot} onClose={() => setPilot(false)} />
    </div>
  )
}
