import { useEffect, useMemo, useRef, useState } from "react"
import { Mic, MicOff, X, Sparkles, CornerDownLeft } from "lucide-react"
import {
  KPIS, TRAFFIC_HOURS, STORES, ZONES, CAMPAIGNS, ALERTS,
  PREDICTIONS, WEEKLY_HISTORY, INSIGHTS, TENANT,
} from "../data/dashboard"
import { formatDemoAnswer } from "../lib/demo-copy"

type Screen = "overview" | "storefront" | "stores" | "store" | "campaigns" | "zones" | "brief" | "manager" | "compare" | "history" | "demographics" | "product" | "alerts" | "tour" | "ads"
type Msg = { role: "user" | "ai"; text: string; screen?: Screen; storeId?: string; storeName?: string }

/* ---------------- Intent engine over sample dashboard fixtures ---------------- */
function answer(q: string): { text: string; screen?: Screen; storeId?: string } {
  const t = q.toLowerCase()

  // Mumbai / Bandra store
  if (t.includes("mumbai") || t.includes("bandra") || t.includes("flagship")) {
    const s = STORES.find((x) => x.id === "madison") ?? STORES[0]
    return {
      text: `Your Mumbai flagship (${s.name}) right now: ${s.footfallToday.toLocaleString("en-US")} footfall, stop rate ${s.stopRate}, trend ${s.trend}. ${s.flag ? `Heads up — ${s.flag}` : "It's the strongest of your 3 stores."}`,
      screen: "store",
      storeId: "madison",
    }
  }

  // Bengaluru / Indiranagar store
  if (t.includes("bengaluru") || t.includes("bangalore") || t.includes("indiranagar") || t.includes("blr")) {
    const s = STORES.find((x) => x.id === "beverly") ?? STORES[1]
    return {
      text: `Bengaluru (${s.name}): ${s.footfallToday.toLocaleString("en-US")} footfall today, stop rate ${s.stopRate}, trend ${s.trend}. Second place in the portfolio — one window away from grade A.`,
      screen: "store",
      storeId: "beverly",
    }
  }

  // Pune / Koregaon store
  if (t.includes("pune") || t.includes("koregaon")) {
    const s = STORES.find((x) => x.id === "mayfair") ?? STORES[2]
    return {
      text: `Pune (${s.name}) is the one to watch: stop rate ${s.stopRate} vs 8.9% cohort and declining 0.3pp/week. ${s.flag ?? "Audit the window display this week."}`,
      screen: "store",
      storeId: "mayfair",
    }
  }

  // Stores / portfolio (generic)
  if (t.includes("stores") || t.includes("portfolio") || t.includes("locations") || t.includes("branches") || t.includes("all my")) {
    return {
      text: STORES.map((s) => `${s.name}: stop ${s.stopRate} · footfall ${s.footfallToday.toLocaleString("en-US")} (${s.trend})`).join(" · "),
      screen: "stores",
    }
  }

  // Greets
  if (/^(hi|hey|hello|namaste)/.test(t)) {
    return { text: `Namaste! I can show sample numbers for ${TENANT.name}. Ask me: "how busy is today", "what's the Mumbai store doing", "worst zone", "did the campaign work", "top alert", or "predictions".`, screen: "overview" }
  }

  // How busy / footfall today
  if (t.includes("busy") || t.includes("footfall") || t.includes("traffic") || t.includes("pass")) {
    const k = KPIS.today[0]
    const peak = TRAFFIC_HOURS.reduce((a, b) => (b.v > a.v ? b : a))
    return {
      text: `Today: ${k.value} people passed the storefront (${k.delta} vs yesterday). The busiest hour is ${peak.h}:00 with ${peak.v} passers-by — that's your 15:00–17:00 attention peak. Staff up 2 for that window.`,
      screen: "storefront",
    }
  }

  // Stop / capture / window
  if (t.includes("stop") || t.includes("capture") || t.includes("window") || t.includes("glass")) {
    const s = KPIS.today[1]
    return {
      text: `Window stop rate today: ${s.value} (${s.delta} vs yesterday; peer set is 8.9%). Capture rate is 21% stop-to-enter. The Winter Rotation lifted capture +14.6% vs baseline and it held for three weeks.`,
      screen: "storefront",
    }
  }

  // Walk-ins / entered
  if (t.includes("walk") || t.includes("enter") || t.includes("visitor") || t.includes("came in")) {
    const k = KPIS.today[2]
    return { text: `${k.value} walk-ins today (${k.delta} vs yesterday). Peak entry clusters 16:30–18:45 — 3 on floor is the right call there.`, screen: "manager" }
  }

  // Dwell
  if (t.includes("dwell") || t.includes("stay") || t.includes("inside") || t.includes("time in")) {
    const k = KPIS.today[3]
    const best = ZONES.reduce((a, b) => (parseFloat(b.dwell.split("m")[0]) > parseFloat(a.dwell.split("m")[0]) ? b : a))
    return { text: `Average in-store dwell: ${k.value} (${k.delta}). The deepest is ${best.name} at ${best.dwell} — that's where your best product and staff should be.`, screen: "zones" }
  }

  // Zones / heatmap
  if (t.includes("zone") || t.includes("heat") || t.includes("floor") || t.includes("rotunda") || t.includes("dead")) {
    const dead = ZONES.filter((z) => z.heat < 0.3)
    const hot = ZONES.reduce((a, b) => (b.traffic > a.traffic ? b : a))
    return {
      text: `10 zones tracked. Hottest: ${hot.name} — ${hot.traffic}% traffic, ${hot.dwell} dwell, heat 0.${Math.round(hot.heat * 100)}. Dead spots: ${dead.map((z) => `${z.code} ${z.name}`).join(", ") || "none"}. Zone F1 is under-lit after 18:00 — relight it.`,
      screen: "zones",
    }
  }

  // Campaigns / A-B / did it work
  if (t.includes("campaign") || t.includes("a/b") || t.includes("ab ") || t.includes("work") || t.includes("verdict") || t.includes("uplift")) {
    const c = CAMPAIGNS[0]
    const c2 = CAMPAIGNS[1]
    return {
      text: `Yes — verified. "${c.name}" lifted ${c.metricLabel} ${c.before} → ${c.after} (+14.6%) over a 14-day A/B, and it held for three weeks. "${c2.name}" lifted hero gaze 8.4s → 9.6s in Wk 8. Verdict: keep the layout, next test the offer.`,
      screen: "campaigns",
    }
  }

  // Store / portfolio
  if (t.includes("store") || t.includes("portfolio") || t.includes("locations") || t.includes("branch")) {
    const lines = STORES.map((s) => `${s.name}: stop ${s.stopRate}, footfall ${s.footfallToday.toLocaleString("en-US")} (${s.trend})`).join(" · ")
    return { text: `Your 3 stores: ${lines}. ${STORES[2].flag ?? ""}`, screen: "stores" }
  }

  // Alerts
  if (t.includes("alert") || t.includes("issue") || t.includes("problem") || t.includes("wrong") || t.includes("attention")) {
    const a = ALERTS[0]
    return { text: `${ALERTS.length} active, ${ALERTS.filter((x) => x.severity === "critical").length} critical. Top: ${a.zone ?? a.store} — ${a.message}. Fix: ${a.action}.`, screen: "alerts" }
  }

  // Predictions / forecast
  if (t.includes("predict") || t.includes("forecast") || t.includes("future") || t.includes("next week") || t.includes("will")) {
    const p = PREDICTIONS.map((x) => `${x.metric}: ${x.current} → ${x.projected} by ${x.timeframe} (${x.confidence})`).join(" · ")
    return { text: `Projections: ${p}. Capture rate keeps compounding — keep the rotation.`, screen: "history" }
  }

  // History / trend / weeks
  if (t.includes("history") || t.includes("trend") || t.includes("week") || t.includes("timeline")) {
    const peakW = WEEKLY_HISTORY.reduce((a, b) => (b.stopRate > a.stopRate ? b : a))
    const first = WEEKLY_HISTORY[0]
    const last = WEEKLY_HISTORY[WEEKLY_HISTORY.length - 1]
    return { text: `Stop rate is up from ${first.stopRate}% in ${first.week} to ${last.stopRate}% now — best week was ${peakW.week} at ${peakW.stopRate}%. Two window events drove it: Winter Rotation (Wk 4) and Hero Sash (Wk 8).`, screen: "history" }
  }

  // Demographics
  if (t.includes("demographic") || t.includes("age") || t.includes("cohort") || t.includes("solo") || t.includes("pair")) {
    return { text: `28–44 year olds drive 62% of attention. Solo visitors 58% vs pairs 42%. Peak window 16:30–18:45. Solos browse deep; pairs decide — different conversations needed.`, screen: "demographics" }
  }

  // Product / gaze
  if (t.includes("product") || t.includes("gaze") || t.includes("fixture") || t.includes("touch")) {
    const hero = { name: "Hero Handbag Vitrine", gaze: "8.4s", touch: "42%" }
    return { text: `Top fixture: ${hero.name} — ${hero.gaze} gaze, ${hero.touch} touch. Jewellery holds attention longest (9m 45s); premium retail is quickest. Gaze maps desire — put your next hero in the sightline.`, screen: "product" }
  }

  // Ads / attribution
  if (t.includes("ad") || t.includes("attribution") || t.includes("poster") || t.includes("ooh")) {
    return { text: `Attribution running on 3 campaigns. The window-trail QR converts best: 0.59% sight-to-store, 61% convert, +17.2% uplift vs unexposed. Street poster pulls 38 attributed walk-ins, mostly to the Leather Island.`, screen: "ads" }
  }

  // Signs / insights
  if (t.includes("insight") || t.includes("sign") || t.includes("happen")) {
    const ins = INSIGHTS.slice(0, 2)
    return { text: `${ins.map((x) => `${x.title} — ${x.description}`).join(" ")} Basis: ${ins[0].basis}.`, screen: "overview" }
  }

  // Numbers / kpi
  if (t.includes("kpi") || t.includes("number") || t.includes("metric") || t.includes("dashboard")) {
    const k = KPIS.today.map((x) => `${x.label} ${x.value}`).join(" · ")
    return { text: `Today's five: ${k}. Stop rate leads the peer band by +0.4pp today.`, screen: "overview" }
  }

  // Did you / what can you do
  if (t.includes("can you do") || t.includes("help") || t.includes("what") && t.includes("do")) {
    return { text: `I can explain the sample dashboard data — footfall, stop rate, walk-ins, dwell, zones, campaigns, alerts, predictions. Try: "how busy is today", "worst zone", "did the campaign work", "predictions", "open alerts".` }
  }

  return { text: "I can explain the sample numbers, but not that exact phrasing. Try asking with a metric: footfall, stop rate, dwell, zones, history, predictions, alerts, ads, or say a screen to jump there." }
}

