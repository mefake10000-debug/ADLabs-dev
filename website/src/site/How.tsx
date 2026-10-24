import { useState } from "react"
import type { FormEvent } from "react"
import { Check, ChevronDown, Send, Plug, Focus, FileText } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { SectionHeader } from "../components/SectionHeader"
import { HOW, PILOT_FORM, BRAND } from "../data/site"

const HOW_ICONS = [Plug, Focus, FileText]
const HOW_TIMES = ["Live measurement", "First full week", "Weekly verdicts"]

const inputCls =
  "w-full rounded-xl border border-white/15 bg-[#1a1a24]/80 px-4 py-3 cosmic-text-base text-[#f5f5f7] placeholder:text-[#86868b] transition-colors duration-150 focus:border-[#8B7CF6] focus:outline-none"

export function How({ onPilot }: { onPilot: () => void }) {
  const h = HOW
  const [sent, setSent] = useState(false)
  const [feedback, setFeedback] = useState<"yes" | "no" | null>(null)
  const [email, setEmail] = useState("")

  const submit = (e: FormEvent) => {
    e.preventDefault()
    setSent(true)
  }

  return (
    <section id="how" className="scroll-mt-24 bg-[#0c0c14] py-12 sm:py-16 lg:py-20">
      <div className="mx-auto max-w-[1200px] px-6">
      <SectionHeader index={h.index} kicker={h.kicker}>
        {h.h2}
      </SectionHeader>

      <div className="mt-8 grid gap-5 md:grid-cols-3">
        {h.steps.map((s, i) => {
          const HowIcon = HOW_ICONS[i]
          return (
          <Reveal key={s.num} delay={i * 0.1}>
            <article className="site-card group relative h-full overflow-hidden p-8">
              <span className="absolute -right-3 -top-6 cosmic-text-6xl font-bold leading-none text-[#f5f5f7]/[0.03]">
                {s.num}
              </span>
              <div className="flex items-center gap-3">
                <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#8B7CF6]/10 text-[#8B7CF6] transition-transform duration-300 group-hover:scale-110">
                  {HowIcon && <HowIcon size={22} strokeWidth={1.9} />}
                </span>
                <span className="rounded-full border border-[#8B7CF6]/30 bg-[#8B7CF6]/10 px-3 py-1 cosmic-text-2xs font-semibold uppercase tracking-wide text-[#8B7CF6]">
                  {HOW_TIMES[i]}
                </span>
              </div>
              <h3 className="mt-6 cosmic-text-2xl font-semibold text-[#f5f5f7]">{s.title}</h3>
              <p className="mt-3 cosmic-text-base leading-relaxed text-[#a1a1aa]">{s.desc}</p>
              <p className="mt-5 border-t border-white/8 pt-4 cosmic-text-sm leading-relaxed text-[#86868b]">
                {s.answer}
              </p>
            </article>
          </Reveal>
          )
        })}
      </div>

      <Reveal delay={0.15}>
        <div className="mt-8 grid gap-8 rounded-2xl border border-white/10 bg-[#12121a] p-8 sm:p-10 lg:grid-cols-[1fr_1.1fr] transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
          <div className="flex flex-col justify-center">
            <span className="cosmic-text-xs font-medium uppercase tracking-normal text-[#86868b]">{h.wishlist.kicker}</span>
            <h3 className="mt-4 cosmic-text-3xl font-bold leading-[1.1] tracking-[-0.02em] text-[#f5f5f7]">
              What happens outside your store matters.
              <br />
              Start understanding it.
            </h3>
            <p className="mt-5 max-w-md cosmic-text-lg leading-relaxed text-[#a1a1aa]">{h.wishlist.sub}</p>
            <p className="mt-6 cosmic-text-xs leading-relaxed text-[#86868b]">
              {h.compat}
            </p>
            <button
              onClick={onPilot}
              className="mt-8 w-fit rounded-full border border-white/15 bg-[#1a1a24]/80 px-6 py-3 cosmic-text-sm font-medium text-[#f5f5f7] transition-all duration-200 hover:border-[#8B7CF6]/50 hover:text-[#8B7CF6] active:scale-[0.98]"
            >
              Or book a full pilot →
            </button>
          </div>

          {!sent ? (
            <form onSubmit={submit} className="flex flex-col gap-4" aria-label="Join the pilot list">
              <div>
                <label htmlFor="wl-brand" className="mb-1.5 block cosmic-text-sm font-medium text-[#f5f5f7]">
                  {PILOT_FORM.fields.brand.label}
                </label>
                <input
                  id="wl-brand"
                  required
                  placeholder={PILOT_FORM.fields.brand.placeholder}
                  className={inputCls}
                />
              </div>
              <div>
                <label htmlFor="wl-email" className="mb-1.5 block cosmic-text-sm font-medium text-[#f5f5f7]">
                  {PILOT_FORM.fields.email.label}
                </label>
                <input
                  id="wl-email"
                  type="email"
                  required
                  placeholder={PILOT_FORM.fields.email.placeholder}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputCls}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="wl-stores" className="mb-1.5 block cosmic-text-sm font-medium text-[#f5f5f7]">
                    Store Locations
                  </label>
                  <div className="relative">
                    <select id="wl-stores" className={`${inputCls} appearance-none pr-10`} defaultValue="1-5 Stores">
                      {PILOT_FORM.fields.locations.options.map((o) => (
                        <option key={o}>{o}</option>
                      ))}
                    </select>
                    <ChevronDown size={16} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-[#86868b]" />
                  </div>
                </div>
                <div>
                  <label htmlFor="wl-sector" className="mb-1.5 block cosmic-text-sm font-medium text-[#f5f5f7]">
                    {PILOT_FORM.fields.sector.label}
                  </label>
                  <div className="relative">
                    <select id="wl-sector" className={`${inputCls} appearance-none pr-10`} defaultValue={PILOT_FORM.fields.sector.options[0]}>
                      {PILOT_FORM.fields.sector.options.map((o) => (
                        <option key={o}>{o}</option>
                      ))}
                    </select>
                    <ChevronDown size={16} className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-[#86868b]" />
                  </div>
                </div>
              </div>
              <button
                type="submit"
                className="mt-2 inline-flex items-center justify-center gap-2 rounded-full bg-[#8B7CF6] px-7 py-3.5 cosmic-text-base font-semibold text-[#05050a] transition-all duration-200 hover:bg-[#6E5CE6] active:scale-[0.98]"
              >
                <Send size={15} strokeWidth={2.5} />
                Join the pilot list
              </button>
              <p className="cosmic-text-sm leading-relaxed text-[#86868b]">
                {PILOT_FORM.note} Replies land at {BRAND.email}.
              </p>
            </form>
          ) : (
            <div className="flex flex-col items-start justify-center rounded-2xl bg-[#1a1a24]/80 p-8 shadow-lg">
              <span className="grid h-12 w-12 place-items-center rounded-full bg-[#8B7CF6] text-[#05050a] font-bold">
                <Check size={22} strokeWidth={2.5} />
              </span>
              <h4 className="mt-5 cosmic-text-2xl font-bold text-[#f5f5f7]">{h.wishlist.successTitle}</h4>
              <p className="mt-3 cosmic-text-base leading-relaxed text-[#a1a1aa]">{h.wishlist.successBody}</p>
              {email && (
                <p className="mt-3 cosmic-text-sm text-[#86868b]">
                  {h.wishlist.successNote} {email}
                </p>
              )}
              <div className="mt-8 border-t border-white/10 pt-6">
                {feedback === null ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="cosmic-text-sm font-medium text-[#a1a1aa]">{h.wishlist.feedbackQ}</span>
                    <button
                      onClick={() => setFeedback("yes")}
                      className="rounded-full border border-white/15 px-4 py-2 cosmic-text-sm font-medium text-[#f5f5f7] transition-colors hover:border-[#8B7CF6]/50 hover:text-[#8B7CF6]"
                    >
                      {h.wishlist.feedbackYes}
                    </button>
                    <button
                      onClick={() => setFeedback("no")}
                      className="rounded-full border border-white/15 px-4 py-2 cosmic-text-sm font-medium text-[#f5f5f7] transition-colors hover:border-[#8B7CF6]/50 hover:text-[#8B7CF6]"
                    >
                      {h.wishlist.feedbackNo}
                    </button>
                  </div>
                ) : (
                  <p className="cosmic-text-sm font-medium text-[#a1a1aa]">{h.wishlist.feedbackThanks}</p>
                )}
              </div>
            </div>
          )}
        </div>
      </Reveal>
      </div>
    </section>
  )
}
