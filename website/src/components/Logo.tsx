export function Logo({ dark = true, className = "" }: { dark?: boolean; className?: string }) {
  const box = dark ? "#8B7CF6" : "#16161f"
  const ad = dark ? "#05050a" : "#ffffff"
  const wordA = dark ? "#f5f5f7" : "#16161f"
  const wordB = dark ? "#a1a1aa" : "#6e6e73"
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <span
        className="grid h-9 w-9 place-items-center rounded-xl font-inter font-extrabold transition-transform duration-200 hover:-translate-y-px"
        style={{ background: box, color: ad, fontSize: 15, letterSpacing: "-0.04em" }}
        aria-hidden
      >
        Ad
      </span>
      <span className="font-inter leading-none">
        <span className="block font-extrabold" style={{ color: wordA, fontSize: 16, letterSpacing: "-0.04em" }}>
          {`AD`}
        </span>
        <span className="block font-semibold" style={{ color: wordB, fontSize: 11, letterSpacing: "-0.02em" }}>
          Labs
        </span>
      </span>
    </span>
  )
}
