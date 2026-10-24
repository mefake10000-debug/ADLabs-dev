import { useCallback } from "react"
import { Download, FileSpreadsheet } from "lucide-react"

/**
 * ReportButton — downloads CSV (or a plain-text report) client-side.
 * Glitch-free: no network, just a Blob + anchor click.
 */
export function ReportButton({
  label = "Export",
  filename,
  cols,
  /// Build rows as array of arrays (already strings/numbers) matching cols.
  build,
  text,
}: {
  label?: string
  filename: string
  cols: string[]
  build: () => string[][]
  text?: string
}) {
  const run = useCallback(() => {
    const header = cols.join(",")
    const rows = build().map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
    let data = header + "\n" + rows.join("\n")
    if (text) data = text + "\n\n" + data
    const blob = new Blob([data], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [filename, cols, build, text])

  return (
    <button
      onClick={run}
      className="group inline-flex items-center gap-2 rounded-full px-3.5 py-2 font-inter cosmic-text-xs font-semibold text-[var(--app-sub)] transition-colors hover:text-[var(--app-text)]"
      style={{ border: "1px solid var(--app-line)", background: "var(--app-card)" }}
    >
      <FileSpreadsheet size={14} strokeWidth={2.1} style={{ color: "var(--app-gold)" }} />
      {label}
      <Download size={13} strokeWidth={2.1} className="transition-transform group-hover:-translate-y-0.5" />
    </button>
  )
}
