"use client"

import { useEffect, useRef, useState, useCallback, useMemo } from "react"
import { Play, Pause, ChevronLeft, ChevronRight } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

/* ---------------------------------------------------------------------------
 * Live telemetry types. These mirror GET /api/v1/live, which reads back what
 * the EdgeSight edge node actually pushed. There are no fallback numbers in
 * this file: if the edge node has not reported, the demo says so.
 * ------------------------------------------------------------------------- */

type LiveProduct = {
  category: string
  viewers: number | null
  viewer_observations: number | null
  detections: number | null
  total_dwell_seconds: number | null
  windows: number | null
}

type LiveSeriesPoint = {
  t: string
  occupancy: number | null
  in: number | null
  out: number | null
  engaged: number | null
  attention: number | null
}

type LivePayload = {
  online: boolean
  received: number
  camera: { id: string; store_id: string; device_id: string }
  window_minutes: number
  last_update: string | null
  seconds_since_update: number
  traffic: {
    entries: number | null
    exits: number | null
    occupancy_now: number | null
    peak_occupancy: number | null
    avg_dwell_seconds: number | null
    queue_length: number | null
    queue_alert_active: boolean | null
  }
  engagement: {
    attention_score: number | null
    facing_ratio: number | null
    phone_usage_rate: number | null
    engaged_ratio: number | null
    group_count: number | null
    people_in_groups: number | null
  }
  demographics: {
    sample_size: number | null
    k_anonymity: number
    age_bands: { band: string; count: number; pct: number }[]
    gender_split: { gender: string; count: number; pct: number }[]
    suppressed_count: number | null
    publishable: boolean
    note: string
  }
  products: LiveProduct[]
  series: LiveSeriesPoint[]
}

type Scene = {
  img: string
  color: string
  subtitle: string
  headline: string
  label: string
  details: { t: string; v: string; c: string }[]
  caption: string
  hud: string
  bars?: (number | null)[]
}

const num = (n: number | null | undefined, digits = 0) =>
  n === undefined || n === null || !Number.isFinite(n)
    ? "—"
    : n.toLocaleString("en-US", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })

const pct = (n: number | null | undefined) => n === undefined || n === null ? "—" : `${num(n * 100, 0)}%`

const secs = (n: number | null | undefined) => n === undefined || n === null ? "—" : `${num(n, 1)}s`

const titleCase = (s: string) =>
  s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())

/* ---------------------------------------------------------------------------
 * Scenes are built from the live payload. Marketing copy that used to carry
 * invented numbers (2,481 passersby, 99.7% uptime, +14.6% lift) is gone: every
 * figure below is read out of the database the edge node writes to.
 * ------------------------------------------------------------------------- */