/* ---------------- Voice helpers ---------------- */
type SpeechResultLike = { results: { 0: { 0: { transcript: string } } } }
type RecognitionLike = {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((e: SpeechResultLike) => void) | null
  onend: (() => void) | null
  onerror: ((e: unknown) => void) | null
  start: () => void
  stop: () => void
}
type SpeechRecognitionCtor = new () => RecognitionLike

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionCtor
    webkitSpeechRecognition?: SpeechRecognitionCtor
  }
}

function speak(_text: string) {
  // Voice-off: user asked to switch off spoken replies. Text + navigation stay.
  try {
    window.speechSynthesis?.cancel()
  } catch { /* ignore */ }
}

export function VoiceAssistant({ onNavigate }: { onNavigate: (s: Screen, storeId?: string) => void }) {
  const [open, setOpen] = useState(false)
  const [listening, setListening] = useState(false)
  const [input, setInput] = useState("")
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "ai", text: `Namaste 👋 I'm your AD Labs copilot. Ask me anything about ${TENANT.name} — or just say a screen name to jump.` },
  ])
  const recRef = useRef<RecognitionLike | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      // Silence: never auto-speak or auto-listen on open.
      window.speechSynthesis?.cancel()
      inputRef.current?.focus()
    }
    return () => window.speechSynthesis?.cancel()
  }, [open])

  const quick = useMemo(() => [
    { label: "How busy today?", q: "how busy is today" },
    { label: "Mumbai store?", q: "what's the mumbai store doing" },
    { label: "Bengaluru?", q: "how is bengaluru" },
    { label: "Pune store?", q: "how is pune doing" },
    { label: "Worst zone?", q: "worst zone" },
    { label: "Did campaign work?", q: "did the a/b campaign work" },
  ], [])

  const submit = (text: string) => {
    const q = text.trim()
    if (!q) return
    setMsgs((m) => [...m, { role: "user", text: q }])
    const res = answer(q)
    res.text = formatDemoAnswer(res.text)
    setTimeout(() => {
      setMsgs((m) => [...m, { role: "ai", text: res.text, screen: res.screen }])
      speak(res.text)
      if (res.screen) onNavigate(res.screen, res.storeId)
      setTimeout(() => scrollRef.current?.scrollTo({ top: 99999, behavior: "smooth" }), 60)
    }, 90)
  }

  const toggleListen = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (listening) {
      recRef.current?.stop()
      setListening(false)
      return
    }
    if (!SR) {
      setMsgs((m) => [...m, { role: "ai", text: "Voice input isn't available in this browser — type or tap a quick question instead." }])
      return
    }
    const rec = new SR()
    rec.lang = "en-IN"
    rec.interimResults = false
    rec.continuous = false
    rec.onresult = (e) => {
      const t = e.results[0][0].transcript
      setInput(t)
      submit(t)
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    recRef.current = rec
    try {
      rec.start()
      setListening(true)
    } catch {
      setListening(false)
    }
  }

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Open AD Labs copilot"
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full py-3 pl-4 pr-5 text-[#05050a] shadow-[0_8px_28px_rgba(139,124,246,0.35)] transition-all duration-200 hover:-translate-y-0.5 active:scale-95"
          style={{ background: "#8B7CF6" }}
        >
          <Sparkles size={18} strokeWidth={2.2} />
          <span className="font-inter cosmic-text-sm font-bold">Ask AD Labs</span>
        </button>
      )}

      {open && (
        <div className="fixed bottom-5 right-5 z-50 flex w-[min(380px,calc(100vw-40px))] flex-col overflow-hidden rounded-3xl border border-[var(--app-line)]" style={{ background: "var(--app-card)", boxShadow: "var(--app-shadow)", maxHeight: "min(560px, calc(100vh - 40px))" }}>
          <div className="flex items-center justify-between border-b border-[var(--app-line)] px-4 py-3">
            <span className="flex items-center gap-2 font-inter cosmic-text-sm font-bold text-[var(--app-text)]">
              <span className="grid h-6 w-6 place-items-center rounded-lg" style={{ background: "#8B7CF6", color: "#05050a" }}>
                <Sparkles size={13} strokeWidth={2.4} />
              </span>
              ASK AD LABS
            </span>
            <button onClick={() => setOpen(false)} aria-label="Close" className="grid h-8 w-8 place-items-center rounded-full text-[var(--app-sub)] hover:text-[var(--app-text)]">
              <X size={15} />
            </button>
          </div>

          {/* Chat thread */}
          <div ref={scrollRef} className="flex-1 space-y-2.5 overflow-y-auto px-4 py-3.5">
            {msgs.map((m, i) => (
              <div key={i} className="flex" style={{ justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div
                  className="max-w-[85%] rounded-2xl px-3.5 py-2.5 font-inter cosmic-text-xs leading-relaxed"
                  style={
                    m.role === "user"
                      ? { background: "var(--app-text)", color: "var(--app-card)", borderBottomRightRadius: 6 }
                      : { background: "var(--app-raise)", color: "var(--app-text)", borderBottomLeftRadius: 6 }
                  }
                >
                  {m.text}
                  {m.screen && (
                    <button
                      onClick={() => onNavigate(m.screen!, m.storeId)}
                      className="mt-1.5 flex items-center gap-1 cosmic-text-2xs font-bold uppercase tracking-[0.08em]"
                      style={{ color: "var(--app-gold)" }}
                    >
                      Open {m.storeId ? "store" : m.screen} →
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Input row */}
          <div className="border-t border-[var(--app-line)] p-3">
            <div className="flex items-center gap-2">
              <button
                onClick={toggleListen}
                aria-label={listening ? "Stop listening" : "Start voice command"}
                className={`grid h-10 w-10 shrink-0 place-items-center rounded-full transition-all duration-200 active:scale-95 ${listening ? "animate-pulse" : ""}`}
                style={{ background: listening ? "var(--app-raise)" : "#8B7CF6", color: listening ? "var(--app-gold)" : "#05050a" }}
              >
                {listening ? <MicOff size={17} /> : <Mic size={17} />}
              </button>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { submit(input); setInput("") } }}
                placeholder={listening ? "Listening… speak now" : "Ask about your store…"}
                className="min-w-0 flex-1 rounded-xl border border-[var(--app-line)] px-3 py-2.5 font-inter cosmic-text-sm outline-none transition-colors focus:border-[var(--app-gold)]"
                style={{ background: "var(--app-raise)", color: "var(--app-text)" }}
              />
            </div>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {quick.map((c) => (
                <button
                  key={c.label}
                  onClick={() => submit(c.q)}
                  className="rounded-full border border-[var(--app-line)] px-2.5 py-1 font-inter cosmic-text-2xs font-semibold text-[var(--app-sub)] transition-colors hover:border-[var(--app-gold)] hover:text-[var(--app-text)]"
                >
                  {c.label}
                </button>
              ))}
            </div>
            <p className="mt-2.5 flex items-center gap-1.5 border-t border-[var(--app-line)] pt-2.5 font-inter cosmic-text-2xs text-[var(--app-faint)]">
              <CornerDownLeft size={10} />
              Sample dashboard figures only · voice input uses your browser's on-device speech engine
            </p>
          </div>
        </div>
      )}
    </>
  )
}
