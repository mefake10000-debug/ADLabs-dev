import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { Reveal } from "../components/Reveal"
import { Section } from "../components/Section"
import { SectionHeader } from "../components/SectionHeader"
import { FAQ } from "../data/site"

export function Faq() {
  const f = FAQ
  const [openIdx, setOpenIdx] = useState<number | null>(0)

  return (
    <Section id="faq" className="site-scope scroll-mt-24" bg="#0c0c14">
      <div className="mx-auto max-w-[820px] px-6">
        <SectionHeader index={f.index} kicker={f.kicker} sub={f.sub}>
          {f.h2}
        </SectionHeader>

        <div className="mt-8 flex flex-col border-t border-white/10">
          {f.items.map((item, i) => {
            const open = openIdx === i
            return (
              <Reveal key={item.q} delay={Math.min(i * 0.03, 0.25)}>
                <div
                  className={`faq-item my-2 rounded-2xl border ${open ? 'border-[#8B7CF6]/40 bg-[#1a1a24]/80 shadow-[0_4px_16px_rgba(139,124,246,0.12)]' : 'border-white/10 bg-[#1a1a24]/80 hover:border-[#8B7CF6]/30 hover:shadow-[0_4px_12px_rgba(0,0,0,0.04)]'} px-6 transition-all duration-300`}
                  data-open={open}
                >
                  <button
                    type="button"
                    onClick={() => setOpenIdx(open ? null : i)}
                    aria-expanded={open}
                    className="flex w-full items-center justify-between gap-6 py-6 text-left"
                  >
                    <span className="flex items-baseline gap-4">
                      <span className="shrink-0 font-mono cosmic-text-2xs tracking-[0.14em] text-[#86868b]">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="font-semibold cosmic-text-xl leading-snug text-[#f5f5f7] sm:cosmic-text-xl">
                        {item.q}
                      </span>
                    </span>
                    <span
                      className={`grid h-9 w-9 shrink-0 place-items-center rounded-full border transition-all duration-300 ${
                        open
                          ? "rotate-180 border-[#8B7CF6]/50 bg-[#8B7CF6]/10 text-[#8B7CF6]"
                          : "border-white/15 text-[#a1a1aa]"
                      }`}
                    >
                      <ChevronDown size={16} strokeWidth={2.2} />
                    </span>
                  </button>
                  <div className="faq-answer">
                    <div>
                      <p className="pb-6 pl-10 pr-2 cosmic-text-base leading-relaxed text-[#a1a1aa]">{item.a}</p>
                    </div>
                  </div>
                </div>
              </Reveal>
            )
          })}
        </div>
      </div>
    </Section>
  )
}
