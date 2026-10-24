import { useRef, useState, type ReactNode, type CSSProperties } from "react"
import { useReducedMotion } from "framer-motion"

/**
 * Adds a soft, pointer-following sheen that glides across a card surface on hover.
 * Calm and premium — a restrained highlight, not a neon glare.
 */
export function CardGlare({
  children,
  className = "",
  highlight = "rgba(255,255,255,0.10)",
}: {
  children: ReactNode
  className?: string
  highlight?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()
  const [pos, setPos] = useState<CSSProperties>()

  const onMove = (e: React.MouseEvent) => {
    if (reduce || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    const x = ((e.clientX - r.left) / r.width) * 100
    const y = ((e.clientY - r.top) / r.height) * 100
    setPos({ background: `radial-gradient(520px circle at ${x}% ${y}%, ${highlight}, transparent 42%)` })
  }

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={() => setPos(undefined)}
      className={`group/cg relative overflow-hidden ${className}`}
    >
      <div aria-hidden className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover/cg:opacity-100" style={{ ...pos, transition: "opacity 0.5s ease" }} />
      <div className="relative h-full">{children}</div>
    </div>
  )
}
