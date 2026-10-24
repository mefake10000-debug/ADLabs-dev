import { useEffect, useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Search } from "lucide-react"

type Screen = string

const ALL: { id: string; label: string; group: string }[] = [
  { id: "overview", label: "Overview", group: "Run" },
  { id: "storefront", label: "Storefront", group: "Run" },
  { id: "stores", label: "Stores", group: "Run" },
  { id: "zones", label: "Zone heatmaps", group: "Run" },
  { id: "brief", label: "Monday Brief", group: "Run" },
  { id: "manager", label: "Today (store)", group: "Store" },
  { id: "campaigns", label: "Campaigns & A/B", group: "Prove" },
  { id: "ads", label: "Out-of-home ads", group: "Prove" },
  { id: "compare", label: "Compare stores", group: "Prove" },
  { id: "history", label: "History", group: "Prove" },
  { id: "demographics", label: "Demographics", group: "Understand" },
  { id: "product", label: "Product gaze", group: "Understand" },
  { id: "alerts", label: "Alerts", group: "Understand" },
  { id: "tour", label: "How you'll see it", group: "Understand" },
]

export function CmdPalette({
  open,
  onClose,
  onNavigate,
}: {
  open: boolean
  onClose: () => void
  onNavigate: (id: Screen) => void
}) {
  const [q, setQ] = useState("")
  const [idx, setIdx] = useState(0)

  const results = useMemo(() => {
    const t = q.trim().toLowerCase()
    return ALL.filter((x) => !t || x.label.toLowerCase().includes(t) || x.id.includes(t))
  }, [q])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
      if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(i + 1, results.length - 1)) }
      if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)) }
      if (e.key === "Enter" && results[idx]) { onNavigate(results[idx].id); onClose() }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, results, idx, onClose, onNavigate])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[120] flex items-start justify-center bg-black/40 px-4 pt-[12vh] backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md overflow-hidden rounded-2xl border border-[var(--app-line)]"
            style={{ background: "var(--app-card)", boxShadow: "0 40px 90px rgba(0,0,0,0.35)" }}
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="flex items-center gap-3 border-b border-[var(--app-line)] px-4 py-3.5">
              <Search size={16} className="text-[var(--app-faint)]" />
              <input
                autoFocus
                value={q}
                onChange={(e) => { setQ(e.target.value); setIdx(0) }}
                placeholder="Jump to a screen…"
                className="w-full bg-transparent font-inter cosmic-text-sm text-[var(--app-text)] outline-none placeholder:text-[var(--app-faint)]"
              />
              <kbd className="rounded border border-[var(--app-line)] px-1.5 py-0.5 font-inter cosmic-text-2xs text-[var(--app-faint)]">ESC</kbd>
            </div>
            <div className="max-h-[40vh] overflow-y-auto p-1.5">
              {results.length === 0 && (
                <p className="px-3 py-4 text-center font-inter cosmic-text-xs text-[var(--app-faint)]">No screens match “{q}”.</p>
              )}
              {results.map((r, i) => (
                <button
                  key={r.id}
                  onMouseEnter={() => setIdx(i)}
                  onClick={() => { onNavigate(r.id); onClose() }}
                  className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left transition-colors"
                  style={{ background: i === idx ? "var(--app-raise)" : "transparent" }}
                >
                  <span className="font-inter cosmic-text-sm text-[var(--app-text)]">{r.label}</span>
                  <span className="font-inter cosmic-text-2xs text-[var(--app-faint)]">{r.group}</span>
                </button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
