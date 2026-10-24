import { useEffect, useState } from "react"
import type { FormEvent } from "react"
import { Check, ChevronDown, X, Loader2 } from "lucide-react"
import { PILOT_FORM } from "../data/site"
import { submitViaEmail } from "../utils/mailto"

const inputCls =
  "w-full rounded-xl border border-white/10 bg-[#05050a] px-4 py-3 cosmic-text-sm text-[#f5f5f7] placeholder:text-[#86868b] transition-colors duration-150 focus:border-[#8B7CF6]"

export function PilotModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)
  const f = PILOT_FORM

  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    if (open) {
      document.addEventListener("keydown", esc)
      document.body.style.overflow = "hidden"
    }
    return () => {
      document.removeEventListener("keydown", esc)
      document.body.style.overflow = ""
    }
  }, [open, onClose])

  if (!open) return null

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget as HTMLFormElement)
    setSending(true)
    window.setTimeout(() => {
      submitViaEmail("Pilot request — AD Labs", [
        { label: "Brand", value: String(fd.get("brand") ?? "") },
        { label: "Sector", value: String(fd.get("sector") ?? "") },
        { label: "Locations", value: String(fd.get("locations") ?? "") },
        { label: "First problem", value: String(fd.get("problem") ?? "") },
        { label: "Budget", value: String(fd.get("budget") ?? "") },
        { label: "Notes", value: String(fd.get("detail") ?? "") },
        { label: "Email", value: String(fd.get("email") ?? "") },
      ])
      setSending(false)
      setSent(true)
    }, 700)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 p-0 backdrop-blur-sm sm:items-center sm:p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={f.title}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-3xl border border-white/10 bg-[#12121a] shadow-[0_24px_80px_rgba(0,0,0,0.6)] sm:rounded-3xl"
      >
        <div className="flex items-start justify-between p-6 pb-0 sm:p-8 sm:pb-0">
          <span className="kicker text-[#86868b]">{f.title}</span>
          <button
            onClick={onClose}
            aria-label="Close"
            className="grid h-9 w-9 place-items-center rounded-full border border-white/10 text-[#a1a1aa] transition-colors hover:border-white/30 hover:text-[#f5f5f7]"
          >
            <X size={16} />
          </button>
        </div>

        {!sent ? (
          <div className="p-6 sm:p-8">
            <h3 className="cosmic-text-3xl font-semibold leading-tight tracking-[-0.01em] text-[#f5f5f7]">{f.h2}</h3>
            <p className="mt-3 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{f.sub}</p>

            <form onSubmit={submit} className="mt-7 flex flex-col gap-4">
              <div>
                <label htmlFor="pf-brand" className="mb-1.5 block cosmic-text-xs font-semibold text-[#c4c4cc]">
                  {f.fields.brand.label}
                </label>
                <input id="pf-brand" name="brand" required placeholder={f.fields.brand.placeholder} className={inputCls} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="pf-sector" className="mb-1.5 block cosmic-text-xs font-semibold text-[#c4c4cc]">
                    {f.fields.sector.label}
                  </label>
                  <div className="relative">
                    <select id="pf-sector" name="sector" className={`${inputCls} appearance-none pr-10`} defaultValue={f.fields.sector.options[0]}>
                      {f.fields.sector.options.map((o) => (
                        <option key={o} className="bg-[#12121a] text-[#f5f5f7]">{o}</option>
                      ))}
                    </select>
                    <ChevronDown size={16} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-[#86868b]" />
                  </div>
                </div>
                <div>
                  <label htmlFor="pf-loc" className="mb-1.5 block cosmic-text-xs font-semibold text-[#c4c4cc]">
                    {f.fields.locations.label}
                  </label>
                  <div className="relative">
                    <select id="pf-loc" name="locations" className={`${inputCls} appearance-none pr-10`} defaultValue={f.fields.locations.options[0]}>
                      {f.fields.locations.options.map((o) => (
                        <option key={o} className="bg-[#12121a] text-[#f5f5f7]">{o}</option>
                      ))}
                    </select>
                    <ChevronDown size={16} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-[#86868b]" />
                  </div>
                </div>
              </div>
              <div>
                <label htmlFor="pf-email" className="mb-1.5 block cosmic-text-xs font-semibold text-[#c4c4cc]">
                  {f.fields.email.label}
                </label>
                <input id="pf-email" name="email" type="email" required placeholder={f.fields.email.placeholder} className={inputCls} />
              </div>
              <button
                type="submit"
                disabled={sending}
                className="mt-2 inline-flex items-center justify-center gap-2 rounded-full bg-[#8B7CF6] px-7 py-3.5 cosmic-text-sm font-semibold text-[#05050a] transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#6E5CE6] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {sending ? (
                  <>
                    <Loader2 size={16} strokeWidth={2.5} className="animate-spin" />
                    Submitting…
                  </>
                ) : (
                  f.submit
                )}
              </button>
              <p className="cosmic-text-xs leading-relaxed text-[#86868b]">{f.note}</p>
            </form>
          </div>
        ) : (
          <div className="flex flex-col items-start p-8 sm:p-10">
            <span className="grid h-12 w-12 place-items-center rounded-full bg-[#8B7CF6] text-[#05050a]">
              <Check size={22} strokeWidth={2.6} />
            </span>
            <h3 className="mt-5 cosmic-text-3xl font-semibold text-[#f5f5f7]">{f.successTitle}</h3>
            <p className="mt-3 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{f.successBody}</p>
            <button
              onClick={onClose}
              className="mt-8 rounded-full border border-white/15 px-6 py-3 cosmic-text-sm font-semibold text-[#f5f5f7] transition-colors hover:border-white/40"
            >
              {f.return}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
