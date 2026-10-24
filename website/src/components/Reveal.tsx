import { motion, useReducedMotion } from "framer-motion"
import type { ReactNode } from "react"

const EASE = [0.16, 1, 0.3, 1] as const

type Dir = "up" | "down" | "left" | "right" | "none"

export function Reveal({
  children,
  delay = 0,
  duration = 0.75,
  y = 26,
  x = 0,
  dir = "up",
  scale = 1,
  blur = 0,
  once = true,
  className,
  fade = false,
}: {
  children: ReactNode
  delay?: number
  duration?: number
  y?: number
  x?: number
  dir?: Dir
  scale?: number
  blur?: number
  once?: boolean
  className?: string
  /** Fade-only reveal — never sets a transform. Use for 3D/flip children so an ancestor transform doesn't flatten 3D context. */
  fade?: boolean
}) {
  const reduce = useReducedMotion()
  if (reduce) {
    return <div className={className}>{children}</div>
  }
  if (fade) {
    return (
      <motion.div
        className={className}
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once, margin: "-60px" }}
        transition={{ duration, delay, ease: EASE }}
      >
        {children}
      </motion.div>
    )
  }
  const useY = dir === "up" || dir === "down"
  const useX = dir === "left" || dir === "right"
  const fromY = dir === "down" ? y : -y
  const fromX = dir === "right" ? x : -x
  const initial: Record<string, number | string> = { opacity: 0 }
  if (useY) initial.y = fromY
  if (useX) initial.x = fromX
  if (scale !== 1) initial.scale = scale
  if (blur > 0) initial.filter = `blur(${blur}px)`
  const intoView: Record<string, number | string> = { opacity: 1, y: 0, x: 0, scale: 1 }
  if (blur > 0) intoView.filter = "blur(0px)"

  return (
    <motion.div
      className={className}
      initial={initial}
      whileInView={intoView}
      viewport={{ once, margin: "-60px" }}
      transition={{ duration, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  )
}

/**
 * Staggered reveal — wraps a list of children and staggers each child's reveal.
 * Useful for grids, lists, and any set of sibling elements.
 */
export function Stagger({
  children,
  className,
  stagger = 0.06,
  delay = 0,
  y = 24,
}: {
  children: ReactNode
  className?: string
  stagger?: number
  delay?: number
  y?: number
}) {
  const reduce = useReducedMotion()
  if (reduce) return <div className={className}>{children}</div>

  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-40px" }}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: stagger, delayChildren: delay } },
      }}
    >
      {Array.isArray(children)
        ? children.map((child, i) => (
            <motion.div
              key={i}
              variants={{
                hidden: { opacity: 0, y },
                visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
              }}
            >
              {child}
            </motion.div>
          ))
        : <motion.div
            variants={{
              hidden: { opacity: 0, y },
              visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
            }}
          >
            {children}
          </motion.div>
      }
    </motion.div>
  )
}
