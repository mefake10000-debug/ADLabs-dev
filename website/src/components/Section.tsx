import type { ReactNode } from "react"
import { motion, useReducedMotion } from "framer-motion"

const EASE = [0.25, 1, 0.5, 1] as const

/**
 * Section wrapper with consistent vertical rhythm and optional fade-in.
 * Standardised padding: py-20 lg:py-28 — uniform across all home page sections.
 */
export function Section({
  id,
  children,
  className = "",
  bg = "#05050a",
  fade = "up",
  pad = true,
}: {
  id?: string
  children: ReactNode
  className?: string
  bg?: string
  fade?: "up" | "fade" | "none"
  pad?: boolean
}) {
  const reduce = useReducedMotion()
  const initial = fade === "none" || reduce ? false : { opacity: 0, y: fade === "up" ? 20 : 0 }

  return (
    <section
      id={id}
      className={`relative ${pad ? "py-12 sm:py-16 lg:py-20" : ""} ${className}`}
      style={{ background: bg }}
    >
      <motion.div
        className="relative"
        initial={initial}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "0px 0px -40px 0px" }}
        transition={{ duration: 0.7, ease: EASE }}
      >
        {children}
      </motion.div>
    </section>
  )
}

/**
 * Gradient divider between sections — a soft glowing line that separates content blocks.
 */
export function SectionDivider({ color = "#8B7CF6", opacity = 0.15 }: { color?: string; opacity?: number }) {
  return (
    <div className="relative h-px w-full" aria-hidden>
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{
          background: `linear-gradient(90deg, transparent, ${color}${Math.round(opacity * 255).toString(16).padStart(2, "0")}, transparent)`,
        }}
      />
    </div>
  )
}