function buildScenes(live: LivePayload | null): Scene[] {
  if (!live) {
    return [
      {
        img: "/images/hero-storefront.jpg",
        color: "#8B7CF6",
        subtitle:
          "Waiting for the edge node to report. Nothing is shown here until a real measurement arrives.",
        headline: "—",
        label: "AWAITING LIVE TELEMETRY",
        details: [
          { t: "Camera", v: "connecting", c: "#8B7CF6" },
          { t: "Transport", v: "HTTPS → Vercel → Postgres", c: "#a1a1aa" },
          { t: "Policy", v: "no placeholder numbers", c: "#a1a1aa" },
        ],
        caption: "Live values replace every metric on this screen once the edge node reports.",
        hud: "CONNECTING · EDGE OBSERVER",
      },
    ]
  }

  const t = live.traffic
  const e = live.engagement
  const d = live.demographics
  const cam = live.camera?.id ?? "camera"

  const topAge = d.age_bands?.[0]
  const topGender = d.gender_split?.[0]
  const topProduct = live.products?.[0]
  const secondProduct = live.products?.[1]
  const liveTag = live.online ? "LIVE" : "STALE"

  const scenes: Scene[] = [
    {
      img: "/images/hero-storefront.jpg",
      color: "#8B7CF6",
      subtitle:
        "The edge node counts every body that crosses the line and every body that leaves it. Nothing about them is remembered.",
      headline: num(t.entries),
      label: "PASSERSBY COUNTED",
      details: [
        { t: "Exited", v: num(t.exits), c: "#a1a1aa" },
        { t: "In Store Now", v: num(t.occupancy_now), c: "#8B7CF6" },
        { t: "Peak Occupancy", v: num(t.peak_occupancy), c: "#a1a1aa" },
      ],
      caption: `${cam} · last ${live.window_minutes} min · ${liveTag} ${live.seconds_since_update}s ago`,
      hud: `${liveTag} FEED · ${cam.toUpperCase()} · EDGE OBSERVER`,
      bars: live.series?.map((s) => s.occupancy),
    },
    {
      img: "/images/sector-beauty.jpg",
      color: "#3ECF8E",
      subtitle:
        "Standing still is a choice. The pose model reads attention from the body, never from a face being tracked.",
      headline: pct(e.engaged_ratio),
      label: "ENGAGED IN ZONE",
      details: [
        { t: "Attention", v: num(e.attention_score, 2), c: "#3ECF8E" },
        { t: "Facing Away", v: pct(e.facing_ratio), c: "#a1a1aa" },
        { t: "On Phone", v: pct(e.phone_usage_rate), c: "#a1a1aa" },
      ],
      caption: `Engaged = inside a calibrated zone · groups detected: ${e.group_count}`,
      hud: `ATTENTION MODEL · ${cam.toUpperCase()} · LIVE`,
    },
    {
      img: "/images/sector-fashion.jpg",
      color: "#5ac8fa",
      subtitle:
        "Age band and gender, published only in cohorts of ten or more. Below that, the cell is withheld entirely.",
      headline: topAge ? `${num(topAge.pct, 0)}%` : "—",
      label: topAge ? `TOP COHORT · ${titleCase(topAge.band)}` : "COHORTS BELOW THRESHOLD",
      details: [
        { t: "Sample", v: `${num(d.sample_size)} people`, c: "#5ac8fa" },
        { t: "Withheld", v: `${num(d.suppressed_count)} under k`, c: "#a1a1aa" },
        {
          t: "Split",
          v: topGender ? `${titleCase(topGender.gender)} ${num(topGender.pct, 0)}%` : "—",
          c: "#a1a1aa",
        },
      ],
      caption: `k = ${d.k_anonymity} · ${d.note}`,
      hud: `k-ANONYMOUS · ${cam.toUpperCase()} · ${d.publishable ? "PUBLISHING" : "WITHHELD"}`,
    },
    {
      img: "/images/sector-premium-retail.jpg",
      color: "#FF9500",
      subtitle:
        "The open-vocabulary detector names what shoppers actually look at, and how long they stand in front of it.",
      headline: topProduct ? num(topProduct.viewers) : "—",
      label: topProduct ? `VIEWERS ON ${topProduct.category.toUpperCase()}` : "NO PRODUCT INTEREST YET",
      details: [
        { t: "Detections", v: topProduct ? num(topProduct.detections) : "—", c: "#FF9500" },
        {
          t: "Dwell",
          v: topProduct ? secs(topProduct.total_dwell_seconds) : "—",
          c: "#a1a1aa",
        },
        {
          t: "Next",
          v: secondProduct ? `${secondProduct.category} ${num(secondProduct.viewers)}` : "—",
          c: "#a1a1aa",
        },
      ],
      caption: "Per-category aggregate over the live window · no images, no embeddings",
      hud: `PRODUCT INTEREST · ${cam.toUpperCase()} · LIVE`,
    },
    {
      img: "/images/sector-jewellery.jpg",
      color: "#AF52DE",
      subtitle:
        "Two calibrated regions: the browsing floor and the checkout queue. Dwell separates a passing glance from a real stop.",
      headline: secs(t.avg_dwell_seconds),
      label: "AVERAGE DWELL",
      details: [
        { t: "Queue Now", v: `${num(t.queue_length)} people`, c: "#AF52DE" },
        { t: "Queue Alert", v: t.queue_alert_active === null ? "—" : t.queue_alert_active ? "ACTIVE" : "clear", c: "#a1a1aa" },
        { t: "Peak", v: num(t.peak_occupancy), c: "#a1a1aa" },
      ],
      caption: "Zone geometry calibrated from the camera's own foot-traffic distribution",
      hud: `ZONES · 2 ROI · ${cam.toUpperCase()}`,
    },
    {
      img: "/images/window-after.jpg",
      color: "#FF2D55",
      subtitle:
        "The part that matters: the edge box throws the video away. What leaves the device is a row of aggregates.",
      headline: "—",
      label: "RETENTION CONFIGURATION",
      details: [
        { t: "Raw footage", v: "not reported by telemetry", c: "#FF2D55" },
        { t: "Cloud storage", v: "deployment policy", c: "#a1a1aa" },
        { t: "Face data", v: "not reported by telemetry", c: "#a1a1aa" },
      ],
      caption: "This telemetry endpoint does not report footage retention or model data handling; verify deployment settings.",
      hud: "PRIVACY STATUS · NOT REPORTED",
    },
  ]

  return scenes
}

