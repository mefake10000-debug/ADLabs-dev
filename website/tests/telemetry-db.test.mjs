import test from "node:test"
import assert from "node:assert/strict"
import { ingestAuthorized, normalizeRollup, queryRows } from "../src/lib/telemetry-db.ts"

test("telemetry ingest rejects requests when the server secret is not configured", () => {
  const previous = process.env.EDGE_INGEST_KEY
  delete process.env.EDGE_INGEST_KEY
  try {
    const result = ingestAuthorized(new Request("http://localhost/api/v1/telemetry", { method: "POST" }))
    assert.equal(result.ok, false)
    assert.match(result.reason, /not configured/i)
  } finally {
    if (previous === undefined) delete process.env.EDGE_INGEST_KEY
    else process.env.EDGE_INGEST_KEY = previous
  }
})

test("telemetry ingest accepts only the configured server secret", () => {
  const previous = process.env.EDGE_INGEST_KEY
  process.env.EDGE_INGEST_KEY = "test-key"
  try {
    assert.equal(ingestAuthorized(new Request("http://localhost/api/v1/telemetry", {
      method: "POST",
      headers: { "x-api-key": "test-key" },
    })).ok, true)
    assert.equal(ingestAuthorized(new Request("http://localhost/api/v1/telemetry", { method: "POST" })).ok, false)
  } finally {
    if (previous === undefined) delete process.env.EDGE_INGEST_KEY
    else process.env.EDGE_INGEST_KEY = previous
  }
})

test("missing or invalid aggregate metrics remain absent while a measured zero stays zero", async () => {
  const { nullableMetric } = await import("../src/lib/telemetry-db.ts")
  assert.equal(nullableMetric(undefined), null)
  assert.equal(nullableMetric(null), null)
  assert.equal(nullableMetric("0"), null)
  assert.equal(nullableMetric(Number.NaN), null)
  assert.equal(nullableMetric(0), 0)
  assert.equal(nullableMetric(2.5), 2.5)
})

test("rollup ingestion preserves explicit zero and leaves omitted or invalid metrics null", () => {
  const normalized = normalizeRollup({
    store_id: "store-1",
    camera_id: "cam-1",
    in_count: 0,
    out_count: undefined,
    current_occupancy: "4",
    avg_dwell_seconds: 4.5,
    queue_length: Number.NaN,
  })
  assert.equal(normalized.in_count, 0)
  assert.equal(normalized.out_count, null)
  assert.equal(normalized.current_occupancy, null)
  assert.equal(normalized.avg_dwell_seconds, 4.5)
  assert.equal(normalized.queue_length, null)
  assert.equal(normalized.store_id, "store-1")
  assert.equal(normalized.camera_id, "cam-1")
})

test("database results normalize to rows and malformed result shapes become empty", () => {
  const rows = [{ camera_id: "cam-1" }]
  assert.equal(queryRows(rows), rows)
  assert.deepEqual(queryRows(null), [])
  assert.deepEqual(queryRows({ rows }), [])
})
