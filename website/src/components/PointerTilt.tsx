import { useEffect, useRef, type ReactNode } from "react"
import { motion, useReducedMotion } from "framer-motion"

export function PointerTilt({
  children,
  max = 5,
  delay = 0,
  className,
}: {
  children: ReactNode
  max?: number
  delay?: number
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()

  useEffect(() => {
    const el = ref.current
    if (!el || reduce) return
    const target = { x: 0, y: 0 }
    const current = { x: 0, y: 0 }
    let raf = 0
    let started = false
    let startTimer = 0

    const onMove = (e: MouseEvent) => {
      if (!started) return
      const r = el.getBoundingClientRect()
      const px = (e.clientX - r.left) / r.width - 0.5
      const py = (e.clientY - r.top) / r.height - 0.5
      target.x = py * -max
      target.y = px * max
    }
    const onLeave = () => {
      target.x = 0
      target.y = 0
    }
    const loop = () => {
      current.x += (target.x - current.x) * 0.1
      current.y += (target.y - current.y) * 0.1
      el.style.transform = `perspective(1100px) rotateX(${current.x.toFixed(2)}deg) rotateY(${current.y.toFixed(2)}deg)`
      raf = requestAnimationFrame(loop)
    }

    window.addEventListener("mousemove", onMove, { passive: true })
    el.addEventListener("mouseleave", onLeave)
    startTimer = window.setTimeout(() => {
      started = true
      raf = requestAnimationFrame(loop)
    }, delay)
    return () => {
      window.removeEventListener("mousemove", onMove)
      el.removeEventListener("mouseleave", onLeave)
      clearTimeout(startTimer)
      cancelAnimationFrame(raf)
    }
  }, [max, reduce, delay])

  return (
    <motion.div
      ref={ref}
      className={className}
      style={{
        transformStyle: "preserve-3d",
        willChange: "transform",
        transform: "perspective(1100px) rotateX(0deg) rotateY(0deg)",
      }}
    >
      {children}
    </motion.div>
  )
}
