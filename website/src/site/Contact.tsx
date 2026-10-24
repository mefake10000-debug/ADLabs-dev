import { useState } from "react"
import { ArrowRight, Mail, Clock, MapPin, Send, Loader2 } from "lucide-react"
import { motion } from "framer-motion"
import { Reveal } from "../components/Reveal"
import { Section } from "../components/Section"
import { SectionHeader } from "../components/SectionHeader"
import { submitViaEmail } from "../utils/mailto"
import { CONTACT } from "../data/site"

const inputCls =
  "w-full rounded-xl border border-white/12 bg-[#1a1a24]/80 px-4 py-3 cosmic-text-base text-[#f5f5f7] outline-none transition-colors duration-200 placeholder:text-[#86868b] focus:border-[#8B7CF6]"

const labelCls = "mb-1.5 block cosmic-text-sm font-medium text-[#f5f5f7]"

export function Contact({ onPilot }: { onPilot: () => void }) {
  const c = CONTACT
  const f = c.fields
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)
  const [form, setForm] = useState({ name: "", email: "", brand: "", sector: "", message: "" })

  const set = (k: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => setForm((prev) => ({ ...prev, [k]: e.target.value }))

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setSending(true)
    window.setTimeout(() => {
      submitViaEmail("Contact — AD Labs", [
        { label: "Name", value: form.name },
        { label: "Email", value: form.email },
        { label: "Brand", value: form.brand },
        { label: "Sector", value: form.sector },
        { label: "Message", value: form.message },
      ])
      setSending(false)
      setSent(true)
    }, 700)
  }

  return (
    <Section id="contact" className="site-scope scroll-mt-24">
      <div className="mx-auto max-w-[1100px] px-6">
        <SectionHeader index={c.index} kicker={c.kicker} sub={c.sub}>
          {c.h2}
        </SectionHeader>

        <div className="mt-8 grid items-start gap-8 lg:grid-cols-[1fr_1.4fr]">
          <Reveal>
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-[#12121a] p-5 transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[rgba(139,124,246,0.1)] text-[#8B7CF6]">
                  <Mail size={18} strokeWidth={2} />
                </span>
                <div className="min-w-0">
                  <p className="cosmic-text-xs font-medium uppercase tracking-normal text-[#86868b]">Email</p>
                  <a href={`mailto:${c.email}`} className="mt-0.5 block truncate cosmic-text-base font-medium text-[#f5f5f7] hover:text-[#8B7CF6]">
                    {c.email}
                  </a>
                </div>
              </div>
              <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-[#12121a] p-5 transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[rgba(139,124,246,0.1)] text-[#8B7CF6]">
                  <MapPin size={18} strokeWidth={2} />
                </span>
                <div className="min-w-0">
                  <p className="cosmic-text-xs font-medium uppercase tracking-normal text-[#86868b]">The Lab</p>
                  <p className="mt-0.5 cosmic-text-base font-medium text-[#f5f5f7]">{c.city}</p>
                </div>
              </div>
              <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-[#12121a] p-5 transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[rgba(139,124,246,0.1)] text-[#8B7CF6]">
                  <Clock size={18} strokeWidth={2} />
                </span>
                <div className="min-w-0">
                  <p className="cosmic-text-xs font-medium uppercase tracking-normal text-[#86868b]">Response time</p>
                  <p className="mt-0.5 cosmic-text-base font-medium text-[#f5f5f7]">{c.response}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onPilot}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-full bg-[#8B7CF6] px-7 py-3.5 cosmic-text-base font-semibold text-[#05050a] transition-all duration-200 hover:bg-[#6E5CE6] active:scale-[0.98]"
              >
                Book a store pilot
                <ArrowRight size={16} strokeWidth={2.5} />
              </button>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="rounded-2xl border border-white/10 bg-[#1a1a24]/80 p-7 sm:p-9 transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
              {sent ? (
                <motion.div
                  className="flex min-h-[360px] flex-col items-center justify-center text-center"
                  initial={{ opacity: 0, scale: 0.94 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.45, ease: [0.25, 1, 0.5, 1] }}
                >
                  <motion.span
                    className="grid h-14 w-14 place-items-center rounded-full bg-[#8B7CF6] text-[#05050a] font-bold"
                    initial={{ scale: 0.4, rotate: -12 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ type: "spring", stiffness: 260, damping: 16, delay: 0.08 }}
                  >
                    <Send size={22} strokeWidth={2.5} />
                  </motion.span>
                  <h3 className="mt-6 cosmic-text-2xl font-bold text-[#f5f5f7]">{c.successTitle}</h3>
                  <p className="mt-3 max-w-sm whitespace-pre-line cosmic-text-base leading-relaxed text-[#a1a1aa]">
                    {c.successBody}
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setSent(false)
                      setForm({ name: "", email: "", brand: "", sector: "", message: "" })
                    }}
                    className="mt-8 cosmic-text-sm font-medium text-[#8B7CF6] underline-offset-4 hover:underline"
                  >
                    Send another message
                  </button>
                </motion.div>
              ) : (
                <form onSubmit={submit} className="flex flex-col gap-5">
                  <div className="grid gap-5 sm:grid-cols-2">
                    <div>
                      <label htmlFor="c-name" className={labelCls}>{f.name.label}</label>
                      <input id="c-name" required value={form.name} onChange={set("name")} placeholder={f.name.placeholder} className={inputCls} />
                    </div>
                    <div>
                      <label htmlFor="c-email" className={labelCls}>{f.email.label}</label>
                      <input id="c-email" type="email" required value={form.email} onChange={set("email")} placeholder={f.email.placeholder} className={inputCls} />
                    </div>
                  </div>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <div>
                      <label htmlFor="c-brand" className={labelCls}>{f.brand.label}</label>
                      <input id="c-brand" required value={form.brand} onChange={set("brand")} placeholder={f.brand.placeholder} className={inputCls} />
                    </div>
                    <div>
                      <label htmlFor="c-sector" className={labelCls}>{f.sector.label}</label>
                      <select id="c-sector" required value={form.sector} onChange={set("sector")} className={inputCls}>
                        <option value="" disabled>{f.sector.placeholder}</option>
                        {f.sector.options.map((o) => (
                          <option key={o} value={o}>{o}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="c-message" className={labelCls}>{f.message.label}</label>
                    <textarea
                      id="c-message"
                      required
                      rows={4}
                      value={form.message}
                      onChange={set("message")}
                      placeholder={f.message.placeholder}
                      className={`${inputCls} resize-y`}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={sending}
                    className="flex w-full items-center justify-center gap-2 rounded-full bg-[#16161f] px-7 py-3.5 cosmic-text-base font-medium text-white transition-all duration-200 hover:bg-[#8B7CF6] hover:text-[#05050a] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-90"
                  >
                    {sending ? (
                      <>
                        <Loader2 size={15} strokeWidth={2.5} className="animate-spin" />
                        Sending…
                      </>
                    ) : (
                      <>
                        {c.submit}
                        <Send size={15} strokeWidth={2.5} />
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>
          </Reveal>
        </div>
      </div>
    </Section>
  )
}
