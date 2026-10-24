import { useEffect, useRef, useState } from "react"
import { motion, AnimatePresence, useInView } from "framer-motion"

// A small, deterministic pool of anonymised events (mirrors the edge->cloud schema).
const SAMPLE_EVENTS: { zone: string; dwell: number | string; bucket: string; walkin: boolean }[] = [
  { zone: "window_display", dwell: "8s", bucket: "25-34", walkin: true },
  { zone: "window_display", dwell: "3s", bucket: "45-60", walkin: false },
  { zone: "window_display", dwell: "12s", bucket: "18-27", walkin: true },
  { zone: "window_display", dwell: "5s", bucket: "28-44", walkin: true },
  { zone: "window_display", dwell: "2s", bucket: "60+", walkin: false },
  { zone: "window_display", dwell: "9s", bucket: "25-34", walkin: true },
  { zone: "window_display", dwell: "6s", bucket: "28-44", walkin: false },
  { zone: "window_display", dwell: "14s", bucket: "18-27", walkin: true },
  { zone: "window_display", dwell: "4s", bucket: "45-60", walkin: false },
  { zone: "window_display", dwell: "7s", bucket: "25-34", walkin: true },
]

function EventLine({ e }: { e: (typeof SAMPLE_EVENTS)[number] }) {
  return (
    <div className="flex items-center gap-2 font-mono cosmic-text-xs leading-tight text-[#e8e6df]/90 break-all">
      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#8B7CF6]" />
      <span className="text-[#8B7CF6]/70">e0a3</span>
      <span className="text-[#e8e6df]/50">{"{"}</span>
      <span>zone:<b className="text-[#8B7CF6]">{e.zone}</b></span>
      <span>dwell:<b>{e.dwell}</b></span>
      <span>bucket:<b>{e.bucket}</b></span>
      <span className={e.walkin ? "text-[#8B7CF6]" : "text-[#e8e6df]/40"}>{e.walkin ? "walkin:true" : "walkin:false"}</span>
      <span className="text-[#e8e6df]/50">{"}"}</span>
    </div>
  )
}

export function EventStream({ rows = 5 }: { rows?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-40px" })
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (!inView) return
    const id = setInterval(() => setIndex((i) => (i + 1) % SAMPLE_EVENTS.length), 2200)
    return () => clearInterval(id)
  }, [inView])

  const visible = Array.from({ length: Math.min(rows, SAMPLE_EVENTS.length) }, (_, r) =>
    SAMPLE_EVENTS[(index + r) % SAMPLE_EVENTS.length],
  )

  return (
    <div
      ref={ref}
      className="flex h-full flex-col rounded-2xl border border-[rgba(255,255,255,0.08)] bg-[#121212] p-4 shadow-[0_20px_60px_rgba(0,0,0,0.35)]"
      aria-label="Live anonymised event stream"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="flex items-center gap-2 font-mono cosmic-text-2xs tracking-[0.16em] text-[#e8e6df]/50">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#8B7CF6] opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[#8B7CF6]" />
          </span>
          EDGE → CLOUD · ANONYMIZED
        </span>
        <span className="font-mono cosmic-text-2xs text-[#8B7CF6]/70">JSON</span>
      </div>

      <div className="relative flex-1 overflow-hidden">
        <AnimatePresence mode="popLayout">
          {visible.map((e, i) => (
            <motion.div
              key={`${index}-${i}`}
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className={i === 0 ? "mb-2" : "mb-2"}
            >
              <EventLine e={e} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <div className="mt-3 border-t border-[rgba(255,255,255,0.06)] pt-2 font-mono cosmic-text-2xs tracking-[0.08em] text-[#e8e6df]/40">
        no raw image · no face embedding · no cross-store id
      </div>
    </div>
  )
}
