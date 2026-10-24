import { useState, useRef, useEffect } from "react"
import { ChevronLeft, ChevronRight, MapPin, MoveRight, Maximize2, Minimize2 } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { Section } from "../components/Section"
import { SectionHeader } from "../components/SectionHeader"
import { ATELIER } from "../data/site"

const TRACE = ["PASS", "STOP", "ENTER", "EXPLORE", "ENGAGE", "VERDICT"]

export function Atelier() {
  const a = ATELIER
  const [tab, setTab] = useState(a.tabs[0].id)
  const [expanded, setExpanded] = useState(false)
  const activeIdx = Math.max(0, a.tabs.findIndex((t) => t.id === tab))
  const active = a.tabs[activeIdx]
  const step = (dir: number) => setTab(a.tabs[(activeIdx + dir + a.tabs.length) % a.tabs.length].id)
  const imageRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    if (a.image) {
      const img = new Image()
      img.src = a.image
    }
  }, [a.image])

  return (
    <Section id="atelier" className="site-scope scroll-mt-24" bg="#0c0c14">
      <div className="mx-auto max-w-[1400px] px-6">
        <SectionHeader index={a.index} kicker={a.kicker} sub={a.sub}>
          {a.h2}
        </SectionHeader>

        <Reveal delay={0.1}>
          <div
            className={`relative overflow-hidden rounded-2xl border border-white/10 transition-all duration-500 ${expanded ? "lg:fixed lg:inset-0 lg:z-50 lg:rounded-none lg:border-none" : ""}`}
            style={{
              background: "#1a1a24",
              boxShadow: expanded ? "0 50px 150px rgba(0,0,0,0.8)" : "0 4px 24px rgba(0,0,0,0.4)",
            }}
          >
            <div
              className={`flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-white/10 px-4 py-3 sm:px-5 transition-all duration-300 ${expanded ? "lg:bg-black/95 lg:backdrop-blur-xl lg:border-b-white/10" : ""}`}
              style={{ background: "#1a1a24" }}
            >
              <span className="flex items-center gap-2 font-mono cosmic-text-2xs font-bold tracking-[0.16em] text-[#8B7CF6]">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-[#8B7CF6] opacity-70 animate-pulse-ring" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[#8B7CF6]" />
                </span>
                {a.ui.live}
              </span>
              <span className="hidden truncate font-mono cosmic-text-2xs tracking-[0.14em] text-[#a1a1aa] sm:inline">
                {a.ui.store}
              </span>
              <div className="flex-1" />
              <span className="hidden truncate font-mono cosmic-text-2xs tracking-[0.14em] text-[#86868b] lg:inline">
                {a.ui.view}
              </span>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => step(-1)}
                  aria-label="Previous view"
                  className="grid h-8 w-8 place-items-center rounded-xl border border-white/15 text-[#f5f5f7] transition-all duration-200 hover:scale-105 hover:border-white/30"
                >
                  <ChevronLeft size={15} strokeWidth={2.3} />
                </button>
                <span className="min-w-[64px] text-center font-mono cosmic-text-xs font-bold tracking-[0.12em] text-[#a1a1aa]">
                  {String(activeIdx + 1).padStart(2, "0")} / {String(a.tabs.length).padStart(2, "0")}
                </span>
                <button
                  onClick={() => step(1)}
                  aria-label="Next view"
                  className="grid h-8 w-8 place-items-center rounded-xl border border-white/15 text-[#f5f5f7] transition-all duration-200 hover:scale-105 hover:border-white/30"
                >
                  <ChevronRight size={15} strokeWidth={2.3} />
                </button>
              </div>

              <button
                onClick={() => setExpanded(!expanded)}
                aria-label={expanded ? "Minimize" : "Expand"}
                className="grid h-8 w-8 place-items-center rounded-xl border border-white/15 text-[#f5f5f7] transition-all duration-200 hover:scale-105 hover:border-white/30"
              >
                {expanded ? <Minimize2 size={16} strokeWidth={2.2} /> : <Maximize2 size={16} strokeWidth={2.2} />}
              </button>
            </div>

            <div
              className="flex items-center gap-1.5 overflow-x-auto border-b border-white/10 bg-[#12121a] px-3 py-2.5 sm:px-5"
              role="tablist"
              aria-label="In-store intelligence views"
            >
              {a.tabs.map((t) => (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={tab === t.id}
                  onClick={() => setTab(t.id)}
                  className="shrink-0 rounded-full px-4 py-2 cosmic-text-xs font-medium transition-all duration-200 sm:cosmic-text-xs"
                  style={
                    tab === t.id
                      ? { background: "#8B7CF6", color: "#05050a", fontWeight: 700 }
                      : { color: "#a1a1aa", border: "1px solid rgba(255,255,255,0.12)" }
                  }
                >
                  {t.label}
                </button>
              ))}
            </div>

            <figure className="group relative" key={active.id}>
              <img
                ref={imageRef}
                src={a.image}
                alt={active.overlay?.tag ?? "Boutique interior with analytics zones"}
                loading="lazy"
                className={`aspect-[16/10] w-full object-cover transition-transform duration-1000 ease-out ${expanded ? "aspect-auto h-[calc(100vh-160px)] min-h-[500px]" : ""} animate-fade-in`}
                style={{ transform: expanded ? "none" : undefined }}
              />
              <div className="pointer-events-none absolute inset-0" style={{
                background: expanded
                  ? "linear-gradient(to top, rgba(6,6,6,0.85), transparent 50%)"
                  : "linear-gradient(to top, rgba(6,6,6,0.55), transparent 45%)"
              }} />

              <figcaption className="absolute left-4 top-4 flex items-center gap-2 rounded-full bg-black/75 px-3.5 py-1.5 font-mono cosmic-text-2xs tracking-[0.16em] text-white backdrop-blur-sm border border-white/10">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-[#8B7CF6] opacity-70 animate-pulse-ring" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#8B7CF6]" />
                </span>
                LIVE · {a.ui.view}
              </figcaption>

              {!expanded && (
                <>
                  <button
                    onClick={() => step(-1)}
                    aria-label="Previous view"
                    className="absolute left-4 top-1/2 hidden h-12 w-12 -translate-y-1/2 place-items-center rounded-full border border-white/30 bg-black/50 text-white backdrop-blur-md transition-all duration-200 hover:scale-110 hover:bg-black/70 lg:grid"
                  >
                    <ChevronLeft size={20} strokeWidth={2.4} />
                  </button>
                  <button
                    onClick={() => step(1)}
                    aria-label="Next view"
                    className="absolute right-4 top-1/2 hidden h-12 w-12 -translate-y-1/2 place-items-center rounded-full border border-white/30 bg-black/50 text-white backdrop-blur-md transition-all duration-200 hover:scale-110 hover:bg-black/70 lg:grid"
                  >
                    <ChevronRight size={20} strokeWidth={2.4} />
                  </button>
                </>
              )}

              {active.markers.map((m) => (
                <button
                  key={`${active.id}-${m.title}`}
                  className="absolute animate-pin-in cursor-pointer"
                  style={{ left: `${m.x}%`, top: `${m.y}%`, transform: "translate(-50%, -50%)" }}
                  title={`${m.title} — ${m.value}`}
                >
                  <span className="relative flex h-5 w-5">
                    <span className="absolute inline-flex h-full w-full animate-ping-soft rounded-full opacity-50" style={{ background: "#8B7CF6", color: "#05050a" }} />
                    <span className="relative inline-flex h-5 w-5 items-center justify-center rounded-full border-2 border-[#05050a] shadow-lg transition-all duration-300 hover:scale-150" style={{ background: "#8B7CF6", color: "#05050a" }}>
                      <MapPin size={10} strokeWidth={3} className="text-[#05050a]" />
                    </span>
                  </span>
                  <span className="pointer-events-none absolute left-1/2 top-full mt-2 hidden min-w-[180px] -translate-x-1/2 rounded-xl border p-3 text-left shadow-[0_4px_16px_rgba(0,0,0,0.4)] backdrop-blur-md sm:block" style={{ background: "rgba(19,19,21,0.95)", borderColor: "rgba(255,255,255,0.12)" }}>
                    <span className="block font-mono cosmic-text-2xs font-bold tracking-[0.14em]" style={{ color: "#8B7CF6" }}>{m.value}</span>
                    <span className="mt-0.5 block cosmic-text-xs font-semibold leading-snug text-[#f5f5f7]">{m.title}</span>
                  </span>
                </button>
              ))}

              <div className={`absolute bottom-4 left-4 max-w-[320px] rounded-2xl p-4 shadow-[0_8px_24px_rgba(0,0,0,0.4)] backdrop-blur-md animate-subtle-float ${expanded ? "bottom-8 left-8 sm:bottom-12 sm:left-12 sm:p-6 max-w-[380px]" : "sm:bottom-6 sm:left-6 sm:p-5"}`} style={{ background: "rgba(19,19,21,0.92)", border: "1px solid rgba(255,255,255,0.1)" }}>
                <p className="font-mono cosmic-text-2xs tracking-[0.18em] text-[#f5f5f7]/48">{active.overlay.tag}</p>
                <p className="mt-2 font-mono cosmic-text-3xl font-bold text-[#f5f5f7]">{active.overlay.big}</p>
                {active.overlay.lines.map((l) => (
                  <p key={l} className="mt-1.5 cosmic-text-xs leading-snug text-[#f5f5f7]/62">{l}</p>
                ))}
                <div className="mt-4 border-t border-white/10 pt-3">
                  <p className="font-mono cosmic-text-2xs tracking-[0.18em] text-[#8B7CF6]">READOUT</p>
                  <p className="mt-1.5 cosmic-text-sm text-[#f5f5f7]/78">{active.overlay.note}</p>
                </div>
              </div>

              <div className={`absolute bottom-4 right-4 hidden max-w-[280px] flex-col gap-2 rounded-2xl border border-[#8B7CF6]/35 bg-black/80 p-4 backdrop-blur-md ${expanded ? "sm:flex sm:bottom-8 sm:right-8" : "sm:flex sm:bottom-6 sm:right-6"}`}>
                <p className="flex items-center gap-1.5 font-mono cosmic-text-2xs tracking-[0.18em] text-[#8B7CF6]">
                  WHAT HAPPENS NEXT <MoveRight size={11} strokeWidth={2.6} />
                </p>
                <p className="cosmic-text-sm text-[#f5f5f7]/85">{active.overlay.move}</p>
              </div>

              <div className={`absolute right-4 top-4 hidden items-center gap-2 rounded-full px-4 py-1.5 font-mono cosmic-text-2xs font-bold tracking-[0.08em] shadow-[0_4px_16px_rgba(0,0,0,0.16)] ${expanded ? "sm:flex sm:right-8 sm:top-8" : "sm:flex sm:right-6 sm:top-6"}`} style={{ background: "#8B7CF6", color: "#05050a" }}>
                <MapPin size={12} strokeWidth={2.5} />
                <span>{active.pin.title} — {active.pin.value}</span>
              </div>
            </figure>

            <div className="flex flex-wrap items-center gap-2 border-t border-white/10 px-4 py-4 sm:px-5 bg-[#1a1a24]">
              <span className="mr-1 font-mono cosmic-text-2xs tracking-[0.16em] text-[#a1a1aa]">EXACTLY WHAT HAPPENS</span>
              {TRACE.map((s, i) => {
                const isNow = i === 2
                return (
                  <span key={s} className="flex items-center gap-2">
                    <span
                      className="rounded-full px-3 py-1 font-mono cosmic-text-2xs font-bold tracking-[0.1em] transition-all duration-300"
                      style={
                        isNow
                          ? { background: "#8B7CF6", color: "#05050a", fontWeight: 700, boxShadow: "0 0 20px rgba(139,124,246,0.4)" }
                          : i > 2
                            ? { background: "rgba(139,124,246,0.15)", color: "#8B7CF6" }
                            : { border: "1px solid rgba(255,255,255,0.12)", color: "#86868b" }
                      }
                    >
                      {s}
                    </span>
                    {i < TRACE.length - 1 && <ChevronRight size={12} className="text-[#86868b]" />}
                  </span>
                )
              })}
            </div>

            <div className="grid grid-cols-2 gap-px border-t border-white/10 bg-[#1a1a24]/80/5">
              {a.features.map((f) => (
                <article key={f.title} className="p-5 sm:p-6 bg-[#1a1a24] transition-all duration-300 hover:bg-[#222226] hover:shadow-[inset_0_0_0_1px_rgba(139,124,246,0.3)]">
                  <h3 className="font-semibold cosmic-text-base leading-tight sm:cosmic-text-lg text-[#f5f5f7]">{f.title}</h3>
                  <p className="mt-0.5 cosmic-text-2xs font-semibold uppercase tracking-[0.12em] text-[#8B7CF6]">{f.sub}</p>
                  <p className="mt-2 cosmic-text-sm text-[#a1a1aa]">{f.desc}</p>
                </article>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </Section>
  )
}
