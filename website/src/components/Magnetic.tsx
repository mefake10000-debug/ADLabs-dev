import { useRef, type ReactNode } from "react"
import { useReducedMotion } from "framer-motion"

export function Magnetic({
  children,
  strength = 0.35,
  className,
}: {
  children: ReactNode
  strength?: number
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()

  const onMove = (e: React.MouseEvent) => {
    if (reduce || !ref.current) return
    const el = ref.current
    const r = el.getBoundingClientRect()
    const dx = e.clientX - (r.left + r.width / 2)
    const dy = e.clientY - (r.top + r.height / 2)
    el.style.transform = `translate(${dx * strength}px, ${dy * strength}px)`
  }
  const onLeave = () => {
    if (ref.current) ref.current.style.transform = "translate(0px, 0px)"
  }

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className={className}
      style={{ willChange: "transform", transition: "transform 0.35s cubic-bezier(0.22,1,0.36,1)" }}
    >
      {children}
    </div>
  )
}
