import type { ReactNode } from "react"
import { motion, useReducedMotion } from "framer-motion"
import { Reveal } from "./Reveal"

const EASE = [0.25, 1, 0.5, 1] as const

export function SectionHeader({
  index,
  kicker,
  children,
  sub,
  center = false,
}: {
  index?: string
  kicker: string
  children: ReactNode
  sub?: string
  center?: boolean
}) {
  const reduce = useReducedMotion()
  return (
    <Reveal className={center ? "text-center" : ""}>
      <div className={`flex items-center gap-3 ${center ? "justify-center" : ""}`}>
        {index && (
          <motion.span
            className="cosmic-text-xs font-medium text-[#86868b]"
            initial={reduce ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.05, ease: EASE }}
          >
            {index} /
          </motion.span>
        )}
        <span className="cosmic-text-xs font-medium uppercase tracking-normal text-[#8B7CF6]">
          {kicker}
        </span>
      </div>
      <span className="block overflow-hidden mt-1 pb-[0.14em] -mb-[0.14em]">
        <motion.h2
          className="mt-3 cosmic-text-4xl font-bold leading-[1.1] tracking-[-0.025em] text-[#f5f5f7] sm:cosmic-text-4xl lg:cosmic-text-5xl"
          initial={reduce ? false : { y: "105%" }}
          whileInView={{ y: "0%" }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, ease: EASE }}
        >
          {children}
        </motion.h2>
      </span>
      {sub && (
        <Reveal delay={0.12} y={12}>
          <p className={`mt-3 max-w-xl cosmic-text-base leading-relaxed text-[#a1a1aa] ${center ? "mx-auto text-center" : ""}`}>
            {sub}
          </p>
        </Reveal>
      )}
    </Reveal>
  )
}
