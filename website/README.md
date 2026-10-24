# AD Labs — Consumer Intelligence for Offline Retail

## Overview

Marketing website + analytics dashboard for **AD Labs** (Ad Labs Tech Pvt Ltd, founded 2026, Bengaluru). A single Next.js app serves four routes: the storefront landing page (`/`), an in-depth company page (`/about`), the marketing/discovery page (`/discover`), and the live analytics dashboard (`/dashboard`).

**Live URLs (when deployed):**
- Website: `https://adlabs.in`
- Dashboard: `https://adlabs.in/dashboard`

## Stack

- **Next.js 16** (App Router) + **React 19** + **TypeScript**
- **Tailwind CSS v4** (via `@tailwindcss/postcss`)
- **Framer Motion** (animations)
- **Lucide React** (icons)
- **oxlint** (linting)

## Project Structure

```
adlabs/
├── app/                           # Next.js App Router
│   ├── layout.tsx                 # Root layout: fonts, GlowCursor, metadata
│   └── page.tsx                   # Home → SitePage
│   ├── about/page.tsx             # /about → About
│   ├── dashboard/page.tsx         # /dashboard → DashboardPage
│   └── discover/page.tsx          # /discover → DiscoveryPage
├── public/
│   ├── images/                    # photography + product assets
│   └── favicon.svg                # Favicon
├── src/
│   ├── site/                      # Marketing website sections
│   │   ├── SitePage.tsx           # Composition root (01–14)
│   │   ├── Nav.tsx                # Sticky, blur, section tracking, mobile drawer
│   │   ├── Hero.tsx               # Full-bleed, telemetry badges, marquee
│   │   ├── BlindSpot.tsx          # 3-card problem framing (01)
│   │   ├── Journey.tsx            # Funnel bars + 5 step cards (02)
│   │   ├── Atelier.tsx            # Tabbed in-store view with overlays (03)
│   │   ├── System.tsx             # Trio + mini dashboard preview (04)
│   │   ├── Privacy.tsx            # Privacy architecture, DPDP charter (05)
│   │   ├── Proof.tsx              # A/B before/after with uplift (06)
│   │   ├── Metrics.tsx            # 12-signal grid (07)
│   │   ├── Sectors.tsx            # 4 sector cards (08)
│   │   ├── Mission.tsx            # Witness-not-spy ethos (09)
│   │   ├── Team.tsx               # Founder cards + operating principles (10)
│   │   ├── How.tsx                # 3 steps + wishlist form (11)
│   │   ├── Pricing.tsx            # Pilot terms + cohort bonuses (12)
│   │   ├── Faq.tsx                # Accordion FAQ (13)
│   │   ├── Contact.tsx            # Contact form (14)
│   │   ├── About.tsx              # /about content
│   │   ├── DiscoveryPage.tsx      # /discover content
│   │   ├── Footer.tsx             # Links, newsletter, socials, legal
│   │   └── PilotModal.tsx         # Full pilot request modal
│   ├── app/                       # Analytics dashboard
│   │   ├── DashboardPage.tsx      # Shell: sidebar, topbar, theme, present mode
│   │   ├── PresentMode.tsx        # Keyboard-nav slides, autoplay
│   │   ├── ui.tsx                 # Panel, Chip, DeltaPill, Segmented
│   │   ├── charts.tsx             # AreaChart, Sparkline, FunnelBars, HeatGrid
│   │   └── screens/               # Overview, Stores, Campaigns, Zones, Brief, Manager
│   ├── components/                # Shared UI primitives (Reveal, Section, FlipCard…)
│   ├── data/
│   │   ├── site.ts                # All website copy (swap point #1)
│   │   └── dashboard.ts           # Dashboard mock data (swap point #2)
│   ├── utils/
│   │   ├── mailto.ts              # mailto: form submission (no backend)
│   │   └── useMountLoader.ts      # Skeleton loading hook
│   └── index.css                  # Tailwind v4 + design tokens + keyframes
├── next.config.mjs
├── postcss.config.mjs
├── vercel.json
└── package.json
```

## Design System

