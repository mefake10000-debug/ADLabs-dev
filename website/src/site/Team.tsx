import { Reveal } from "../components/Reveal"
import { Section } from "../components/Section"
import { SectionHeader } from "../components/SectionHeader"
import { FlipCard, AnswerPanel } from "../components/FlipCard"
import { FOUNDERS, BRAND, type Founder } from "../data/site"
import { FlaskConical, ShieldCheck, Target } from "lucide-react"

const HAIR: Record<Founder["avatar"]["hairPath"], string> = {
  A: "M25 41 Q25 17 50 17 Q75 17 75 41 Q75 29 71 26 Q64 21 50 21 Q36 21 29 26 Q25 29 25 41 Z",
  B: "M25 43 Q25 19 50 19 Q75 19 75 43 Q75 32 70 29 L70 30 Q68 27 66 27 Q60 24 56 24 Q53 22 50 22 Q47 22 50 22 Q40 27 34 27 Q32 27 30 30 Q25 32 25 43 Z",
  C: "M25 44 Q23 22 34 17 Q43 13.5 50 14 Q57 13.5 66 17 Q77 22 75 44 L73 44 Q71 34 67 30 Q63 26 57 24 Q52 23 50 23 Q48 23 43 24 Q37 26 33 30 Q29 34 27 44 Z",
}

function FounderAvatar({ f, idx }: { f: Founder; idx: number }) {
  const a = f.avatar
  const gradId = `avatarBg-${idx}`
  return (
    <svg viewBox="0 0 100 100" className="h-[120px] w-[120px] transition-all duration-500 group-hover:-translate-y-2 group-hover:scale-[1.05]" aria-hidden>
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="rgba(139,124,246,0.08)" />
          <stop offset="100%" stopColor="rgba(139,124,246,0.02)" />
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r="48" fill={`url(#${gradId})`} />
      <circle cx="50" cy="50" r="48" fill="none" stroke="rgba(139,124,246,0.12)" strokeWidth="1.5" />
      <path d="M20 100 Q32 72 50 70 Q68 72 80 100 Z" fill={a.shirt} />
      <rect x="43" y="60" width="14" height="9" rx="3.5" fill={a.skin} />
      <circle cx="26.5" cy="45" r="5" fill={a.skin} />
      <circle cx="73.5" cy="45" r="5" fill={a.skin} />
      <ellipse cx="50" cy="43" rx="23.5" ry="26.5" fill={a.skin} />
      <path d={HAIR[a.hairPath]} fill={a.hair} />
      {a.glasses && (
        <g stroke="#16161f" strokeWidth="1.8" fill="none">
          <circle cx="41" cy="42" r="6.2" />
          <circle cx="59" cy="42" r="6.2" />
          <line x1="47.2" y1="42" x2="52.8" y2="42" />
        </g>
      )}
      <circle cx="40.5" cy="42.5" r="2.05" fill="#16161f" />
      <circle cx="59.5" cy="42.5" r="2.05" fill="#16161f" />
      <path d="M36 36 Q40.5 33.5 45 36" stroke="#16161f" strokeWidth="1.4" fill="none" strokeLinecap="round" opacity="0.5" />
      <path d="M55 36 Q59.5 33.5 64 36" stroke="#16161f" strokeWidth="1.4" fill="none" strokeLinecap="round" opacity="0.5" />
      <path d="M43.5 53.5 Q50 58 56.5 53.5" stroke="#16161f" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  )
}

