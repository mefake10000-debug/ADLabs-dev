import { HARDWARE, MODEL_SUITE, ARCHITECTURE_TIERS } from "../data/instrument"

export function HardwareSpecs() {
  const h = HARDWARE
  return (
    <div className="flex h-full flex-col rounded-2xl border border-[rgba(29,29,31,0.1)] bg-[#fffdfa]/90 p-6">
      <span className="font-mono cosmic-text-2xs tracking-[0.18em] text-[#8B7CF6]">TECHNICAL INSTRUMENT</span>
      <h4 className="mt-2 font-serif cosmic-text-xl leading-tight text-[#121212]">{h.title}</h4>
      <p className="mt-2 body-sm text-[#16161f]/62">{h.sub}</p>

      <div className="mt-4 rounded-xl border border-[rgba(29,29,31,0.08)] bg-[#121212] p-4">
        <div className="flex items-center justify-between">
          <span className="font-mono cosmic-text-xs font-bold text-[#d4ad5e]">EDGE DEVICE</span>
          <span className="font-mono cosmic-text-2xs text-[#e8e6df]/50">{h.cost}</span>
        </div>
        <p className="mt-1 font-serif cosmic-text-base text-[#FAF8F5]">{h.device}</p>
        <p className="mt-1 font-mono cosmic-text-xs text-[#8B7CF6]">{h.compute}</p>
      </div>

      <dl className="mt-4 flex-1 space-y-2.5">
        {h.specs.map((s) => (
          <div key={s.label} className="flex items-start justify-between gap-4 border-b border-[rgba(29,29,31,0.06)] pb-2.5 last:border-0">
            <dt className="w-24 shrink-0 font-mono cosmic-text-2xs tracking-[0.12em] text-[#16161f]/45">{s.label}</dt>
            <dd className="flex-1 text-right">
              <p className="cosmic-text-sm font-semibold text-[#121212]">{s.value}</p>
              {s.note && <p className="font-mono cosmic-text-2xs text-[#16161f]/45">{s.note}</p>}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export function ModelSuite() {
  const m = MODEL_SUITE
  return (
    <div className="flex h-full flex-col rounded-2xl border border-[rgba(29,29,31,0.1)] bg-[#fffdfa]/90 p-6">
      <span className="font-mono cosmic-text-2xs tracking-[0.18em] text-[#8B7CF6]">CV / ML MODEL SUITE</span>
      <h4 className="mt-2 font-serif cosmic-text-xl leading-tight text-[#121212]">{m.title}</h4>
      <p className="mt-2 body-sm text-[#16161f]/62">{m.sub}</p>

      <div className="mt-4 flex-1 overflow-hidden rounded-xl border border-[rgba(29,29,31,0.08)]">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-[rgba(29,29,31,0.08)] bg-[#faf6ee]">
              {["TASK", "MODEL", "STATUS", "NOTE"].map((th) => (
                <th key={th} className="px-3 py-2 font-mono cosmic-text-2xs tracking-[0.14em] text-[#16161f]/45">{th}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {m.rows.map((r) => (
              <tr key={r.task} className="border-b border-[rgba(29,29,31,0.05)] last:border-0">
                <td className="px-3 py-2 cosmic-text-xs font-semibold text-[#121212]">{r.task}</td>
                <td className="px-3 py-2 font-mono cosmic-text-xs text-[#8B7CF6]">{r.model}</td>
                <td className="px-3 py-2 font-mono cosmic-text-2xs text-[#16161f]/55">{r.status}</td>
                <td className="hidden px-3 py-2 cosmic-text-xs text-[#16161f]/55 md:table-cell">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function ArchitectureTiers() {
  const a = ARCHITECTURE_TIERS
  return (
    <div className="flex h-full flex-col rounded-2xl border border-[rgba(29,29,31,0.1)] bg-[#fffdfa]/90 p-6">
      <span className="font-mono cosmic-text-2xs tracking-[0.18em] text-[#8B7CF6]">DATA ARCHITECTURE</span>
      <h4 className="mt-2 font-serif cosmic-text-xl leading-tight text-[#121212]">{a.title}</h4>
      <p className="mt-2 body-sm text-[#16161f]/62">{a.sub}</p>

      <div className="mt-4 flex-1 space-y-2">
        {a.tiers.map((t, i) => (
          <div key={t.tier} className="flex items-center gap-3 rounded-lg border border-[rgba(29,29,31,0.07)] bg-[#faf6ee] px-3 py-2.5">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#121212] font-mono cosmic-text-2xs font-bold text-[#d4ad5e]">
              {i + 1}
            </span>
            <div className="flex-1">
              <p className="cosmic-text-sm font-semibold text-[#121212]">{t.name}</p>
              <p className="font-mono cosmic-text-2xs text-[#16161f]/45">{t.desc}</p>
            </div>
            <span className="hidden font-mono cosmic-text-2xs tracking-[0.1em] text-[#8B7CF6] sm:block">{t.sample}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