const SCENE_MS = 9000
const FADE = 0.8

const hash01 = (i: number, salt: number) => {
  const x = Math.sin(i * 127.1 + salt * 311.7) * 43758.5453
  return x - Math.floor(x)
}

export function Demo() {
  const [idx, setIdx] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [subtitleKey, setSubtitleKey] = useState(0)
  const [live, setLive] = useState<LivePayload | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const obsRef = useRef(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const locked = useRef(false)

  const SCENES = useMemo(() => buildScenes(live), [live])

  // Poll the live telemetry endpoint. The edge node pushes rollups every 10s,
  // so a 5s poll keeps the screen honest without hammering the API.
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const res = await fetch("/api/v1/live?minutes=30", { cache: "no-store" })
        if (!res.ok) return
        const data = (await res.json()) as LivePayload
        if (!cancelled && typeof data?.traffic === "object") {
          setLive(data)
        }
      } catch {
        /* offline: keep the last good payload rather than blanking the screen */
      }
    }
    load()
    const id = setInterval(load, 5000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  const goto = useCallback(
    (i: number) => {
      if (locked.current) return
      locked.current = true
      setIdx(i)
      setProgress(0)
      setSubtitleKey(k => k + 1)
      setTimeout(() => {
        locked.current = false
      }, FADE * 1000 + 100)
    },
    []
  )

  const next = useCallback(() => goto((idx + 1) % SCENES.length), [idx, goto, SCENES.length])
  const prev = useCallback(() => goto((idx - 1 + SCENES.length) % SCENES.length), [idx, goto, SCENES.length])
  const toggle = useCallback(() => setPlaying(p => !p), [])

  // auto-play on viewport
  useEffect(() => {
    const el = containerRef.current
    if (!el || obsRef.current) return
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !obsRef.current) {
        obsRef.current = true
        setPlaying(true)
      }
    }, { threshold: 0.3 })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // auto-advance
  useEffect(() => {
    if (!playing) {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }
    timerRef.current = setInterval(next, SCENE_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [playing, next])

  // progress
  useEffect(() => {
    if (!playing) {
      if (progressRef.current) clearInterval(progressRef.current)
      return
    }
    let step = 0
    progressRef.current = setInterval(() => {
      step += 1
      setProgress((step / 100) * 100)
      if (step >= 100) step = 0
    }, SCENE_MS / 100)
    return () => {
      if (progressRef.current) clearInterval(progressRef.current)
    }
  }, [playing])

  // keyboard
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") next()
      if (e.key === "ArrowLeft") prev()
      if (e.key === " ") {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener("keydown", h)
    return () => window.removeEventListener("keydown", h)
  }, [next, prev, toggle])

  const activeIndex = Math.min(idx, SCENES.length - 1)
  const s = SCENES[activeIndex]

  return (
    <section
      id="demo"
      ref={containerRef}
      className="relative min-h-screen max-h-[95vh] flex flex-col items-center overflow-hidden cosmic-bg"
      style={{ scrollMarginTop: "4rem" }}
    >
      {/* === LAYER 0: BACKGROUND IMAGE with Ken Burns === */}
      <AnimatePresence mode="sync">
        <motion.div
          key={`bg-${idx}`}
          className="absolute inset-0"
          initial={{ opacity: 0, scale: 1.1 }}
          animate={{ opacity: 1, scale: 1.0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: FADE, ease: [0.22, 1, 0.36, 1] }}
        >
          <motion.div
            className="absolute inset-0"
            style={{ backgroundImage: `url(${s.img})`, backgroundSize: "cover", backgroundPosition: "center" }}
            animate={{ scale: [1, 1.06] }}
            transition={{ duration: SCENE_MS / 1000, ease: "linear" }}
          />
          {/* darkening layers */}
          <div className="absolute inset-0" style={{
            background: `radial-gradient(ellipse at 50% 40%, ${s.color}18 0%, transparent 60%), linear-gradient(180deg, ${s.color}10 0%, var(--cosmic-void) 100%)`
          }} />
          <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(3,3,6,0.5) 0%, rgba(3,3,6,0.2) 40%, rgba(3,3,6,0.85) 100%)" }} />
        </motion.div>
      </AnimatePresence>

      {/* === LAYER 1: FLOATING PARTICLES === */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={`p-${idx}-${i}`}
            className="absolute rounded-full"
            style={{
              width: `${1.5 + hash01(i, 5) * 2}px`,
              height: `${1.5 + hash01(i, 6) * 2}px`,
              left: `${hash01(i, 1) * 100}%`,
              top: `${hash01(i, 2) * 100}%`,
              background: s.color,
              opacity: 0,
            }}
            animate={{ opacity: [0, 0.4 + hash01(i, 3) * 0.3, 0], y: [0, -40 - hash01(i, 4) * 80] }}
            transition={{ duration: 3 + hash01(i, 7) * 3, delay: hash01(i, 8) * 2, repeat: Infinity }}
          />
        ))}
      </div>

      {/* === LAYER 2: FILM GRAIN OVERLAY === */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03]" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E\")", backgroundSize: "200px 200px" }} />

      {/* === LAYER 3: LETTERBOX BARS (cinematic framing) === */}
      <div className="absolute top-0 left-0 right-0 h-12 sm:h-16" style={{ background: "linear-gradient(180deg, rgba(3,3,6,0.8) 0%, transparent 100%)" }} />
      <div className="absolute bottom-0 left-0 right-0 h-20 sm:h-28" style={{ background: "linear-gradient(0deg, rgba(3,3,6,0.9) 0%, transparent 100%)" }} />

      {/* === LAYER 4: HUD TOP — scene counter + time === */}
      <div className="relative z-20 w-full max-w-[1200px] px-6 pt-6 sm:pt-10">
        <motion.div
          key={`hud-${idx}`}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 font-mono cosmic-text-2xs tracking-[0.14em]" style={{ background: `${s.color}18`, border: `1px solid ${s.color}30`, color: s.color }}>
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full" style={{ background: s.color, opacity: 0.6 }} />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />
              </span>
              {s.hud}
            </span>
          </div>
          <span className="font-mono cosmic-text-2xs tracking-[0.1em]" style={{ color: `${s.color}80` }}>
            {String(idx + 1).padStart(2, "0")} / {String(SCENES.length).padStart(2, "0")}
          </span>
        </motion.div>
      </div>

      {/* === LAYER 5: MAIN CONTENT === */}
      <div className="relative z-20 flex-1 flex flex-col items-center justify-center w-full max-w-[1200px] px-6 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={`content-${idx}`}
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -30 }}
            transition={{ duration: FADE, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col items-center text-center max-w-3xl"
          >
            {/* BIG METRIC */}
            <motion.div
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 120, damping: 18, delay: 0.15 }}
            >
              <div className="font-num font-bold tracking-tight" style={{ fontSize: "clamp(72px, 12vw, 140px)", color: s.color, lineHeight: 1 }}>
                {s.headline}
              </div>
              <div className="mt-2 font-mono cosmic-text-xs tracking-[0.2em] uppercase font-semibold" style={{ color: `${s.color}cc` }}>
                {s.label}
              </div>
            </motion.div>

            {/* DETAIL ROW — 3 sub-metrics */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.35 }}
              className="mt-8 flex flex-wrap items-center justify-center gap-4 sm:gap-6"
            >
              {s.details.map((d, di) => (
                <motion.div
                  key={d.t}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + di * 0.1 }}
                  className="text-center min-w-[100px]"
                >
                  <p className="cosmic-text-2xs font-mono uppercase tracking-[0.12em] mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>{d.t}</p>
                  <p className="cosmic-text-sm font-semibold" style={{ color: d.c }}>{d.v}</p>
                </motion.div>
              ))}
            </motion.div>

            {/* REAL OCCUPANCY TREND — one bar per 10s rollup the edge node pushed */}
            {s.bars && s.bars.length > 1 && (
              <motion.div
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.5 }}
                className="mt-7 flex w-full max-w-[520px] flex-col items-center gap-2"
              >
                <div className="flex h-10 w-full items-end gap-[2px]">
                  {s.bars.slice(-60).map((v, i) => {
                    const visibleBars = s.bars!.slice(-60)
                    const max = Math.max(...visibleBars.filter((value): value is number => value !== null), 1)
                    return (
                      <div
                        key={i}
                        className="flex-1 rounded-t-[2px]"
                        style={{
                          height: v === null ? "0%" : `${Math.max((v / max) * 100, 3)}%`,
                          background: v === null ? "transparent" : `linear-gradient(180deg, ${s.color}, ${s.color}44)`,
                        }}
                      />
                    )
                  })}
                </div>
                <p className="font-mono cosmic-text-2xs tracking-[0.1em]" style={{ color: "rgba(255,255,255,0.3)" }}>
                  OCCUPANCY · LAST {s.bars.length} ROLLUPS · 10S EACH
                </p>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* === LAYER 6: SUBTITLE BAR (movie-style) === */}
      <div className="relative z-20 w-full max-w-[900px] px-6 pb-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={`sub-${subtitleKey}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="rounded-xl px-5 py-3 sm:px-8 sm:py-4 text-center"
            style={{ background: "rgba(3,3,6,0.7)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <TypewriterText text={s.subtitle} color="rgba(255,255,255,0.88)" />
            <p className="mt-1.5 font-mono cosmic-text-2xs tracking-[0.08em]" style={{ color: `${s.color}80` }}>{s.caption}</p>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* === LAYER 7: CONTROLS + PROGRESS === */}
      <div className="relative z-20 w-full max-w-[900px] px-6 pb-6 sm:pb-10 flex flex-col items-center gap-4">
        {/* Progress */}
        <div className="w-full h-0.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.08)" }}>
          <motion.div
            className="h-full rounded-full"
            style={{ width: `${progress}%`, background: `linear-gradient(90deg, ${s.color}, ${s.color}aa)` }}
            transition={{ duration: 0.1 }}
          />
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-3">
          <button onClick={prev} className="grid h-10 w-10 place-items-center rounded-full transition-all hover:scale-110" style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.1)", color: "white" }} aria-label="Previous">
            <ChevronLeft size={18} />
          </button>
          <button onClick={toggle} className="grid h-12 w-12 place-items-center rounded-full transition-all hover:scale-110" style={{ background: s.color, color: "white", boxShadow: `0 0 30px ${s.color}40` }} aria-label={playing ? "Pause" : "Play"}>
            {playing ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
          </button>
          <button onClick={next} className="grid h-10 w-10 place-items-center rounded-full transition-all hover:scale-110" style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.1)", color: "white" }} aria-label="Next">
            <ChevronRight size={18} />
          </button>
        </div>

        {/* Scene dots */}
        <div className="flex gap-2 items-center">
          {SCENES.map((sc, i) => (
            <button
              key={i}
              onClick={() => goto(i)}
              className="h-1.5 rounded-full transition-all duration-500"
              style={{ width: i === idx ? 32 : 8, background: i === idx ? sc.color : "rgba(255,255,255,0.2)" }}
              aria-label={`Scene ${i + 1}`}
            />
          ))}
        </div>

        <p className="cosmic-text-2xs font-mono tracking-[0.1em]" style={{ color: "rgba(255,255,255,0.25)" }}>
          ← → navigate · Space play/pause
        </p>

        {live && (
          <p className="cosmic-text-2xs font-mono tracking-[0.1em] text-center" style={{ color: "rgba(255,255,255,0.28)" }}>
            LIVE TELEMETRY FROM THE EDGE NODE · NO PLACEHOLDER NUMBERS · UPDATED {live.seconds_since_update}S AGO
          </p>
        )}
      </div>
    </section>
  )
}

/* Typewriter component — types text letter-by-letter */
function TypewriterText({ text, color }: { text: string; color: string }) {
  const [visible, setVisible] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    setVisible(0)
    let i = 0
    timerRef.current = setInterval(() => {
      i += 1
      setVisible(i)
      if (i >= text.length) {
        if (timerRef.current) clearInterval(timerRef.current)
      }
    }, 22)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [text])

  return (
    <p className="cosmic-text-base sm:cosmic-text-lg leading-relaxed font-medium" style={{ color }}>
      {text.slice(0, visible)}
      {visible < text.length && (
        <span className="inline-block w-[2px] h-[1em] ml-0.5 align-middle animate-pulse" style={{ background: color }} />
      )}
    </p>
  )
}
