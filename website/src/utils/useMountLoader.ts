import { useEffect, useState } from "react"

export function useMountLoader(initialMs = 620) {
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    const t = window.setTimeout(() => setLoading(false), initialMs)
    return () => window.clearTimeout(t)
  }, [initialMs])
  return loading
}
