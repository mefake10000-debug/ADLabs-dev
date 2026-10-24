import { useEffect, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"

/**
 * Cycles through a set of words with a smooth morphing swap — used for the
 * Manifesto's shifting pain-point sentence. Calm and restrained.
 */
export function MorphingText({
  words,
  intervalMs = 2200,
  className,
}: {
  words: string[]
  intervalMs?: number
  className?: string
}) {
  const reduce = useReducedMotion()
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (words.length <= 1 || reduce) return
    const t = window.setInterval(() => setIndex((i) => (i + 1) % words.length), intervalMs)
    return () => window.clearInterval(t)
  }, [words.length, intervalMs, reduce])

  return (
    <span className={className}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={words[index]}
          initial={reduce ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduce ? undefined : { opacity: 0, y: -14 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="inline-block"
        >
          {words[index]}
        </motion.span>
      </AnimatePresence>
    </span>
  )
}
