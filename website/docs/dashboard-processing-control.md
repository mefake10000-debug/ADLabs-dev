# Dashboard processing control

The dashboard retains its existing analytics preview and marks it as **Demo**. Fixture-backed figures, campaign examples, portfolio comparisons, demographic charts, staffing suggestions, alerts, and assistant answers are sample content; sample labels do not claim those values came from footage or a connected POS system. A separate Edge processing panel allows a local operator to select configured cameras, start/stop processing, refresh state, and see whether recent frames reached the worker. It does not copy live worker numbers into the demo charts.

The website repository is independent from EdgeSight and talks to it only through the versioned HTTP API. The Next.js App Router is rooted at `app/`; routes are under `app/api/processing/`, while `src/app/` holds React dashboard screens/components.

Set server-only `EDGESIGHT_API_URL=http://127.0.0.1:8000` and `EDGESIGHT_API_KEY` in the local website `.env.local`, then run `npm run dev`. The API key is not prefixed with `NEXT_PUBLIC_`, serialized to the browser, or committed. Controls are disabled outside local development. A hosted Vercel/production site cannot reach the store computer’s loopback service and cannot start its edge worker.

This is a local single-operator control path, not user login or tenant authorization. Existing dashboard business figures remain samples; no analytics-to-live integration is claimed here.

The website App Router lives at `app/`, not `src/app/`: its local-only control handlers are in `app/api/processing/{cameras,start,status,stop}/route.ts`. The React screens in `src/app/` are presentation only. Starting a local session changes the EdgeSight runtime state panel; it does not update the sample analytics sections. A hosted Vercel dashboard cannot reach the store computer's loopback service and these routes do not remotely start an edge machine.
