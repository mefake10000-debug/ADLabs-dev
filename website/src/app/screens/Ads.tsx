import { ArrowRight, BadgeCheck, Megaphone, MapPin, Wallet } from "lucide-react"
import { Panel, Label, Chip, InfoTip, ScreenHeader } from "../ui"
import { ADS, AD_FLOW, SIMULATED_NOTE, PEER_NOTE } from "../../data/dashboard"

export function Ads() {
  return (
    <div className="flex flex-col gap-5">
      <ScreenHeader
        icon={Megaphone}
        eyebrow="Attribution · offline → on-floor"
        title="Ads"
        sub="Did they see the ad — and did it convert? Each campaign below tracks the same journey: sighting on the street, entrance at the door, first zone reached, and the product they engaged."
      >
        <div className="flex flex-col items-end gap-2">
          <Chip tone="gold">{SIMULATED_NOTE}</Chip>
          <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">{PEER_NOTE}</span>
        </div>
      </ScreenHeader>

      {/* River: saw → entered → zone → converted */}
      <Panel
        pad={false}
        verified="Sample attribution · no live link"
        info="Statistical match between pedestrians on the ad's sightline and store entries — anonymous counts, never individuals."
      >
        <div className="border-b border-[var(--app-line)] p-6 sm:p-7">
          <div className="flex flex-wrap items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-2xl" style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>
              <Megaphone size={18} strokeWidth={1.9} />
            </span>
            <div>
              <p className="card-title text-[var(--app-text)]">The ad → store journey</p>
              <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">
                Four steps the system measures for every campaign. The photos are anonymised previews.
              </p>
            </div>
          </div>
        </div>
        <div className="grid gap-4 p-6 sm:grid-cols-4 sm:p-7">
          {AD_FLOW.steps.map((s, i) => (
            <div key={s.key} className="relative">
              <figure className="overflow-hidden rounded-2xl border border-[var(--app-line-strong)]">
                <img src={s.image} alt={s.title} loading="lazy" className="aspect-[4/3] w-full object-cover" />
                <figcaption className="p-3.5">
                  <div className="flex items-center justify-between">
                    <Label>{s.title}</Label>
                    <span className="font-mono cosmic-text-xs font-bold text-[var(--app-gold)]">0{i + 1}</span>
                  </div>
                  <p className="mt-2 font-inter cosmic-text-xl font-bold font-num leading-none text-[var(--app-text)]">{s.value}</p>
                  <p className="mt-1.5 font-inter cosmic-text-xs leading-relaxed text-[var(--app-faint)]">{s.desc}</p>
                </figcaption>
              </figure>
              {i < AD_FLOW.steps.length - 1 && (
                <ArrowRight size={15} className="absolute -right-2.5 top-1/2 z-10 -translate-y-1/2 rounded-full border border-[var(--app-line)] bg-[var(--app-card)] p-0.5 text-[var(--app-faint)]" />
              )}
            </div>
          ))}
        </div>
      </Panel>

      {/* Campaign cards */}
      <div className="grid gap-5 xl:grid-cols-3">
        {ADS.map((ad) => {
          const best = ad.redirect.reduce((a, b) => (b.pct > a.pct ? b : a))
          return (
            <Panel key={ad.id} title={ad.name} action={<Chip tone="gold">{ad.channel}</Chip>} verified="Example · not attributed live">
              <div className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl" style={{ background: "var(--app-raise)", color: "var(--app-gold)" }}>
                  <MapPin size={16} strokeWidth={2} />
                </span>
                <div className="min-w-0">
                  <p className="font-inter cosmic-text-xs text-[var(--app-sub)]">{ad.placement}</p>
                  <p className="font-inter cosmic-text-xs text-[var(--app-faint)]">{ad.week} · spend {ad.spend}</p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2.5">
                <div className="rounded-xl border border-[var(--app-line)] p-3">
                  <Label>Impressions</Label>
                  <p className="kpi-value mt-1 !cosmic-text-xl text-[var(--app-text)]">{ad.impressions.toLocaleString("en-US")}</p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] p-3">
                  <Label>Attributed walk-ins</Label>
                  <p className="kpi-value mt-1 !cosmic-text-xl text-[var(--app-text)]">{ad.attributedWalkins} <span className="font-inter cosmic-text-xs font-semibold font-num text-[var(--app-faint)]">({ad.attributedRate})</span></p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] p-3">
                  <Label>Convert rate</Label>
                  <p className="kpi-value mt-1 !cosmic-text-xl" style={{ color: "var(--app-pos)" }}>{ad.convertRate}</p>
                </div>
                <div className="rounded-xl border border-[var(--app-line)] p-3">
                  <Label>Uplift</Label>
                  <p className="kpi-value mt-1 !cosmic-text-xl" style={{ color: "var(--app-pos)" }}>{ad.uplift.split(" ")[0]}</p>
                </div>
              </div>

              <div className="mt-4">
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-inter cosmic-text-xs font-semibold text-[var(--app-text)]">Where they went first</p>
                  <span className="inline-flex items-center gap-1 font-inter cosmic-text-2xs font-semibold text-[var(--app-gold)]">
                    <BadgeCheck size={11} strokeWidth={2.6} /> {best.zone} · {best.pct}%
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  {ad.redirect.map((z) => (
                    <div key={z.zone} className="flex items-center gap-2">
                      <span className="w-8 font-mono cosmic-text-2xs font-bold text-[var(--app-faint)]">{z.zone}</span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: "var(--app-grid)" }}>
                        <div className="h-full rounded-full" style={{ width: `${z.pct}%`, background: z.pct === best.pct ? "var(--app-gold)" : "color-mix(in srgb, var(--app-gold) 45%, var(--app-card))" }} />
                      </div>
                      <span className="w-9 text-right font-mono cosmic-text-2xs font-semibold font-num text-[var(--app-sub)]">{z.pct}%</span>
                    </div>
                  ))}
                </div>
              </div>

              <p className="mt-3.5 flex items-start gap-2 border-t border-[var(--app-line)] pt-3 font-inter cosmic-text-2xs leading-relaxed text-[var(--app-faint)]">
                <Wallet size={11} className="mt-0.5 shrink-0 text-[var(--app-gold)]" />
                {ad.uplift} · cost per attributed walk-in ≈ ${Math.round((parseInt(ad.spend.replace(/[^0-9]/g, "")) ) / ad.attributedWalkins)}
              </p>
            </Panel>
          )
        })}
      </div>

      <Panel
        title="How to read attribution"
        action={<Label>n = 3 campaigns</Label>}
        info="Attributed walk-in = store entry linked to an ad sightline within 30 minutes. Never a track on a person."
      >
        <ol className="flex flex-col gap-2.5">
          {[
            "Impressions = people past the ad placement — counted like footfall, not like a DV pixel.",
            "Attributed walk-ins = entries inside the flight window, matched anonymously by time + direction patterns.",
            "Convert rate = attributed visitors who reached a high-intent product touch (engage stage).",
            "Zone redirect = the first zone they entered — this is the ad's real spatial intelligence.",
          ].map((t, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full font-inter cosmic-text-2xs font-bold" style={{ background: "var(--app-gold-soft)", color: "var(--app-gold)" }}>{i + 1}</span>
              <p className="font-inter cosmic-text-xs leading-relaxed text-[var(--app-sub)]">{t}</p>
            </li>
          ))}
        </ol>
      </Panel>
    </div>
  )
}

export function AdInfoTip() {
  return <InfoTip text="Attribution windows: 30 min after ad sighting. Same-day only — no cross-day matching." />
}
