"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Menu, X, ArrowRight, ChevronDown } from "lucide-react"
import { useScroll, useSpring, motion, AnimatePresence } from "framer-motion"
import { BRAND, NAV_GROUPS } from "../data/site"
import { Logo } from "../components/Logo"

const HOME_SECTION_IDS = [
  "top",
  "blindspot",
  "sensor",
  "demo",
  "journey",
  "pillars",
  "atelier",
  "proof",
  "system",
  "metrics",
  "flow",
  "privacy",
  "why",
  "sectors",
  "mission",
  "team",
  "how",
  "pricing",
  "faq",
  "contact",
]

export function Nav({ onPilot }: { onPilot: () => void }) {
  const router = useRouter()
  const pathname = usePathname()
  const headerRef = useRef<HTMLElement | null>(null)
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const [menu, setMenu] = useState<string | null>(null)
  const [active, setActive] = useState("")
  // Assume the home layout at SSR/hydration; correct after mount so static
  // exports served from file:// (where pathname is the filesystem path) hydrate cleanly.
  const [onHome, setOnHome] = useState(true)
  useEffect(() => {
    const clean = (pathname || "/").replace(/\/(index\.html)?\/?$/, "")
    // oxlint-disable-next-line react/set-state-in-effect
    setOnHome(clean === "" || clean === "/")
  }, [pathname])
  const { scrollYProgress } = useScroll()
  const progress = useSpring(scrollYProgress, { stiffness: 130, damping: 28, restDelta: 0.001 })

  /* Close menus when navigation changes route */
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    setOpen(false)
    setMenu(null)
  }, [pathname])

  /* Scroll to a hash target after the page mounts (cross-page one-click reach) */
  useEffect(() => {
    if (typeof window === "undefined") return
    const hash = window.location.hash.slice(1)
    if (hash) {
      requestAnimationFrame(() => {
        const el = document.getElementById(hash)
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" })
        else window.scrollTo({ top: 0 })
      })
    } else {
      window.scrollTo({ top: 0 })
    }
  }, [pathname])

  /* Track the section currently in view on the home page */
  useEffect(() => {
    const fn = () => {
      const probe = window.scrollY + 160
      let cur = ""
      for (const id of HOME_SECTION_IDS) {
        const el = document.getElementById(id)
        if (el && el.offsetTop <= probe) cur = id
      }
      setActive(cur)
    }
    fn()
    window.addEventListener("scroll", fn, { passive: true })
    return () => window.removeEventListener("scroll", fn)
  }, [onHome])

  /* Frosted header once the page is scrolled */
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 12)
    fn()
    window.addEventListener("scroll", fn, { passive: true })
    return () => window.removeEventListener("scroll", fn)
  }, [])

  /* Outside-click + Escape close the menus */
  useEffect(() => {
    const onDown = (e: PointerEvent) => {
      if (headerRef.current && !headerRef.current.contains(e.target as Node)) {
        setMenu(null)
        setOpen(false)
      }
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMenu(null)
        setOpen(false)
      }
    }
    document.addEventListener("pointerdown", onDown)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("pointerdown", onDown)
      document.removeEventListener("keydown", onKey)
    }
  }, [])

  /* Smooth-scroll to a section id, updating the URL without history spam */
  const scrollToHash = (id: string) => {
    const el = document.getElementById(id)
    if (el) {
      const sm = window.getComputedStyle(el).scrollMarginTop
      const offset = sm ? (parseFloat(sm) || 0) : 96
      window.scrollTo({ top: Math.max(0, el.getBoundingClientRect().top + window.scrollY - offset), behavior: "smooth" })
      history.replaceState(null, "", `#${id}`)
    }
  }

  const closeAll = () => {
    setMenu(null)
    setOpen(false)
  }

  const isExported = typeof window !== "undefined" && typeof (window as unknown as { __ADL?: string }).__ADL === "string"
  const fileRel = (href: string) => {
    const base = (window as unknown as { __ADL?: string }).__ADL ?? ""
    const hashIdx = href.indexOf("#")
    const hash = hashIdx === -1 ? "" : href.slice(hashIdx)
    const path = href.slice(0, hashIdx === -1 ? href.length : hashIdx).replace(/^\/+|\/+$/g, "")
    return path ? `${base}${path}/index.html${hash}` : `${base}index.html${hash}`
  }

  /* Is the script running from a static export (file:// or a local server)? */
  const exportedAt = (): boolean => {
    if (typeof window === "undefined") return false
    return typeof (window as unknown as { __ADL?: string }).__ADL === "string"
  }

  /* One-click reach from anywhere: same page → smooth scroll; other page → navigate then scroll */
  const go = (href: string) => {
    closeAll()
    const exported = exportedAt()
    if (href.startsWith("#")) {
      if (!exported && !onHome) {
        router.push("/" + href)
      } else if (onHome) {
        scrollToHash(href.slice(1))
      } else {
        window.location.assign(`${fileRel("")}#${href.slice(1)}`)
      }
    } else {
      const [path, hash] = href.split("#")
      if (hash && onHome && (!path || path === "/")) {
        scrollToHash(hash)
      } else if (!exported) {
        router.push(href)
      } else {
        window.location.assign(fileRel(href))
      }
    }
  }

  const goHome = () => {
    closeAll()
    if (onHome) {
      history.replaceState(null, "", window.location.pathname)
      window.scrollTo({ top: 0, behavior: "smooth" })
    } else if (isExported) {
      window.location.href = fileRel("/")
    } else {
      router.push("/")
    }
  }

  const activeItemHref = active ? `#${active}` : ""

  return (
    <header
      ref={headerRef}
      className={`fixed inset-x-0 top-0 z-40 transition-all duration-300 ${
        scrolled || menu
          ? "border-b border-white/10 bg-[#05050a]/85 backdrop-blur-xl"
          : "border-b border-transparent bg-transparent"
      }`}
      style={{ color: "#f5f5f7" }}
    >
      <div className="absolute inset-x-0 top-0 h-[3px] origin-left">
        <motion.div className="h-full w-full origin-left" style={{ scaleX: progress, background: "#8B7CF6" }} />
      </div>

      <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between gap-6 px-6">
        <Link href="/" onClick={goHome} aria-label="AD Labs — digital storefront home" className="shrink-0 transition-opacity hover:opacity-75">
          <Logo />
        </Link>

        {/* Desktop grouped menu */}
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary">
          {NAV_GROUPS.map((g) => {
            const isOpen = menu === g.id
            const groupActive = g.links.some((l) => l.href.slice(1) === active)
            return (
              <div key={g.id} className="relative">
                <button
                  type="button"
                  onClick={() => setMenu(isOpen ? null : g.id)}
                  aria-expanded={isOpen}
                  aria-haspopup="true"
                  className={`inline-flex items-center gap-1 rounded-full px-4 py-2 cosmic-text-sm font-medium transition-colors duration-200 ${
                    groupActive || isOpen ? "text-[#8B7CF6]" : "text-[#f5f5f7] hover:text-[#8B7CF6]"
                  }`}
                >
                  {g.label}
                  <ChevronDown
                    size={14}
                    strokeWidth={2}
                    className={`transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                  />
                </button>

                <AnimatePresence>
                  {isOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                      transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                      className="absolute left-0 top-full z-50 mt-2 w-[360px] origin-top rounded-2xl border border-white/10 bg-[#12121a]/95 p-2 shadow-[0_24px_60px_rgba(0,0,0,0.55)] backdrop-blur-xl"
                    >
                      <p className="px-3 pb-2 pt-1.5 cosmic-text-2xs font-semibold uppercase tracking-[0.18em] text-[#86868b]">
                        {g.label}
                      </p>
                      <div className={`grid gap-0.5 ${g.links.length > 5 ? "sm:grid-cols-2" : ""}`}>
                        {g.links.map((l, i) => {
                          const isActiveItem = onHome && l.href === activeItemHref
                          return (
                            <button
                              key={l.href}
                              type="button"
                              onClick={() => go(l.href)}
                              className="group flex flex-col rounded-xl px-3 py-2.5 text-left transition-colors duration-150 hover:bg-[#8B7CF6]/10"
                            >
                              <span className="flex items-center gap-2 cosmic-text-sm font-medium text-[#f5f5f7]">
                                <span className="font-mono cosmic-text-2xs text-[#8B7CF6]/70">{String(i + 1).padStart(2, "0")}</span>
                                {l.label}
                                {l.new && (
                                  <span className="rounded-full bg-[#8B7CF6] px-1.5 py-px cosmic-text-2xs font-bold uppercase tracking-wide text-[#05050a]">
                                    new
                                  </span>
                                )}
                                {isActiveItem && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[#8B7CF6]" />}
                              </span>
                              {l.desc && <span className="mt-0.5 pl-5 cosmic-text-xs leading-snug text-[#86868b]">{l.desc}</span>}
                            </button>
                          )
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}
        </nav>

        <div className="flex shrink-0 items-center gap-2.5">
          {!onHome && (
            <Link
              href="/"
              onClick={closeAll}
              className="hidden rounded-full px-4 py-2 cosmic-text-sm font-medium text-[#f5f5f7] transition-colors duration-200 hover:bg-white/5 hover:text-[#8B7CF6] sm:block"
            >
              Home
            </Link>
          )}
          <Link
            href="/discover"
            onClick={closeAll}
            className="hidden items-center gap-1.5 rounded-full px-4 py-2 cosmic-text-sm font-medium text-[#8B7CF6] transition-all duration-200 hover:bg-[#8B7CF6]/10 sm:inline-flex"
          >
            Discover
            <ArrowRight size={14} strokeWidth={2.5} />
          </Link>
          <button
            onClick={() => {
              closeAll()
              onPilot()
            }}
            className="hidden rounded-full bg-[#8B7CF6] px-5 py-2 cosmic-text-sm font-semibold text-[#05050a] transition-all duration-200 hover:bg-[#6E5CE6] active:scale-[0.98] sm:block"
          >
            Book a Pilot
          </button>
          <button
            onClick={() => {
              setMenu(null)
              setOpen(!open)
            }}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            className="grid h-9 w-9 place-items-center rounded-full border border-white/15 transition-colors lg:hidden text-[#f5f5f7]"
          >
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden border-t border-white/10 bg-[#05050a]/95 text-[#f5f5f7] backdrop-blur-xl lg:hidden"
          >
            <div className="px-6 pb-5 pt-2">
              <nav className="flex flex-col" aria-label="Mobile">
                <Link
                  href="/"
                  onClick={() => closeAll()}
                  className="flex items-center justify-between border-b py-3 cosmic-text-base font-medium text-[#f5f5f7] active:opacity-60"
                  style={{ borderColor: "rgba(255,255,255,0.1)" }}
                >
                  Home
                </Link>
                {NAV_GROUPS.map((g) => {
                  const expanded = menu === g.id
                  return (
                    <div key={g.id} className="border-b" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
                      <button
                        type="button"
                        onClick={() => setMenu(expanded ? null : g.id)}
                        aria-expanded={expanded}
                        className="flex w-full items-center justify-between py-3 text-left cosmic-text-base font-semibold active:opacity-60"
                      >
                        {g.label}
                        <ChevronDown size={16} className={`text-[#86868b] transition-transform duration-200 ${expanded ? "rotate-180" : ""}`} />
                      </button>
                      {expanded && (
                        <div className="flex flex-col pb-3">
                          {g.links.map((l) => (
                            <button
                              key={l.href}
                              type="button"
                              onClick={() => go(l.href)}
                              className="flex items-center justify-between rounded-lg py-2.5 pl-3 text-left cosmic-text-base text-[#e8e8ed] active:opacity-60"
                            >
                              <span>
                                {l.label}
                                {l.desc && <span className="ml-2 cosmic-text-xs text-[#86868b]">— {l.desc}</span>}
                              </span>
                              <ArrowRight size={14} className="text-[#86868b]" />
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}

                <Link
                  href="/discover"
                  onClick={() => closeAll()}
                  className="flex items-center justify-between border-b py-3 cosmic-text-base font-medium text-[#8B7CF6] active:opacity-60"
                  style={{ borderColor: "rgba(255,255,255,0.1)" }}
                >
                  Discover
                  <ArrowRight size={14} className="text-[#86868b]" />
                </Link>

                <button
                  onClick={() => {
                    closeAll()
                    onPilot()
                  }}
                  className="mt-4 w-full rounded-full bg-[#8B7CF6] px-7 py-3 cosmic-text-base font-semibold text-[#05050a]"
                >
                  Book a Pilot
                </button>
                <p className="pt-4 text-center cosmic-text-xs text-[#86868b]">
                  {BRAND.city} · {BRAND.email}
                </p>
              </nav>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
