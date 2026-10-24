import test from "node:test"
import assert from "node:assert/strict"
import { liveTelemetryAccess } from "../src/lib/telemetry-db.ts"

test("production live telemetry stays unavailable until tenant authorization exists", () => {
  assert.deepEqual(liveTelemetryAccess("production"), {
    allowed: false,
    reason: "Tenant authorization is not configured for live telemetry.",
  })
  assert.deepEqual(liveTelemetryAccess("development"), { allowed: true })
})
