# On-Demand Dashboard Control Implementation Plan

> This is the planning record, not the status source of truth. Current implementation and verification are in [`docs/dashboard-processing-control.md`](../../dashboard-processing-control.md); the full cross-repository handoff is maintained in the EdgeSight worktree at `docs/handoff/foundation-audit.md`. Do not interpret unchecked planning boxes as current status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add clear local Start/Stop/status controls to the existing dashboard without presenting sample dashboard metrics as live EdgeSight data.

**Architecture:** A typed browser client calls same-origin Next route handlers. The server handlers forward only versioned processing control requests to the local EdgeSight API using a server-only key. Requests are accepted only from a loopback-hosted local dashboard; the key never enters browser code. The UI distinguishes live processing status from the existing sample analytics and fails closed when local control is not configured.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Node test runner.

**Spec:** User request in this task (no spec file in the repository).

## Global Constraints

- Never edit, commit to, reset, rebase, merge into, or push to `main`; never touch `website-*` branches.
- Work only in the existing worktree branch `product/dashboard-foundation`, based on `353663e3b43c76180fce4151a4ef2c3d686dbc87`; this name is applied by renaming the already existing isolated local branch in place.
- Keep website and EdgeSight repositories independent; use only documented `/api/v1/processing/*` responses.
- Never import Python model code, load weights, or directly control Docker from the website.
- Keep the EdgeSight API key server-side and accept control only on a loopback-hosted local dashboard.
- These website control routes operate only when the dashboard itself is local; a hosted website cannot start/stop a remote edge machine.
- Show unknown/stale/error state explicitly; do not substitute missing live values with zero or sample values.
- Do not claim public tenant authorization. Real authentication and tenant scope remain a release blocker for remote deployment.

## Review Focus

- EdgeSight offline, stale, malformed, or unreachable: show an unavailable/error state without fabricated metrics.
- Missing local API URL or server key: disable Start and explain the local setup needed.
- Non-loopback host/origin: reject all control calls.
- Double-click/retry Start or Stop: API calls remain idempotent and the UI cannot imply duplicate sessions.
- Sample analytics remain visible only with an explicit sample-data label, never as current live measurements.

---

### Task 1: Typed control client and local API route handlers

**Files:**
- Create: `src/lib/processing-control.ts`
- Create: `app/api/processing/status/route.ts`
- Create: `app/api/processing/start/route.ts`
- Create: `app/api/processing/stop/route.ts`
- Create: `tests/processing-control.test.mjs`
- Modify: `package.json`

**Interfaces:**
- Browser client exposes typed `getProcessingStatus()`, `startProcessing(cameraIds)`, and `stopProcessing()` functions through same-origin Next routes under the verified root `app/` App Router directory (`src/app/` is a component folder, not the route root).
- Route handlers use server-only `EDGESIGHT_API_URL` and `EDGESIGHT_API_KEY`; require `Host` and `Origin` to be loopback; forward no arbitrary path or command.

- [ ] Add Node tests for status parsing, unavailable response, failed authorization, and safe start/stop payload construction.
- [ ] Run tests and verify expected red failures.
- [ ] Implement route handlers and typed client; ensure API credentials are absent from serialized responses and browser bundles.
- [ ] Verify focused tests pass and TypeScript/lint succeeds when dependencies are available.

### Task 2: Dashboard processing controls and trustworthy states

**Files:**
- Create: `src/app/ProcessingControl.tsx`
- Modify: `src/app/DashboardPage.tsx`
- Modify: `src/app/screens/Tour.tsx`
- Test: `tests/processing-control.test.mjs`

- [ ] Add tests for OFF, STARTING, RUNNING, STOPPING, ERROR, stale, and unconfigured UI state labels and actions.
- [ ] Run tests to observe expected failures.
- [ ] Add a compact “Edge processing” panel with configured camera selection, Start, Stop, session/freshness/error display, and refresh status action.
- [ ] Label current dashboard metrics as sample/demo data and keep them separate from EdgeSight live status.
- [ ] Run `node --test tests/*.test.mjs`, `npm run lint`, and `npm run build` when dependencies are available; review for leaked secret/env values.
- [ ] Review diff and commit with `[DASHBOARD]` label; do not push.
