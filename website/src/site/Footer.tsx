"use client"

import { useState } from "react"
import { ArrowUpRight, Check } from "lucide-react"
import type { ReactNode } from "react"
import Link from "next/link"
import { BRAND, SOCIALS, NAV_GROUPS } from "../data/site"
import { submitViaEmail } from "../utils/mailto"
import { Logo } from "../components/Logo"
import { LinkedInIcon, InstagramIcon } from "../components/BrandIcons"

const to = (href: string) => (href.startsWith("#") ? "/" + href : href)

export function Footer() {
  const year = new Date().getFullYear()
  const [email, setEmail] = useState("")
  const [subscribed, setSubscribed] = useState(false)

  const social = (url: string, label: string, icon: ReactNode) => (
    <a
      href={url || "#"}
      onClick={(e) => !url && e.preventDefault()}
      title={url ? label : `${label} — ${SOCIALS.label}`}
      aria-label={label}
      className={`grid h-10 w-10 place-items-center rounded-full border transition-all duration-200 ${
        url
          ? "border-[#16161f]/15 text-[#a1a1aa] hover:border-[#8B7CF6] hover:text-[#8B7CF6]"
          : "cursor-not-allowed border-[#16161f]/10 text-[#86868b]/60"
      }`}
    >
      {icon}
    </a>
  )

  return (
    <footer className="border-t border-white/10 bg-[#05050a] pb-10 pt-16 text-[#f5f5f7]">
      <div className="mx-auto max-w-[1200px] px-6">
        <div className="flex flex-col justify-between gap-12 lg:flex-row">
          <div className="max-w-sm">
            <Logo />
            <p className="mt-5 cosmic-text-sm leading-relaxed text-[#a1a1aa]">{BRAND.tagline}</p>

            <div className="mt-7">
              <p className="cosmic-text-xs font-medium text-[#86868b] uppercase tracking-normal">Store Updates · Monthly</p>
              {subscribed ? (
                <p className="mt-3 flex items-center gap-2 cosmic-text-sm font-medium text-[#f5f5f7]">
                  <span className="grid h-6 w-6 place-items-center rounded-full bg-[#8B7CF6] text-[#05050a] font-bold">
                    <Check size={13} strokeWidth={2.5} />
                  </span>
                  You're on the list — see you next month.
                </p>
              ) : (
                <form
                  className="mt-3 flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault()
                    if (email.trim()) {
                      submitViaEmail("Store updates — subscribe", [
                        { label: "Email", value: email.trim() },
                      ])
                      setSubscribed(true)
                    }
                  }}
                >
                  <label htmlFor="nl-email" className="sr-only">Email address</label>
                  <input
                    id="nl-email"
                    name="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@brand.com"
                    className="h-11 min-w-0 flex-1 rounded-full border border-[#16161f]/15 bg-[#1a1a24]/80 px-4 cosmic-text-sm text-[#f5f5f7] outline-none transition-colors placeholder:text-[#86868b] focus:border-[#8B7CF6]"
                  />
                  <button
                    type="submit"
                    className="h-11 shrink-0 rounded-full bg-[#8B7CF6] px-6 cosmic-text-sm font-semibold text-[#05050a] transition-colors hover:bg-[#6E5CE6]"
                  >
                    Join
                  </button>
                </form>
              )}
            </div>

            <div className="mt-7 flex gap-3">
              {social(SOCIALS.linkedin, "LinkedIn", <LinkedInIcon size={16} />)}
              {social(SOCIALS.instagram, "Instagram", <InstagramIcon size={16} />)}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-10 sm:grid-cols-3">
            {NAV_GROUPS.map((g) => (
              <nav key={g.id} aria-label={g.label}>
                <p className="cosmic-text-xs font-medium text-[#86868b] uppercase tracking-normal">{g.label}</p>
                <ul className="mt-4 flex flex-col gap-2.5">
                  {g.links.map((l) => (
                    <li key={l.href}>
                      <Link href={to(l.href)} className="cosmic-text-sm text-[#a1a1aa] transition-colors hover:text-[#f5f5f7]">
                        {l.label}
                        {l.new && <ArrowUpRight size={13} className="inline" />}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-white/10 pt-8 sm:flex-row">
          <p className="cosmic-text-xs text-[#86868b]">
            © {year} {BRAND.legal} · {BRAND.city}
          </p>
          <div className="flex items-center gap-4">
            <a
              href={`mailto:${BRAND.email}`}
              className="cosmic-text-xs text-[#86868b] transition-colors hover:text-[#8B7CF6]"
            >
              {BRAND.email}
            </a>
            <span className="cosmic-text-xs text-[#86868b]">{BRAND.domain}</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
