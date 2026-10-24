# Runtime Hardening Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan task-by-task with test-first verification.

**Goal:** Make the existing pilot recoverable, safer to expose, and honest about runtime readiness, then push only the existing working branches.

**Architecture:** Keep the edge process and SQLite outbox. Add durable record identities, transactional receiver deduplication, explicit fallback delivery semantics, interruptible retries, storage maintenance, readiness and operator authentication. Protect the sibling portal with the same optional operator credentials and forward device credentials only server-side.

**Tech Stack:** Python, FastAPI, SQLite, unittest; Next.js, TypeScript, node:test.

**Spec:** This document records the user-authorized repository review recommendations from 2026-10-25.

## Global Constraints
- Never switch, merge, or push main/master; target fps-optimization-enhance in each repository.
- Preserve pre-existing local work; do not commit footage, weights, credentials or runtime databases.
- Preserve trusted-local development defaults; secure deployment mode must fail closed without operator credentials.
- No fabricated accuracy or FPS claims; hardware and labeled field evaluation remain deployment acceptance gates.
- No new cloud infrastructure or destructive runtime restarts.

## Review Focus
- Lost HTTP acknowledgement must not duplicate accepted telemetry.
- Restart and upgrade must retain record IDs and pending records.
- Partial acknowledgements must never discard unacknowledged records.
- Stale snapshots must not imply a ready pipeline.
- Operator authentication must cover the portal and live video without leaking device keys.

### Task 1: Durable delivery
Files: src/storage/local_buffer.py, server/telemetry_receipts.py, server/app.py, src/telemetry/exporter.py, tests/test_runtime_hardening.py.
Interfaces: persisted record_id on outbox records; receiver accepts optional record_id and acknowledges accepted_record_ids. Legacy records remain compatible.
- [x] Add and run failing tests for stable IDs across restart, duplicate batch delivery, rollback and partial acknowledgement.
- [x] Implement transactional deduplication scoped by store/device/channel and persistent UUID migration.
- [x] Implement acknowledgement-aware exporter with documented fallback endpoints and interruptible shutdown.
- [x] Run focused and full Python suites.

### Task 2: Storage and readiness
Files: src/storage/local_buffer.py, server/runtime_readiness.py, server/app.py, tests/test_runtime_hardening.py.
Interfaces: maintenance only removes acknowledged old data; /ready reports snapshot freshness and writable storage separately from /health.
- [x] Add failing tests for pending-record retention, stale/missing/future snapshots and low disk.
- [x] Add bounded cleanup, backlog statistics, WAL/busy timeout and operational readiness response.
- [x] Run focused and full Python suites.

### Task 3: Operator access and portal integration
Files: server/operator_access.py, server/app.py, website/proxy.ts, website/src/lib/operator-access.ts, website/app/api/edgesight/*, tests.
Interfaces: optional HTTP Basic operator credentials; EDGESIGHT_SECURE_MODE requires credentials and device key. Device ingestion stays API-key authenticated; operator browser routes use operator credentials.
- [x] Add failing tests for secure-mode misconfiguration, unauthorized reads, operator access, and portal access policy.
- [x] Implement access middleware, remove device key from HTML, and add server-only forwarding plus a same-origin API proxy.
- [x] Run Python suite, portal tests and production build.

### Task 4: Runtime integrity and acceptance guide
Files: src/main.py, tests/test_runtime_hardening.py, docs/runtime-hardening.md, website/README.md.
- [x] Add failing regression for duplicate runtime method definitions, then remove the shadowed definition.
- [x] Document recovery drills, evaluation protocol, performance budgets, secure configuration, retention and remaining limits.
- [x] Review diffs and secrets; run suites/build; commit reviewed local prerequisite work and hardening changes; push explicit working-branch refs in both repositories (delivery tracked in progress log).

## Scope refinement
The evaluation deliverable also includes src/evaluation.py and tests/test_evaluation_runner.py: a real offline box-scoring command with provenance, without fabricating labels or field accuracy.
