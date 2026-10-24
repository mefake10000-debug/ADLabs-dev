"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  LayoutDashboard, Store, Megaphone, Map, FileText, ClipboardList,
  Sun, Moon, Play, Presentation, ArrowLeft, ShieldCheck,
  BarChart3, Users, Package, Sparkles, ChartPie, History as HistoryIcon, Search,
  Eye,
} from "lucide-react"
import Link from "next/link"
import { Logo } from "../components/Logo"
import { Chip, Segmented } from "./ui"
import { TENANT, SIMULATED_NOTE } from "../data/dashboard"
import { Overview } from "./screens/Overview"
import { Stores, StoreDetail } from "./screens/Stores"
import { Campaigns } from "./screens/Campaigns"
import { Zones } from "./screens/Zones"
import { Brief } from "./screens/Brief"
import { Manager } from "./screens/Manager"
import { Storefront } from "./screens/Storefront"
import { Compare } from "./screens/Compare"
import { History } from "./screens/History"
import { Demographics } from "./screens/Demographics"
import { Product } from "./screens/Product"
import { Alerts } from "./screens/Alerts"
import { Tour } from "./screens/Tour"
import { Ads } from "./screens/Ads"
import { PresentMode } from "./PresentMode"
import { VoiceAssistant } from "./VoiceAssistant"
import { CmdPalette } from "./CmdPalette"
import { ProcessingControl } from "./ProcessingControl"

type Screen = "overview" | "storefront" | "stores" | "store" | "campaigns" | "zones" | "brief" | "manager" | "compare" | "history" | "demographics" | "product" | "alerts" | "tour" | "ads"
type Role = "Brand" | "Store"
type Theme = "light" | "dark"

const OWNER_NAME = "Alexa"
const OWNER_ROLE = "Brand owner · Maison Étoile"

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return "Good morning"
  if (h < 17) return "Good afternoon"
  return "Good evening"
}

type NavItem = { id: Screen; label: string; icon: typeof LayoutDashboard; badge?: number; color?: string }

const NAV_SECTIONS_BRAND: { label: string; items: NavItem[] }[] = [
  {
    label: "Run",
    items: [
      { id: "overview", label: "Overview", icon: LayoutDashboard, color: "#8B7CF6" },
      { id: "storefront", label: "Storefront", icon: Eye, color: "#3ECF8E" },
      { id: "stores", label: "Stores", icon: Store, color: "#5ac8fa" },
      { id: "zones", label: "Zones", icon: Map, color: "#FF9500" },
      { id: "brief", label: "Brief", icon: FileText, badge: 3, color: "#FF3B30" },
    ],
  },
  {
    label: "Prove",
    items: [
      { id: "campaigns", label: "Campaigns", icon: Megaphone, color: "#AF52DE" },
      { id: "ads", label: "Ads", icon: ChartPie, color: "#FF2D55" },
      { id: "compare", label: "Compare", icon: BarChart3, color: "#5856D6" },
      { id: "history", label: "History", icon: HistoryIcon, color: "#007AFF" },
    ],
  },
  {
    label: "Understand",
    items: [
      { id: "demographics", label: "People", icon: Users, color: "#FF9500" },
      { id: "product", label: "Product", icon: Package, color: "#34C759" },
      { id: "alerts", label: "Alerts", icon: ShieldCheck, badge: 4, color: "#FF3B30" },
      { id: "tour", label: "Tour", icon: Sparkles, color: "#8B7CF6" },
    ],
  },
]

const NAV_SECTIONS_STORE: { label: string; items: NavItem[] }[] = [
  {
    label: "Store",
    items: [
      { id: "manager", label: "Today", icon: ClipboardList, color: "#3ECF8E" },
      { id: "stores", label: "Stores", icon: Store, color: "#5ac8fa" },
      { id: "alerts", label: "Alerts", icon: ShieldCheck, badge: 4, color: "#FF3B30" },
    ],
  },
  {
    label: "Reference",
    items: [
      { id: "zones", label: "Zones", icon: Map, color: "#FF9500" },
      { id: "tour", label: "Tour", icon: Sparkles, color: "#8B7CF6" },
    ],
  },
]

const PAGE_TITLES: Record<Screen, string> = {
  overview: "Overview",
  storefront: "Storefront",
  stores: "Stores",
  store: "Store detail",
  campaigns: "Campaigns",
  zones: "Zones",
  brief: "Weekly Brief",
  manager: "Today",
  compare: "Compare",
  history: "History",
  demographics: "People",
  product: "Product",
  alerts: "Alerts",
  tour: "How you'll see it",
  ads: "Ads",
}

