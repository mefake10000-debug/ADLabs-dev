import { SectionHeader } from "../components/SectionHeader"
import { Reveal } from "../components/Reveal"
import { Section } from "../components/Section"
import { Users, Store, Briefcase, Megaphone, Sparkles, ArrowRight } from "lucide-react"
import Link from "next/link"

const PILLARS = [
  {
    icon: Users,
    title: "Consumer Intelligence",
    body: "Who actually comes to your shop — at a level footfall will never reach. Behaviour without identity.",
    ships: ["Anonymised demographics", "Deep-look share", "Stop-to-enter"],
    tint: "var(--app-accent)",
  },
  {
    icon: Store,
    title: "Store Intelligence",
    body: "The storefront as a measurable funnel — who stops at the glass, enters, browses and buys.",
    ships: ["Street footfall", "Window stop rate", "Dwell & zone heat"],
    tint: "var(--app-accent)",
  },
  {
    icon: Briefcase,
    title: "Staffing",
    body: "Put the floor where the demand is. Peak windows, queue heat and shift alignment from real traffic.",
    ships: ["Peak windows", "Queue waits", "Shift alignment"],
    tint: "var(--app-accent)",
  },
  {
    icon: Megaphone,
    title: "Ads",
    body: "Offline advertising with an ROI number — from sighting on the street to engagement in store.",
    ships: ["Sighting → entry attribution", "Physical A/B", "Campaign ROI"],
    tint: "var(--app-accent)",
  },
  {
    icon: Sparkles,
    title: "Insights",
    body: "Every week, a Brief that tells you what to change — and the measured number to prove it did.",
    ships: ["Monday Brief", "Anomaly alerts", "4-week forecast"],
    tint: "var(--app-accent)",
  },
]

export function Pillars() {
  return (
    <Section id="pillars" className="site-scope scroll-mt-24" bg="#05050a">
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader
          index="03"
          kicker="The Five Product Families"
          sub="AD Labs organizes as five families — consumer intelligence, store intelligence, staffing, ads and insights. They share one edge box, one privacy charter and one weekly rhythm."
        >
          One sensor. <em className="em-accent">Five families of intelligence.</em>
        </SectionHeader>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {PILLARS.map((p, i) => {
            const Icon = p.icon
            return (
              <Reveal key={p.title} delay={i * 0.07}>
                <article className="site-card site-card-glare group flex h-full flex-col p-6">
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-[#8B7CF6]/10 text-[#8B7CF6] transition-all duration-300 group-hover:scale-110 group-hover:bg-[#8B7CF6] group-hover:text-[#05050a]">
                    <Icon size={20} strokeWidth={1.9} />
                  </span>
                  <h3 className="mt-4 font-serif cosmic-text-xl font-semibold leading-snug text-[#f5f5f7]">
                    {p.title}
                  </h3>
                  <p className="mt-2 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{p.body}</p>
                  <div className="mt-4 flex flex-wrap gap-1.5 border-t border-white/8 pt-4">
                    {p.ships.map((s) => (
                      <span
                        key={s}
                        className="rounded-full border border-[#8B7CF6]/20 bg-[#8B7CF6]/8 px-2.5 py-1 font-mono cosmic-text-2xs tracking-[0.12em] text-[#8B7CF6]"
                      >
                        {s.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </article>
              </Reveal>
            )
          })}

          {/* CTA tile completes the grid */}
          <Reveal delay={0.35}>
            <div className="flex h-full flex-col justify-between overflow-hidden rounded-3xl border border-[#8B7CF6]/25 bg-[#1a1a24] p-6">
              <div>
                <p className="font-mono cosmic-text-2xs tracking-[0.16em] text-[#8B7CF6]">ONE EDGE BOX · ALL FIVE</p>
                <h3 className="mt-3 font-serif cosmic-text-xl font-semibold leading-snug text-[#f5f5f7]">
                  See every family working on one storefront.
                </h3>
                <p className="mt-2 cosmic-text-sm leading-relaxed text-[#a1a1aa]">
                  The live demo and the scoping flow walk through all five — about five minutes of your day.
                </p>
              </div>
              <div className="mt-6 flex flex-col gap-2.5">
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 rounded-full bg-[#8B7CF6] px-5 py-3 cosmic-text-sm font-semibold text-[#05050a] transition-all duration-200 hover:bg-[#6E5CE6] hover:-translate-y-0.5 active:scale-[0.98]"
                >
                  Open the live demo <ArrowRight size={15} strokeWidth={2.4} />
                </Link>
                <Link
                  href="/discover"
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 px-5 py-3 cosmic-text-sm font-medium text-[#f5f5f7] transition-all duration-200 hover:border-[#8B7CF6]/40 hover:text-[#8B7CF6]"
                >
                  Scope your pilot
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </Section>
  )
}