### Website (Dark / Ink + Violet)
- Background: `#0a0a0b` (ink)
- Surface: `#18181c` / `#121214`
- Text: `#f5f5f7` · Sub: `#a1a1aa` · Faint: `#86868b`
- Accent: `#8B7CF6` (violet) · Hover: `#6E5CE6`
- Gold (positives): `#d4be8a` · Danger: `#ff3b30`
- Fonts: Inter (sans) / Fraunces (display headings)
- Radii: 12–24px · Motion: 280ms cubic-bezier(0.25, 1, 0.5, 1), `prefers-reduced-motion` safe

### Dashboard (Light/Dark Apple-neutrals)
Defined via `--app-*` tokens under `.app-scope[data-theme="light"/"dark"]` in `src/index.css`. Metric numerals use tabular figures.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start the Next.js dev server (port 3000) |
| `npm run build` | Type-check + production build |
| `npm run start` | Serve the production build |
| `npm run lint` | Run oxlint |

## Data Contracts (Swap Points)

All copy and numbers are centralized for instant swapping:

| File | Purpose |
|------|---------|
| `src/data/site.ts` | Website copy, nav groups, founders, form fields, pricing, FAQ |
| `src/data/dashboard.ts` | Dashboard KPIs, funnel, traffic hours, stores, zones, campaigns, briefs |

Section indices (01–14) and navigation anchor ids (`#blindspot`, `#journey`, …) are driven from `src/data/site.ts` — keep them in sync when reordering sections.

## Deployment (Vercel)

```bash
npm run build
vercel --prod
```

- Framework preset: **Next.js** (auto-detected; no `rewrites` needed)
- Custom domain: `adlabs.in` (add in Vercel dashboard after first deploy)
- `deploy.sh` / `autodeploy.sh` contain one-command / watch-mode deploy helpers

## Demo Data Coherence

All numbers share a single universe:

- **Tenant:** Organic Clothing Co. · Bandra Flagship · Mumbai
- **Today footfall:** 2,481 | Stop rate: 7.5% | Walk-ins: 39
- **Week stop rate:** 11.4% (peer 8.9%)
- **A/B test (14 days):** Capture 6.4% → 7.3% (+14.6% uplift)
- **Zones:** Leather Goods Island 68% traffic, Vitrine West under-lit

All numbers are **simulated** — no real client data.

## Accessibility

- Contrast AA throughout
- Focus-visible violet rings
- `prefers-reduced-motion` respected
- ARIA labels on tabs, dialogs, forms
- Keyboard navigation throughout

## Future Swap Checklist

- [ ] Replace `sales@adlabs.in` with real email
- [ ] Fill `SOCIALS.linkedin` / `SOCIALS.instagram` URLs
- [ ] Replace demo tenant name + imagery
- [ ] Swap mock KPIs/funnel with real API endpoints
- [ ] Attach `adlabs.in` domain in Vercel
- [ ] Add analytics (Plausible/GA) if desired
# AD Labs Website and Dashboard

This repository contains the independent Next.js marketing site and dashboard. It does not import EdgeSight Python model code or load model weights. Product/marketing content lives in `src/site/`; dashboard screens/components live in `src/app/`; the Next.js App Router is the repository-root `app/` folder.

The dashboard’s current analytics are a preview marked **Demo**. The Edge processing panel reports local worker state and camera freshness separately. It does not turn sample charts into live metrics.

Local processing control is documented in [`docs/dashboard-processing-control.md`](docs/dashboard-processing-control.md). It works only with `npm run dev` on the same computer as EdgeSight, a loopback `EDGESIGHT_API_URL`, and server-only `EDGESIGHT_API_KEY`. Hosted production/Vercel pages cannot control a remote store edge machine.

Checks: `npm test`, `npm run lint`, and `npm run build`.

## EdgeSight API boundary and controls

The Next.js App Router is the repository-root `app/` directory. `app/api/processing/` forwards fixed Start/Stop/status requests to EdgeSight v1 only during local development and only to a loopback EdgeSight URL. It does not execute commands or control Docker. A hosted Vercel site cannot reach the store's localhost.

The `/api/v1/telemetry/` routes accept aggregate telemetry only and require `EDGE_INGEST_KEY`; the live read route requires `DATABASE_URL`. The database integration currently has no user identity or tenant/store authorization. Do not expose client data or call this a production multi-tenant service. Missing measurements stay null; sample dashboard data remains explicitly labeled.

Run with `npm ci && npm run dev`. This starts the website only; it does not open video or load models.
