"use client"

import { Reveal } from "../components/Reveal"
import { HERO } from "../data/site"
import Link from "next/link"
import { ArrowRight, Eye, Zap, Shield } from "lucide-react"

const hash01 = (i: number, salt: number) => {
  const x = Math.sin(i * 127.1 + salt * 311.7) * 43758.5453
  return x - Math.floor(x)
}

const PARTICLES = [...Array(20)].map((_, i) => ({
  left: hash01(i, 1) * 100,
  top: hash01(i, 2) * 100,
  delay: hash01(i, 3) * 6,
  duration: 4 + hash01(i, 4) * 4,
}))

const RHYTHM = [34, 41, 38, 52, 63, 58, 71, 66, 84, 77, 92, 88, 96, 100]

export function Hero({ onPilot }: { onPilot: () => void }) {
  return (
    <section id="top" className="relative min-h-[100dvh] flex items-center overflow-hidden">
      {/* Pure cosmic backdrop — no photography */}
      <div className="absolute inset-0 bg-[radial-gradient(900px_600px_at_75%_35%,rgba(139,124,246,0.16),transparent_60%),radial-gradient(700px_500px_at_15%_85%,rgba(62,207,142,0.08),transparent_60%)]" />
      <div className="absolute inset-0 cosmic-bg opacity-70" />

      {/* Floating particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {PARTICLES.map((p, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 rounded-full bg-[#8B7CF6]/40 animate-float"
            style={{
              left: `${p.left}%`,
              top: `${p.top}%`,
              animationDelay: `${p.delay}s`,
              animationDuration: `${p.duration}s`,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 mx-auto max-w-[1200px] px-6 py-32">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          {/* Left: The Hook */}
          <div>
            <Reveal>
              <span className="badge-cosmic">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#8B7CF6]" />
                {HERO.kicker}
              </span>
            </Reveal>

            <Reveal delay={0.1}>
              <h1 className="mt-8 visual-headline">
                {HERO.headlineA}
                <br />
                <span className="text-[#8B7CF6]">{HERO.headlineB}</span>
              </h1>
            </Reveal>

            <Reveal delay={0.2}>
              <p className="mt-6 visual-sub max-w-[500px]">
                {HERO.sub}
              </p>
            </Reveal>

            <Reveal delay={0.3}>
              <div className="mt-10 flex flex-wrap items-center gap-4">
                <Link
                  href="/dashboard"
                  className="group inline-flex items-center gap-3 rounded-full bg-[#8B7CF6] px-8 py-4 cosmic-text-base font-semibold text-white transition-all duration-300 hover:bg-[#6E5CE6] active:scale-[0.98]"
                >
                  {HERO.demoCta ?? "See it live"}
                  <ArrowRight size={18} strokeWidth={2.5} className="transition-transform duration-300 group-hover:translate-x-1" />
                </Link>
                <button
                  onClick={onPilot}
                  className="inline-flex items-center gap-2 rounded-full border border-[#8B7CF6]/30 bg-[#8B7CF6]/10 px-8 py-4 cosmic-text-base font-medium text-[#8B7CF6] transition-all duration-300 hover:bg-[#8B7CF6]/20 hover:border-[#8B7CF6]/50 active:scale-[0.98]"
                >
                  {HERO.primaryCta}
                </button>
              </div>
            </Reveal>

            <Reveal delay={0.4}>
              <div className="mt-12 grid grid-cols-3 gap-6">
                {[
                  { icon: Eye, value: "2,481", label: "people counted today", color: "#8B7CF6" },
                  { icon: Zap, value: "7.5%", label: "stopped to look", color: "#3ECF8E" },
                  { icon: Shield, value: "0", label: "faces stored", color: "#5ac8fa" },
                ].map((m) => (
                  <div key={m.label}>
                    <m.icon size={20} style={{ color: m.color }} />
                    <p className="mt-2 font-mono cosmic-text-xl font-bold" style={{ color: m.color }}>{m.value}</p>
                    <p className="mt-1 cosmic-text-xs" style={{ color: "rgba(255,255,255,0.45)" }}>{m.label}</p>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>

          {/* Right: The Product — live snapshot, drawn in code, not photography */}
          <Reveal delay={0.2} y={20} scale={0.98}>
            <div className="relative">
              {/* Soft ambient glow */}
              <div className="absolute -inset-10 bg-[radial-gradient(500px_420px_at_50%_50%,rgba(139,124,246,0.18),transparent_70%)]" />

              <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-[#0b0b12]/90 shadow-[0_0_80px_rgba(0,0,0,0.6)] backdrop-blur-md">
                {/* Monitor chrome */}
                <div className="flex items-center gap-2 border-b border-white/10 bg-white/[0.02] px-4 py-3">
                  <span className="h-2 w-2 rounded-full bg-[#ff5f57]" />
                  <span className="h-2 w-2 rounded-full bg-[#febc2e]" />
                  <span className="h-2 w-2 rounded-full bg-[#28c840]" />
                  <span className="ml-2 truncate font-mono cosmic-text-2xs text-white/40">edge.adlabs.in · highstreet-01</span>
                  <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-[#3ECF8E]/40 bg-[#3ECF8E]/10 px-2.5 py-1 font-mono cosmic-text-2xs text-[#6effb0]">
                    <span className="h-1 w-1 animate-pulse rounded-full bg-[#3ECF8E]" />
                    LIVE
                  </span>
                </div>

                {/* Live readouts */}
                <div className="space-y-5 px-5 py-5">
                  {[
                    { k: "PASS", v: "2,481", sub: "walked past today", bar: 78, color: "#8B7CF6" },
                    { k: "STOP", v: "186", sub: "paused ≥ 4 seconds", bar: 41, color: "#3ECF8E" },
                    { k: "ENTER", v: "39", sub: "crossed the threshold", bar: 9, color: "#5ac8fa" },
                  ].map((r) => (
                    <div key={r.k}>
                      <div className="flex items-baseline justify-between">
                        <span className="font-mono cosmic-text-2xs tracking-[0.18em] text-white/40">{r.k}</span>
                        <span className="font-mono cosmic-text-2xl font-bold leading-none" style={{ color: r.color }}>{r.v}</span>
                      </div>
                      <p className="mt-1 cosmic-text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>{r.sub}</p>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/5">
                        <div className="h-full rounded-full" style={{ width: `${r.bar}%`, background: r.color, opacity: 0.75 }} />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Footfall rhythm */}
                <div className="border-t border-white/10 px-5 py-4">
                  <div className="flex items-center justify-between">
                    <p className="font-mono cosmic-text-2xs tracking-[0.18em] text-white/40">FOOTFALL · 14 DAYS</p>
                    <p className="font-mono cosmic-text-2xs text-[#8B7CF6]">+12%</p>
                  </div>
                  <div className="mt-3 flex h-14 items-end gap-1.5">
                    {RHYTHM.map((h, i) => (
                      <div
                        key={i}
                        className="flex-1 rounded-sm"
                        style={{
                          height: `${h}%`,
                          background: i >= 12 ? "#3ECF8E" : "rgba(139,124,246,0.55)",
                          opacity: 0.85,
                        }}
                      />
                    ))}
                  </div>
                </div>

                {/* Verdict strip */}
                <div className="grid grid-cols-3 border-t border-white/10" style={{ background: "rgba(255,255,255,0.02)" }}>
                  {[
                    ["VERDICT", "ROTATION A", "#8B7CF6"],
                    ["NEXT BRIEF", "MON 07:01", "#3ECF8E"],
                    ["FACES", "0–STORE", "#5ac8fa"],
                  ].map(([k, v, c]) => (
                    <div key={k} className="px-4 py-3.5">
                      <p className="font-mono cosmic-text-2xs tracking-[0.14em] text-white/35">{k}</p>
                      <p className="mt-1 font-mono cosmic-text-sm font-bold" style={{ color: c }}>{v}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
