type NeonClient = ReturnType<(typeof import("@neondatabase/serverless"))["neon"]>

let client: Promise<NeonClient> | null = null
let schemaReady: Promise<void> | null = null

export async function db(): Promise<NeonClient> {
  if (!client) {
    const url = process.env.DATABASE_URL
    if (!url) throw new Error("DATABASE_URL is not configured")
    client = import("@neondatabase/serverless").then(({ neon }) => neon(url))
  }
  return client
}

export function nullableMetric(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

export function queryRows(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value as Record<string, unknown>[] : []
}

const ROLLUP_METRICS = [
  "in_count", "out_count", "current_occupancy", "avg_dwell_seconds", "queue_length",
  "avg_queue_wait_seconds", "queue_alert_active", "avg_attention_score", "facing_ratio",
  "phone_usage_rate", "engaged_ratio", "group_count", "people_in_groups",
] as const

export function normalizeRollup(row: Record<string, unknown>): Record<string, unknown> {
  const normalized: Record<string, unknown> = {
    store_id: typeof row.store_id === "string" ? row.store_id : null,
    device_id: typeof row.device_id === "string" ? row.device_id : null,
    camera_id: typeof row.camera_id === "string" ? row.camera_id : null,
    timestamp_start: typeof row.timestamp_start === "string" ? row.timestamp_start : null,
    timestamp_end: typeof row.timestamp_end === "string" ? row.timestamp_end : null,
    demographics_json: typeof row.demographics_json === "string" ? row.demographics_json : null,
  }
  for (const field of ROLLUP_METRICS) normalized[field] = nullableMetric(row[field])
  return normalized
}

export function ingestAuthorized(request: Request): { ok: boolean; reason?: string } {
  const expected = process.env.EDGE_INGEST_KEY
  if (!expected) return { ok: false, reason: "EDGE_INGEST_KEY is not configured" }
  const provided = request.headers.get("x-api-key")
  if (!provided || provided !== expected) return { ok: false, reason: "invalid or missing X-API-Key" }
  return { ok: true }
}

export function liveTelemetryAccess(nodeEnv: string | undefined):
  | { allowed: true }
  | { allowed: false; reason: string } {
  if (nodeEnv === "production") {
    return { allowed: false, reason: "Tenant authorization is not configured for live telemetry." }
  }
  return { allowed: true }
}

export async function ensureSchema(): Promise<void> {
  if (!schemaReady) {
    schemaReady = (async () => {
      const sql = await db()
      await sql`CREATE TABLE IF NOT EXISTS telemetry_rollups (
        id SERIAL PRIMARY KEY, store_id TEXT, device_id TEXT, camera_id TEXT,
        timestamp_start TEXT, timestamp_end TEXT, in_count INTEGER, out_count INTEGER,
        current_occupancy INTEGER, avg_dwell_seconds REAL, queue_length INTEGER,
        avg_queue_wait_seconds REAL, queue_alert_active INTEGER, avg_attention_score REAL,
        facing_ratio REAL, phone_usage_rate REAL, engaged_ratio REAL, group_count INTEGER,
        people_in_groups INTEGER, demographics_json TEXT, received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`
      await sql`CREATE TABLE IF NOT EXISTS telemetry_events (
        id SERIAL PRIMARY KEY, store_id TEXT, device_id TEXT, camera_id TEXT, wire_id TEXT,
        track_id INTEGER, direction TEXT, event_timestamp TEXT, received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`
      await sql`CREATE TABLE IF NOT EXISTS telemetry_products (
        id SERIAL PRIMARY KEY, store_id TEXT, device_id TEXT, camera_id TEXT, category TEXT,
        viewers INTEGER, detections INTEGER, total_dwell_seconds REAL, avg_dwell_seconds REAL,
        timestamp_start TEXT, timestamp_end TEXT, received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`
      await sql`CREATE INDEX IF NOT EXISTS idx_rollups_camera_ts ON telemetry_rollups (camera_id, timestamp_start DESC)`
      await sql`CREATE INDEX IF NOT EXISTS idx_products_camera_ts ON telemetry_products (camera_id, timestamp_start DESC)`
    })().catch((error) => {
      schemaReady = null
      throw error
    })
  }
  return schemaReady
}

const SAFE_IDENTIFIER = /^[a-z_][a-z0-9_]*$/

export async function bulkInsert(
  table: string,
  columns: string[],
  rows: Record<string, unknown>[],
): Promise<void> {
  if (rows.length === 0) return
  if (!SAFE_IDENTIFIER.test(table) || columns.some((column) => !SAFE_IDENTIFIER.test(column))) {
    throw new Error("unsafe SQL identifier")
  }
  const values: unknown[] = []
  const tuples = rows.map((row) => `(${columns.map((column) => {
    values.push(row[column] ?? null)
    return `$${values.length}`
  }).join(", ")})`)
  await (await db()).query(`INSERT INTO ${table} (${columns.join(", ")}) VALUES ${tuples.join(", ")}`, values)
}
