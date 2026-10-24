import { Users } from "lucide-react"
import { Panel, Label, ScreenHeader, Chip } from "../ui"
import { DonutChart, HBars } from "../charts"
import { DEMOGRAPHICS, SIMULATED_NOTE, PEER_NOTE } from "../../data/dashboard"

export function Demographics() {
  const g = DEMOGRAPHICS
  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader
        icon={Users}
        eyebrow="Consumer intelligence"
        title="Demographics"
        sub="Sample visitor-composition charts for preview only; no camera-derived demographic results are connected."
      >
        <Chip tone="gold" title={SIMULATED_NOTE}>Sample data</Chip>
      </ScreenHeader>

      <div className="grid gap-5 xl:grid-cols-3">
        <Panel
          title="Gender split"
          action={<Label>today</Label>}
          info="Illustrative chart only. No gender inference is being performed by this preview."
        >
          <DonutChart
            data={[
              { label: "Female", pct: g.gender.female },
              { label: "Male", pct: g.gender.male },
            ]}
            size={160}
          />
          <p className="mt-4 font-inter cosmic-text-xs text-[var(--app-faint)]">
            Example narrative only — not a finding about current visitors.
          </p>
        </Panel>

        <Panel
          title="Individual vs group"
          info="Solo shoppers browse deep · groups decide faster at the product."
        >
          <DonutChart
            data={[
              { label: "Individual", pct: g.party.individual },
              { label: "Group", pct: g.party.group },
            ]}
            size={160}
          />
          <p className="mt-4 font-inter cosmic-text-xs text-[var(--app-faint)]">
            Groups convert higher at the fitting room · peak attention {g.peak}
          </p>
        </Panel>

        <Panel
          title="Group composition"
          info="Solo browsers browse deep · pairs discuss at the product."
        >
          <DonutChart
            data={[
              { label: "Solo", pct: g.dynamics.solo },
              { label: "Pair", pct: g.dynamics.pair },
            ]}
            size={160}
          />
          <p className="mt-4 font-inter cosmic-text-xs text-[var(--app-faint)]">Peak attention window: {g.peak}</p>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_1.4fr]">
        <Panel
          title="Age bands"
          action={<Label>18–60+</Label>}
          info="Aggregated age cohorts — the 28–44 band owns most attention."
        >
          <HBars items={g.ages.map((a) => ({ label: a.band, pct: a.pct }))} />
          <p className="mt-4 font-inter cosmic-text-2xs text-[var(--app-faint)]">{g.note}</p>
        </Panel>

        <Panel
          title="Day-hour attention heatmap"
          info="Day × hour attention. Darker gold = higher intensity."
        >
          <p className="mb-3 font-inter cosmic-text-xs text-[var(--app-faint)]">Attention intensity across days and hours · darker cells indicate higher engagement.</p>
          <div className="overflow-x-auto">
            <svg viewBox="0 0 660 200" className="h-auto w-full min-w-[500px]" role="img" aria-label="Day-hour heatmap">
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, i) => (
                <text key={d} x={44} y={12 + i * 26} textAnchor="end" fontSize={10} fill="var(--app-faint)" className="font-inter">{d}</text>
              ))}
              {["09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"].map((hr, i) => (
                <text key={hr} x={60 + i * 50} y={195} textAnchor="middle" fontSize={9} fill="var(--app-faint)" className="font-mono">{hr}</text>
              ))}
              {[
                [20, 25, 35, 48, 62, 78, 92, 95, 88, 65, 40, 22],
                [18, 22, 32, 45, 58, 75, 90, 93, 85, 62, 38, 20],
                [22, 28, 38, 52, 65, 82, 95, 96, 90, 68, 42, 24],
                [19, 24, 34, 46, 60, 76, 88, 90, 82, 60, 36, 18],
                [21, 27, 36, 50, 64, 80, 93, 94, 86, 64, 40, 22],
                [25, 30, 40, 55, 70, 85, 96, 97, 92, 70, 45, 28],
                [28, 34, 44, 58, 72, 88, 97, 98, 94, 72, 48, 30],
              ].map((row, di) => (
                <g key={di}>
                  {row.map((val, hi) => {
                    const t = (val - 18) / (98 - 18)
                    const color = t < 0.25 ? `rgba(169, 121, 43, ${0.08 + t * 0.3})` : t < 0.5 ? `rgba(169, 121, 43, ${0.3 + (t - 0.25) * 0.4})` : t < 0.75 ? `rgba(169, 121, 43, ${0.6 + (t - 0.5) * 0.2})` : `rgba(169, 121, 43, ${0.8 + (t - 0.75) * 0.2})`
                    return (
                      <rect key={`${di}-${hi}`} x={60 + hi * 50} y={12 + di * 26} width={48} height={24} rx={3} fill={color} stroke="var(--app-card)" strokeWidth={1} />
                    )
                  })}
                </g>
              ))}
            </svg>
          </div>
          <p className="mt-3 font-inter cosmic-text-2xs text-[var(--app-faint)]">Weekend afternoons strongest · east entrance peaks earliest.</p>
        </Panel>
      </div>

      <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{SIMULATED_NOTE} · {PEER_NOTE}</p>
    </div>
  )
}