export function DashboardPage() {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("adlabs-theme")
      if (saved === "light" || saved === "dark") return saved
    }
    return "dark"
  })
  const [role, setRole] = useState<Role>("Brand")
  const [screen, setScreen] = useState<Screen>("overview")
  const [present, setPresent] = useState(false)
  const [selectedStore, setSelectedStore] = useState("madison")
  const [cmd, setCmd] = useState(false)
  const [now, setNow] = useState<Date | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setCmd((c) => !c)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  useEffect(() => {
    const tick = () => setNow(new Date())
    tick()
    const t = setInterval(tick, 1000 * 30)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    localStorage.setItem("adlabs-theme", theme)
  }, [theme])

  const changeRole = (r: Role) => {
    setRole(r)
    if (r === "Store" && screen !== "stores" && screen !== "store" && screen !== "manager") {
      setScreen("manager")
    }
    if (r === "Brand" && screen === "manager") {
      setScreen("overview")
    }
  }

  const navSections = role === "Brand" ? NAV_SECTIONS_BRAND : NAV_SECTIONS_STORE

  const renderScreen = () => {
    switch (screen) {
      case "overview": return <Overview onNavigate={(s) => setScreen(s as Screen)} />
      case "storefront": return <Storefront />
      case "stores": return <Stores onOpen={(id) => { setSelectedStore(id); setScreen("store") }} />
      case "store": return <StoreDetail storeId={selectedStore} />
      case "campaigns": return <Campaigns />
      case "zones": return <Zones />
      case "brief": return <Brief />
      case "manager": return <Manager />
      case "compare": return <Compare />
      case "history": return <History />
      case "demographics": return <Demographics />
      case "product": return <Product />
      case "alerts": return <Alerts />
      case "tour": return <Tour />
      case "ads": return <Ads />
      default: return <Overview />
    }
  }

  return (
    <div className="app-scope page-in relative min-h-screen" data-theme={theme} style={{ background: "var(--app-bg)" }}>
      <div aria-hidden className="app-glow" />
      <div className="relative mx-auto flex max-w-[1400px]">
        {/* Sidebar */}
        <aside className="sticky top-0 hidden h-screen w-[260px] shrink-0 flex-col border-r border-[var(--app-line)] px-4 py-6 lg:flex">
          <Link href="/" aria-label="Back to AD Labs website" className="px-2">
            <Logo dark={theme === "dark"} />
          </Link>

          <div className="mt-7 flex-1 overflow-y-auto" style={{ scrollBehavior: "smooth" }}>
            {navSections.map((sec) => (
              <div key={sec.label} className="mb-6">
                <p className="px-3 pb-2 font-inter cosmic-text-2xs font-bold uppercase tracking-[0.16em] text-[var(--app-faint)]">
                  {sec.label}
                </p>
                <div className="flex flex-col gap-1">
                  {sec.items.map((n) => {
                    const active = screen === n.id || (n.id === "stores" && screen === "store")
                    return (
                      <button
                        key={n.id}
                        onClick={() => setScreen(n.id)}
                        aria-current={active}
                        className="relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-left font-inter cosmic-text-sm font-medium transition-all duration-200 hover:bg-[var(--app-card)] hover:shadow-sm"
                        style={{ color: active ? "var(--app-text)" : "var(--app-sub)" }}
                      >
                        {active && (
                          <motion.span
                            layoutId="nav-active"
                            className="absolute inset-0 rounded-xl"
                            style={{ background: "var(--app-card)", boxShadow: "var(--app-shadow)" }}
                            transition={{ type: "spring", stiffness: 420, damping: 34 }}
                          />
                        )}
                        <span
                          className="relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-lg transition-all duration-200"
                          style={{
                            background: active ? `${n.color}20` : "var(--app-raise)",
                            color: active ? n.color : "var(--app-faint)",
                          }}
                        >
                          <n.icon size={16} strokeWidth={2.2} />
                        </span>
                        <span className="relative z-10 flex-1 truncate">{n.label}</span>
                        {n.badge != null && (
                          <span
                            className="relative z-10 grid h-5 min-w-5 place-items-center rounded-full px-1.5 font-inter cosmic-text-2xs font-bold"
                            style={{ background: `${n.color}20`, color: n.color }}
                          >
                            {n.badge}
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-auto flex flex-col gap-3">
            <div
              className="flex items-start gap-2.5 rounded-xl border border-[var(--app-line)] p-3.5"
              style={{ background: "var(--app-card)" }}
            >
              <ShieldCheck size={15} className="mt-0.5 shrink-0 text-[var(--app-gold)]" strokeWidth={2.2} />
              <p className="font-inter cosmic-text-xs leading-snug text-[var(--app-sub)]">
                Faces never leave the device. Aggregates only.
              </p>
            </div>
            <button
              onClick={() => setPresent(true)}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2.5 font-inter cosmic-text-sm font-semibold text-[var(--app-sub)] transition-colors hover:text-[var(--app-text)]"
            >
              <Presentation size={16} strokeWidth={2.1} />
              Present mode
            </button>
          </div>
        </aside>

        {/* Main */}
        <div className="min-w-0 flex-1">
          {/* Topbar */}
          <header className="sticky top-0 z-30 border-b border-[var(--app-line)] backdrop-blur-xl" style={{ background: "color-mix(in srgb, var(--app-bg) 82%, transparent)" }}>
            <div className="flex flex-wrap items-center gap-3 px-5 py-3.5 sm:px-7">
              <Link
                href="/"
                className="grid h-9 w-9 place-items-center rounded-full border border-[var(--app-line)] text-[var(--app-sub)] transition-colors hover:text-[var(--app-text)] lg:hidden"
                aria-label="Back to website"
              >
                <ArrowLeft size={16} />
              </Link>
              <div className="min-w-0">
                <p className="truncate font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">{TENANT.name}</p>
                <AnimatePresence mode="wait" initial={false}>
                  <motion.p
                    key={screen}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.18 }}
                    className="truncate font-inter cosmic-text-xs font-medium text-[var(--app-gold)]"
                  >
                    {PAGE_TITLES[screen]}
                  </motion.p>
                </AnimatePresence>
              </div>
              <div className="hidden min-w-0 items-center gap-2.5 sm:flex">
                <span className="h-5 w-px shrink-0" style={{ background: "var(--app-line)" }} />
                <span
                  className="grid h-8 w-8 shrink-0 place-items-center rounded-full font-inter cosmic-text-xs font-bold"
                  style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}
                  title={`${greeting()}, ${OWNER_NAME} · ${OWNER_ROLE}`}
                >
                  {OWNER_NAME[0]}
                </span>
              </div>
              <div className="ml-auto flex flex-wrap items-center gap-2.5">
                <span className="hidden items-center gap-1.5 font-mono cosmic-text-xs font-semibold font-num text-[var(--app-sub)] md:inline-flex">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full" style={{ background: "#8B7CF6" }} />
                  {now && now.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: false })}
                </span>
                <Chip tone="neutral">Preview</Chip>
                <Chip tone="gold" title={SIMULATED_NOTE}>
                  Demo
                </Chip>
                <Segmented options={["Brand", "Store"] as const} value={role} onChange={changeRole} />
                <button
                  onClick={() => setCmd(true)}
                  aria-label="Jump to a screen"
                  className="hidden h-9 items-center gap-2 rounded-full border border-[var(--app-line)] px-3 font-inter cosmic-text-xs font-semibold text-[var(--app-faint)] transition-colors hover:text-[var(--app-text)] md:flex"
                >
                  <Search size={13} strokeWidth={2.2} />
                  Jump
                  <kbd className="rounded border border-[var(--app-line)] px-1 font-inter cosmic-text-2xs">⌘K</kbd>
                </button>
                <button
                  onClick={() => setTheme(theme === "light" ? "dark" : "light")}
                  aria-label="Toggle theme"
                  className="grid h-9 w-9 place-items-center rounded-full border border-[var(--app-line)] text-[var(--app-sub)] transition-colors hover:text-[var(--app-text)]"
                >
                  {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
                </button>
                <button
                  onClick={() => setPresent(true)}
                  aria-label="Enter present mode"
                  className="hidden h-9 items-center gap-2 rounded-full px-4 font-inter cosmic-text-xs font-semibold text-[var(--app-card)] transition-transform hover:-translate-y-0.5 sm:flex"
                  style={{ background: "var(--app-text)" }}
                >
                  <Play size={13} strokeWidth={2.6} />
                  Present
                </button>
              </div>
            </div>
            {/* Mobile nav */}
            <div className="flex gap-2 overflow-x-auto px-4 pb-2.5 lg:hidden" style={{ scrollBehavior: "smooth", scrollbarWidth: "none" }}>
              {navSections.flatMap((s) => s.items).map((n) => {
                const active = screen === n.id || (n.id === "stores" && screen === "store")
                return (
                  <button
                    key={n.id}
                    onClick={() => setScreen(n.id)}
                    className="shrink-0 flex items-center gap-2 rounded-full px-3.5 py-2 font-inter cosmic-text-xs font-medium transition-all duration-200"
                    style={{
                      background: active ? `${n.color}20` : "var(--app-card)",
                      color: active ? n.color : "var(--app-sub)",
                      boxShadow: active ? "var(--app-shadow)" : "none",
                    }}
                  >
                    <n.icon size={14} strokeWidth={2.2} />
                    {n.label}
                  </button>
                )
              })}
            </div>
          </header>

          <main className="px-5 py-6 sm:px-7 sm:py-8">
            <ProcessingControl />
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={screen + role}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.24, ease: "easeOut" }}
              >
                {renderScreen()}
              </motion.div>
            </AnimatePresence>
          </main>

          <footer className="border-t border-[var(--app-line)] px-5 py-5 sm:px-7">
            <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">
              AD Labs Dashboard · {SIMULATED_NOTE} · © 2026 Ad Labs Tech Pvt Ltd
            </p>
          </footer>
        </div>
      </div>

      {present && <PresentMode theme={theme} onClose={() => setPresent(false)} />}
      <VoiceAssistant
        onNavigate={(s, storeId) => {
          if (s === "store" && storeId) {
            setSelectedStore(storeId)
            setScreen("store")
          } else {
            setScreen(s)
          }
        }}
      />
      <CmdPalette open={cmd} onClose={() => setCmd(false)} onNavigate={(id) => setScreen(id as Screen)} />
    </div>
  )
}
