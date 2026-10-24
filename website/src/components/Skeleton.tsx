export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-lg bg-[rgba(29,29,31,0.08)] ${className}`} />
}
