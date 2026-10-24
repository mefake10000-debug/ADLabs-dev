import { useEffect, useRef } from "react"

/**
 * A lightweight, zero-dependency Canvas-2D particle field.
 * Drifts calm specks of light over a dark surface — restrained, premium,
 * brand-tinted. Auto-disabled for reduced-motion users and stops on resize.
 * Used as ambient cosmic ambience behind the Discovery manifest.
 */
export function ParticleField({
  count = 70,
  hue = "169,121,43",
  className,
}: {
  count?: number
  hue?: string
  className?: string
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      canvas.style.display = "none"
      return
    }
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let raf = 0
    let w = 0
    let h = 0

    type P = { x: number; y: number; r: number; vx: number; vy: number; tw: number; ph: number }
    let pts: P[] = []

    const init = () => {
      w = canvas.offsetWidth
      h = canvas.offsetHeight
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      pts = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 1.4 + 0.4,
        vx: (Math.random() - 0.5) * 0.22,
        vy: (Math.random() - 0.5) * 0.12 - 0.04,
        tw: Math.random() * Math.PI * 2,
        ph: Math.random() * 0.02 + 0.005,
      }))
    }

    const tick = () => {
      ctx.clearRect(0, 0, w, h)
      for (const p of pts) {
        p.x += p.vx
        p.y += p.vy
        p.tw += p.ph
        if (p.x < -8) p.x = w + 8
        if (p.x > w + 8) p.x = -8
        if (p.y < -8) p.y = h + 8
        if (p.y > h + 8) p.y = -8
        const a = 0.22 + (Math.sin(p.tw) + 1) * 0.28
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${hue},${a.toFixed(3)})`
        ctx.fill()
      }
      raf = requestAnimationFrame(tick)
    }

    init()
    raf = requestAnimationFrame(tick)
    const ro = new ResizeObserver(() => {
      init()
    })
    ro.observe(canvas)
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [count, hue])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={`pointer-events-none absolute inset-0 h-full w-full ${className ?? ""}`}
    />
  )
}
