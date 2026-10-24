"use client"

import { useEffect, useState } from "react"
import { Reveal } from "../components/Reveal"
import { SENSOR } from "../data/site"
import { Zap, Clock, Camera, Cpu, Wifi, Shield } from "lucide-react"

function useClock(initial = "08:41:07") {
  const [t, setT] = useState(initial)
  useEffect(() => {
    const tick = () =>
      setT(new Date().toLocaleTimeString("en-IN", { hour12: false }))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])
  return t
}

export function Sensor() {
  const clock = useClock()

  return (
    <section id="sensor" className="relative py-24 section-cosmic cosmic-bg" style={{ scrollMarginTop: "4rem" }}>
      {/* Subtle signal texture */}
      <div className="absolute inset-0">
        <img
          src="/images/renders/data-flow.jpg"
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-30 mix-blend-screen"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#05050a] via-[#05050a]/85 to-[#05050a]" />
      </div>

      <div className="relative z-10 mx-auto max-w-[1200px] px-6">
        {/* Hook */}
        <Reveal>
          <div className="text-center mb-12">
            <span className="badge-cosmic">The Solution</span>
            <h2 className="mt-6 visual-headline">
              One box. Your cameras. Zero faces.
            </h2>
            <p className="mt-4 visual-sub max-w-[600px] mx-auto">
              {SENSOR.sub}
            </p>
            <p className="mt-5 font-mono cosmic-text-2xs tracking-[0.14em] text-white/45">
              CAMERA IN · VERDICT OUT · NOBODY IN BETWEEN
            </p>
          </div>
        </Reveal>

        {/* The product — feed in, verdict out */}
        <Reveal delay={0.1}>
          <div className="grid gap-6 lg:grid-cols-2 mb-12">
            {/* Live telemetry — what the box reads */}
            <div className="relative flex flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#0b0b12]/90 backdrop-blur-md">
              {/* Chrome */}
              <div className="relative z-10 flex items-center gap-2 border-b border-white/10 bg-white/[0.02] px-4 py-3">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#ff4d5e] opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[#ff4d5e]" />
                </span>
                <span className="font-mono cosmic-text-2xs tracking-[0.14em] text-white/55">REC · CAM 02 · {clock}</span>
                <span className="ml-auto font-mono cosmic-text-2xs tracking-[0.14em] text-white/40">GAZE 94%</span>
              </div>

              {/* Zone readouts */}
              <div className="space-y-5 px-5 py-5">
                {[
                  { zone: "ZONE 01 · DOOR", k: "PASS", v: "2,481", sub: "walked past · 18:00 peak", bar: 78, color: "#8B7CF6" },
                  { zone: "ZONE 02 · THRESHOLD", k: "ENTER", v: "39", sub: "crossed in · 16:1 into store", bar: 12, color: "#5ac8fa" },
                  { zone: "ZONE 03 · DISPLAY", k: "STOP", v: "186", sub: "paused ≥ 4s · gaze 78%", bar: 41, color: "#3ECF8E" },
                ].map((r) => (
                  <div key={r.zone}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="font-mono cosmic-text-2xs tracking-[0.18em] text-white/40">{r.zone}</span>
                      <span className="font-mono cosmic-text-2xl font-bold leading-none" style={{ color: r.color }}>{r.v}</span>
                    </div>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="font-mono cosmic-text-2xs tracking-[0.18em]" style={{ color: r.color }}>{r.k}</span>
                      <span className="cosmic-text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>{r.sub}</span>
                    </div>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/5">
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${r.bar}%`, background: r.color, opacity: 0.75 }} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Live counter strip */}
              <div className="mt-auto grid grid-cols-3 border-t border-white/10" style={{ background: "rgba(255,255,255,0.02)" }}>
                {[
                  ["PASS", "2,481", "walked past", "#8B7CF6"],
                  ["STOP", "186", "paused ≥ 4s", "#3ECF8E"],
                  ["ENTER", "39", "crossed in", "#5ac8fa"],
                ].map(([k, v, sub, c]) => (
                  <div key={k} className="px-4 py-3.5">
                    <p className="font-mono cosmic-text-2xs tracking-[0.14em] text-white/35">{k}</p>
                    <p className="mt-0.5 font-mono cosmic-text-lg font-bold" style={{ color: c }}>{v}</p>
                    <p className="mt-0.5 font-mono cosmic-text-2xs text-white/40">{sub}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Monday Brief — what comes out of the box */}
            <div className="relative flex flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#0b0b12]/90 backdrop-blur-md">
              {/* Chrome */}
              <div className="relative z-10 flex items-center gap-2 border-b border-white/10 bg-white/[0.02] px-4 py-3">
                <span className="h-2 w-2 rounded-full bg-[#ff5f57]" />
                <span className="h-2 w-2 rounded-full bg-[#febc2e]" />
                <span className="h-2 w-2 rounded-full bg-[#28c840]" />
                <span className="ml-2 truncate font-mono cosmic-text-2xs text-white/40">dashboard.adlabs.in / highstreet-01</span>
              </div>

              <div className="flex-1 px-5 py-5">
                <div className="flex items-center justify-between">
                  <p className="font-mono cosmic-text-2xs tracking-[0.18em] text-white/40">MONDAY BRIEF</p>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-[#3ECF8E]/40 bg-[#3ECF8E]/10 px-2.5 py-1 font-mono cosmic-text-2xs text-[#6effb0]">
                    <span className="h-1 w-1 rounded-full bg-[#3ECF8E]" />
                    VERDICT READY · 07:01 AM
                  </span>
                </div>

                <div className="mt-5 space-y-3">
                  {[
                    { n: "01", t: "Move rotation A to window 2", d: "+2.9% stops vs current", v: "+2.9%", c: "#3ECF8E" },
                    { n: "02", t: "Restock display zone 03", d: "dwell up 12% since Thursday", v: "+12%", c: "#5ac8fa" },
                    { n: "03", t: "Test Tuesday evening layout", d: "convert passerby dip −6s", v: "−6s", c: "#8B7CF6" },
                  ].map((a) => (
                    <div key={a.n} className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3.5">
                      <span className="font-mono cosmic-text-2xs text-white/30">{a.n}</span>
                      <div className="min-w-0 flex-1">
                        <p className="cosmic-text-sm font-semibold text-[#f5f5f7]">{a.t}</p>
                        <p className="mt-0.5 cosmic-text-2xs text-white/40">{a.d}</p>
                      </div>
                      <span className="font-mono cosmic-text-sm font-bold" style={{ color: a.c }}>{a.v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Morning stats */}
              <div className="grid grid-cols-3 border-t border-white/10" style={{ background: "rgba(255,255,255,0.02)" }}>
                {[
                  ["PEOPLE", "2,706", "counted"],
                  ["DWELL", "4.6s", "avg on display"],
                  ["SURGE", "+12%", "vs Friday"],
                ].map(([k, v, sub]) => (
                  <div key={k} className="px-4 py-3.5">
                    <p className="font-mono cosmic-text-2xs tracking-[0.14em] text-white/35">{k}</p>
                    <p className="mt-0.5 font-mono cosmic-text-lg font-bold text-white">{v}</p>
                    <p className="mt-0.5 font-mono cosmic-text-2xs text-white/40">{sub}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>

        {/* The hardware */}
        <Reveal delay={0.15}>
          <div className="relative mb-12 flex flex-col items-center justify-center overflow-hidden rounded-3xl cosmic-card-glow p-8 text-center sm:p-12">
            <div className="absolute inset-0 bg-[radial-gradient(520px_420px_at_50%_38%,rgba(139,124,246,0.22),transparent_70%)]" />
            <img
              src="/images/renders/sensor-render.png"
              alt="Edge Observer device"
              className="relative mx-auto w-full max-w-[420px] mix-blend-screen"
              style={{ filter: "drop-shadow(0 0 60px rgba(139,124,246,0.4))" }}
            />

            {/* Spec callouts */}
            <div className="absolute left-6 top-8 hidden rounded-lg border border-white/10 bg-black/50 px-3 py-2 font-mono cosmic-text-2xs tracking-[0.12em] text-white/85 backdrop-blur-md lg:block">
              HAILO-8L · 13 TOPS
            </div>
            <div className="absolute right-6 top-24 hidden rounded-lg border border-white/10 bg-black/50 px-3 py-2 font-mono cosmic-text-2xs tracking-[0.12em] text-white/85 backdrop-blur-md lg:block">
              POE · 12W
            </div>
            <div className="absolute bottom-24 left-6 hidden rounded-lg border border-white/10 bg-black/50 px-3 py-2 font-mono cosmic-text-2xs tracking-[0.12em] text-white/85 backdrop-blur-md lg:block">
              RTSP · YOUR CAMERAS
            </div>

            <div className="relative mt-2 cosmic-text-2xl font-bold cosmic-text">Edge Observer</div>
            <div className="relative mt-2 cosmic-text-sm" style={{ color: "var(--cosmic-text-dim)" }}>
              One box. Your cameras. Zero faces. Every morning, a verdict.
            </div>
          </div>
        </Reveal>

        {/* Insight ribbon */}
        <Reveal delay={0.15}>
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              { icon: Cpu, k: "On-device, not cloud", v: "13 TOPS on 12 watts", d: "Inference runs on the box. Nothing leaves the store except verdicts." },
              { icon: Clock, k: "Real-time", v: "< 80ms per frame", d: "Stops, dwell and counts resolve the second they happen on camera." },
              { icon: Shield, k: "Zero faces, forever", v: "Privacy by architecture", d: "The model classifies motion and pose — there is no face pipeline to leak." },
            ].map((i) => (
              <div key={i.k} className="cosmic-card p-6">
                <i.icon size={20} className="mb-3 text-[#8B7CF6]" />
                <p className="cosmic-text-xs font-semibold uppercase tracking-[0.14em] text-[#8B7CF6]">{i.k}</p>
                <p className="mt-2 cosmic-text-lg font-bold text-white">{i.v}</p>
                <p className="mt-2 cosmic-text-sm leading-relaxed" style={{ color: "var(--cosmic-text-dim)" }}>{i.d}</p>
              </div>
            ))}
          </div>
        </Reveal>

        {/* Visual specs */}
        <Reveal delay={0.2}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { icon: Zap, value: "12W", label: "Power" },
              { icon: Clock, value: "5 min", label: "Install" },
              { icon: Camera, value: "RTSP", label: "Cameras" },
              { icon: Cpu, value: "Hailo-8L", label: "AI Chip" },
              { icon: Wifi, value: "Offline", label: "Works" },
              { icon: Shield, value: "Zero", label: "Faces" },
            ].map((spec) => (
              <div key={spec.label} className="cosmic-card p-6 text-center h-full">
                <spec.icon size={24} className="text-[#8B7CF6] mx-auto mb-3" />
                <div className="cosmic-text-xl font-bold mb-1">{spec.value}</div>
                <div className="cosmic-text-xs" style={{ color: "var(--cosmic-text-dim)" }}>{spec.label}</div>
              </div>
            ))}
          </div>
        </Reveal>

        {/* Install steps */}
        <Reveal delay={0.3}>
          <div className="mt-16 max-w-[800px] mx-auto">
            <h3 className="text-center cosmic-text-2xl font-bold text-white mb-8">Live in 3 steps</h3>
            <div className="grid gap-6 sm:grid-cols-3">
              {[
                { num: "01", title: "Connect", desc: "Plug into your existing cameras" },
                { num: "02", title: "Calibrate", desc: "Map zones in 5 minutes" },
                { num: "03", title: "See data", desc: "Dashboard live next morning" },
              ].map((step) => (
                <div key={step.num} className="cosmic-card p-6 text-center">
                  <div className="cosmic-text-3xl font-bold text-[#8B7CF6]">{step.num}</div>
                  <div className="mt-2 cosmic-text-lg font-semibold text-white">{step.title}</div>
                  <div className="mt-2 cosmic-text-sm text-white/60">{step.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