const founderCards = FOUNDERS.map((f, i) => (
  <Reveal key={f.name} delay={i * 0.1} fade>
    <FlipCard
      back={<AnswerPanel eyebrow="THE OBSESSION" note={f.focus} />}
      front={
        <article className="site-card site-card-glare group h-full p-8">
          <div className="flex flex-col items-center text-center h-full">
            <div className="flex w-fit items-center justify-center rounded-2xl bg-[#12121a] p-4 ring-1 ring-white/10 transition-all duration-500 group-hover:ring-[#8B7CF6]/30">
              <FounderAvatar f={f} idx={i} />
            </div>
            <h3 className="mt-8 cosmic-text-2xl font-bold text-[#f5f5f7]">{f.name}</h3>
            <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-[#8B7CF6]/08 px-4 py-2">
              <span className="cosmic-text-xs font-semibold text-[#8B7CF6]">{f.role}</span>
            </div>
            <p className="mt-6 max-w-xs mx-auto cosmic-text-sm leading-relaxed text-[#a1a1aa] flex-1">
              {f.focus.split(" — ")[0] || f.focus.slice(0, 80)}…
            </p>
            <div className="mt-6 pt-5 border-t border-white/8 w-full">
              <span className="cosmic-text-xs font-medium text-[#8B7CF6] flex items-center justify-center gap-2">
                Hover or tap to learn more
                <span className="inline-block transition-transform duration-300 group-hover:translate-x-1">→</span>
              </span>
            </div>
          </div>
        </article>
      }
    />
  </Reveal>
))

const valueCards = [
  {
    icon: FlaskConical,
    title: "Evidence Over Opinion",
    desc: "Every feature ships with its proof chain. If a stat can't be reproduced by hand, it doesn't print. The Monday Brief is audited, not authored.",
  },
  {
    icon: ShieldCheck,
    title: "Privacy By Architecture",
    desc: "Not a policy. A constraint. The system literally cannot watch — it counts. Zero faces. Zero cloud video. Zero re-identification. By design, not promise.",
  },
  {
    icon: Target,
    title: "Verdicts, Not Dashboards",
    desc: "Numbers that end in a move. The A/B engine decides keep-or-kill. The Monday Brief delivers three actions. No dashboards to babysit.",
  },
].map((v, i) => (
  <Reveal key={v.title} delay={0.08 * i}>
    <div className="group rounded-2xl border border-white/8 bg-[#1a1a24]/80 p-8 transition-all duration-500 hover:-translate-y-2 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
      <span className="grid h-14 w-14 place-items-center rounded-2xl bg-[#8B7CF6]/10 text-[#8B7CF6] mb-5 transition-transform duration-500 group-hover:scale-110 group-hover:-rotate-3">
        <v.icon size={24} strokeWidth={1.8} />
      </span>
      <h4 className="cosmic-text-xl font-semibold text-[#f5f5f7] mb-3">{v.title}</h4>
      <p className="cosmic-text-sm leading-relaxed text-[#a1a1aa]">{v.desc}</p>
    </div>
  </Reveal>
))

export function Team() {
  return (
    <Section id="team" className="site-scope scroll-mt-24">
      <div className="mx-auto max-w-[1200px] px-6">
        <SectionHeader
          index="11"
          kicker="The Lab"
          sub={`Founded in ${BRAND.founded} in ${BRAND.city}. Retail people and machine people — building the instrument the street was missing.`}
        >
          Small team. Singular obsession.
        </SectionHeader>

        <Reveal delay={0.1}>
          <div className="mt-8 max-w-3xl mx-auto text-center">
            <h3 className="cosmic-text-3xl font-bold text-[#f5f5f7] sm:cosmic-text-4xl leading-tight">
              One question started the company the industry couldn't answer:
            </h3>
            <p className="mt-8 max-w-2xl mx-auto cosmic-text-lg leading-relaxed text-[#a1a1aa]">
              <span className="text-[#f5f5f7] font-semibold">"Did the window work?"</span> — and nobody could prove it.
              Not with footfall. Not with sales. The decision happened at the glass, and the tools only counted who came inside.
            </p>
            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {[
                { n: "3–8s", label: "how long a shopper spends judging a window (Gajjar, 2024)" },
                { n: "86–92%", label: "of Indian retail still happens offline (Brickwork Ratings, 2024)" },
                { n: "1", label: "sensor answers it, privacy-first and on-device" },
              ].map((d) => (
                <div key={d.label} className="rounded-2xl border border-white/8 bg-[#1a1a24]/70 px-6 py-5">
                  <p className="cosmic-text-2xl font-bold text-[#8B7CF6] leading-none">{d.n}</p>
                  <p className="mt-2 cosmic-text-xs leading-snug text-[#a1a1aa]">{d.label}</p>
                </div>
              ))}
            </div>
            <p className="mt-8 max-w-2xl mx-auto cosmic-text-base leading-relaxed text-[#a1a1aa]">
              We built the instrument to answer that question. On-device. Privacy-first. Sub-second. So a boutique owner knows
              what the street decided, not what the spreadsheet guessed.
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.15}>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {founderCards}
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="mt-8 rounded-3xl border border-white/10 bg-[#1a1a24]/80 p-8 sm:p-12 transition-all duration-300 hover:border-[#8B7CF6]/40 hover:shadow-[0_12px_36px_rgba(139,124,246,0.15)]">
            <div className="text-center mb-12">
              <h3 className="cosmic-text-2xl font-bold text-[#f5f5f7] sm:cosmic-text-3xl">Three Principles That Guide Every Decision</h3>
              <p className="mt-4 max-w-xl mx-auto cosmic-text-base text-[#a1a1aa]">Not values on a wall. Constraints we design into the product.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {valueCards}
            </div>
          </div>
        </Reveal>
      </div>
    </Section>
  )
}
