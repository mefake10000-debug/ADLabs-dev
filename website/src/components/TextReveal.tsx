import { motion, useReducedMotion } from "framer-motion"

const EASE = [0.16, 1, 0.3, 1] as const

type Segment = { text: string; className?: string }

const spaced = (text: string) => text.split(" ")

/**
 * Cinematic word-by-word reveal. Preserves the surrounding font/type styling
 * by letting `segments` carry per-fragment classNames (e.g. an <em> accent),
 * while the wrapper `className` holds the shared headline font + line-height.
 */
export function TextReveal({
  text,
  segments,
  as = "span",
  className,
  delay = 0,
  stagger = 0.045,
  once = true,
}: {
  text?: string
  segments?: Segment[]
  as?: "span" | "h1" | "h2" | "h3" | "p"
  className?: string
  delay?: number
  stagger?: number
  once?: boolean
}) {
  const reduce = useReducedMotion()

  if (reduce) {
    return <span className={className}>{segments ? segments.map((s, i) => <span key={i} className={s.className}>{s.text} </span>) : text}</span>
  }

  // Flatten into word runs, each retaining its segment's className.
  const runs: { word: string; className?: string }[] = []
  if (segments) {
    for (const s of segments) {
      for (const w of spaced(s.text)) runs.push({ word: w, className: s.className })
    }
  } else if (text) {
    for (const w of spaced(text)) runs.push({ word: w })
  }

  const Tag = as as "span"
  const ariaLabel = segments ? segments.map((s) => s.text).join(" ") : text
  return (
    <Tag className={className} aria-label={ariaLabel}>
      <span className="inline-flex flex-wrap" aria-hidden>
        {runs.map((r, i) => (
          <span key={i} className="inline-flex overflow-hidden align-baseline">
            <motion.span
              className={`inline-block will-change-transform ${r.className ?? ""}`}
              initial={{ y: "115%" }}
              whileInView={{ y: "0%" }}
              viewport={{ once, margin: "-40px" }}
              transition={{ duration: 0.7, delay: delay + i * stagger, ease: EASE }}
            >
              {r.word}
            </motion.span>
            {i < runs.length - 1 ? "\u00A0" : ""}
          </span>
        ))}
      </span>
    </Tag>
  )
}
