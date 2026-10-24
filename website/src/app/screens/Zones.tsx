import { TriangleAlert, Map } from "lucide-react"
import { Panel, Label, ScreenHeader } from "../ui"
import { HeatGrid, HBars } from "../charts"
import { ZONES } from "../../data/dashboard"

export function Zones() {
  const sorted = [...ZONES].sort((a, b) => b.traffic - a.traffic).slice(0, 6)
  const flagged = ZONES.filter((z) => z.flag)

  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader
        icon={Map}
        eyebrow="Store intelligence"
        title="Zones"
        sub="Traffic share per zone · hover any cell for dwell and notes. Red dot = flagged."
      />

      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Panel
          title="Floor heat · today"
          action={<Label>10 ZONES</Label>}
          info="Each cell = floor zone · colour = traffic share · red dot = flagged. Hover for dwell."
        >
          <HeatGrid zones={ZONES} />
          <div className="mt-4 flex items-center gap-3">
            <span className="font-inter cosmic-text-2xs text-[var(--app-faint)]">Cold</span>
            <div
              className="h-1.5 flex-1 rounded-full"
              style={{
                background:
                  "linear-gradient(to right, var(--app-card), color-mix(in srgb, var(--app-gold) 72%, var(--app-card)))",
              }}
            />
            <span className="font-inter cosmic-text-2xs text-[var(--app-faint)]">Hot</span>
          </div>
        </Panel>

        <div className="flex flex-col gap-5">
          <Panel
            title="Attention share"
            info="Traffic share per zone — where the footfall actually goes."
          >
            <HBars items={sorted.map((z) => ({ label: z.name, pct: z.traffic }))} />
          </Panel>

          {flagged.map((z) => (
            <Panel key={z.code} pad={false}>
              <div className="flex items-start gap-3 p-5">
                <span
                  className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full"
                  style={{ background: "color-mix(in srgb, var(--app-neg) 12%, transparent)", color: "var(--app-neg)" }}
                >
                  <TriangleAlert size={15} strokeWidth={2.3} />
                </span>
                <div>
                  <p className="font-inter cosmic-text-sm font-semibold text-[var(--app-text)]">
                    Zone {z.code} — {z.name}
                  </p>
                  <p className="mt-1 font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">{z.flag}</p>
                  <p className="mt-2 font-inter cosmic-text-xs text-[var(--app-faint)]">
                    Suggested move: relight at 18:00 and re-measure for 7 days.
                  </p>
                </div>
              </div>
            </Panel>
          ))}
        </div>
      </div>
    </div>
  )
}
