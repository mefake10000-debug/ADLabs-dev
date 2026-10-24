# AD Labs — SWAP LIST (Single-Source Data Contracts)

## Quick Reference

Every user-facing string and number lives in **two files**. Edit these — no component surgery needed.

---

## 1. `src/data/site.ts` — Marketing Website

| Export | What to Swap |
|--------|--------------|
| `BRAND` | Legal name, email, domain, city, founded year, tagline |
| `SOCIALS` | `linkedin`, `instagram` URLs (currently empty strings) |
| `FOUNDERS` | Names, roles, bios, LinkedIn URLs, initials |
| `NAV` | Section labels + anchor hrefs |
| `HERO` | Headline, sub, CTAs, badge text, ticker values, live counters, marquee lines, footline |
| `BLINDSPOT` | 3 cards: tags, titles, metrics, descriptions, images |
| `JOURNEY` | Funnel bars, 5 step cards (counts, rates, descriptions, metrics), band tags |
| `ATELIER` | 4 tabs (overlays, pins), 4 feature cards, main image |
| `PROOF` | Store name, before/after values + images, uplift text |
| `SYSTEM` | Trio cards, interface card (store name, stats, trend, hours, CTA) |
| `METRICS` | 12 metric cards (title + desc) |
| `SECTORS` | 4 cards (title, sub, tag, images) |
| `PRIVACY` | 3 principles, 3 pipeline stages |
| `HOW` | 3 steps, wishlist form fields, success copy, feedback text |
| `PILOT_FORM` | Modal form fields, options, success copy, note |

**Images referenced (in `public/images/`):**
- `hero-storefront.*`, `blindspot-pass.jpg`, `blindspot-stop.jpg`, `blindspot-enter.jpg`
- `in-store-zones.jpg`, `window-before.jpg`, `window-after.jpg`, `mission-street.jpg`
- `sector-fashion.jpg`, `sector-beauty.jpg`, `sector-jewellery.jpg`, `sector-premium-retail.jpg`

---

## 2. `src/data/dashboard.ts` — Analytics Dashboard

| Export | What to Swap |
|--------|--------------|
| `TENANT` | Tenant name + store name (used in sidebar/topbar) |
| `PERIODS` | Period labels (Today / This week / 30 days / Baseline → Wk 12) |
| `KPIS.today` / `KPIS.week` | 5 KPI cards: label, value, delta, tone, note, peer, hint |
| `FUNNEL.today` / `FUNNEL.week` | 5-stage funnel (stage, value, rate, label) |
| `TRAFFIC_HOURS` | 13 hourly points `{h, v}` for area chart |
| `PEAK_WINDOWS` | Peak window labels + notes |
| `STORES` | Store list: name, city, grade, footfall, stopRate, trend, sparkline data, flag |
| `ZONES` | 10 zones: code, name, traffic%, dwell, heat (0-1), note, flag |
| `DEMOGRAPHICS` | Age bands, solo/pair split, peak window, note |
| `CAMPAIGNS` | 2 campaigns: before/after values, images, window, uplift, verified |
| `CAMPAIGN_TIMELINE` | 12 weekly stop-rate points + event markers |
| `CAMPAIGN_VERDICT` | Engine-generated verdict paragraph |
| `BRIEF` | Week label, title, verdict, 3 actions (title/why/priority/tag), benchmark, evidence images |
| `MANAGER` | Store/date, alert, staffing windows, checklist items |
| `WINDOW_ENGAGEMENT` | 3 engagement bars (label, pct) |
| `PEER_NOTE` | Benchmark footnote text |
| `SIMULATED_NOTE` | "Simulated showcase data" chip text |

---

## 3. Image Assets (Drop-in Replace)

| Path | Used In | Spec |
|------|---------|------|
| `/images/hero-storefront.jpg` | Hero, Atelier cam, Brief evidence | 1376×768, hero |
| `/images/in-store-zones.jpg` | Atelier, Campaign after, Brief evidence | 1376×768 |
| `/images/window-before.jpg` | Proof before, Campaign before, Brief evidence | 1376×768 |
| `/images/window-after.jpg` | Proof after, Campaign after, Brief evidence | 1376×768 |
| `/images/blindspot-pass.jpg` | BlindSpot card 1 | 1376×768 |
| `/images/blindspot-stop.jpg` | BlindSpot card 2 | 1376×768 |
| `/images/blindspot-enter.jpg` | BlindSpot card 3 | 1376×768 |
| `/images/sector-fashion.jpg` | Sectors card 1 | 1376×768 |
| `/images/sector-beauty.jpg` | Sectors card 2 | 1376×768 |
| `/images/sector-jewellery.jpg` | Sectors card 3 | 1376×768 |
| `/images/sector-premium-retail.jpg` | Sectors card 4 | 1376×768 |

**Swap rule:** Replace file in `public/images/` with same filename + aspect ratio. No code changes.

---

## 4. Config Constants (Single File)

| File | Constant | Current | Purpose |
|------|----------|---------|---------|
| `site.ts` | `BRAND.email` | `sales@adlabs.in` | All form submissions, footer |
| `site.ts` | `BRAND.domain` | `adlabs.in` | Canonical URL, OG meta |
| `site.ts` | `BRAND.city` | `Bengaluru, India` | Footer, Team |
| `site.ts` | `BRAND.founded` | `2026` | Footer, Team |
| `site.ts` | `SOCIALS.linkedin` | `""` | Footer, Team links |
| `site.ts` | `SOCIALS.instagram` | `""` | Footer |
| `dashboard.ts` | `SIMULATED_NOTE` | `"Simulated showcase data"` | Dashboard demo chip |

---

## 4. One-Command Swaps

```bash
# Replace all mock emails
sed -i 's/sales@adlabs.in/real@adlabs.in/g' src/data/site.ts

# Replace demo tenant name
sed -i 's/Maison Étoile/MyBrand/g' src/data/dashboard.ts

# Replace demo store name
sed -i 's/Madison Avenue Flagship/Flagship Store/g' src/data/dashboard.ts

# Toggle pricing visibility (site)
# Edit HOW.wishlist.h2 / HOW.wishlist.sub in site.ts
```

---

## 5. Deployment Checklist

- [ ] `BRAND.email` → real sales email
- [ ] `SOCIALS.linkedin` / `SOCIALS.instagram` → real URLs
- [ ] `FOUNDERS[].linkedin` → real profiles
- [ ] `public/images/` → real photography (same filenames)
- [ ] `src/data/dashboard.ts` → real KPIs/funnel from API
- [ ] Vercel: add `adlabs.in` custom domain
- [ ] Vercel: set `NODE_ENV=production`
- [ ] Test `/dashboard` present mode (P key, arrows, Esc)

---

## 6. TypeScript Types (for API Integration)

When swapping mock → real API, the types are already defined in `dashboard.ts`:

```typescript
interface Kpi { id, label, value, delta, deltaTone, deltaNote, peer?, hint }
interface Store { id, name, city, grade, footfallToday, stopRate, trend, spark, flag? }
interface Zone { code, name, traffic, dwell, heat, note?, flag? }
interface Campaign { id, name, week, type, metricLabel, before, after, window, verified, uplift, imageBefore, imageAfter }
```

Extend `fetch` calls in screens to populate these interfaces.
