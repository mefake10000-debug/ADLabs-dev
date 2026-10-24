import { NextResponse } from "next/server"
import { bulkInsert, ensureSchema, ingestAuthorized, normalizeRollup } from "../../../../src/lib/telemetry-db"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

/**
 * EdgeSight rollup ingest.
 *
 * Body: { batch_size, rollups: RollupItem[], exported_at }
 *
 * Every field is an aggregate over a 10 second window. There is no face, no
 * image, no embedding and no per-person row in this payload.
 */
export async function POST(request: Request) {
  const auth = ingestAuthorized(request)
  if (!auth.ok) {
    return NextResponse.json({ error: auth.reason }, { status: 401 })
  }

  let body: { batch_size?: number; rollups?: Record<string, unknown>[] }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 })
  }

  const rollups = Array.isArray(body.rollups) ? body.rollups : []
  if (rollups.length === 0) {
    return NextResponse.json({ error: "no rollups in payload" }, { status: 400 })
  }

  await ensureSchema()

  const rows = rollups.map(normalizeRollup)

  await bulkInsert(
    "telemetry_rollups",
    [
      "store_id",
      "device_id",
      "camera_id",
      "timestamp_start",
      "timestamp_end",
      "in_count",
      "out_count",
      "current_occupancy",
      "avg_dwell_seconds",
      "queue_length",
      "avg_queue_wait_seconds",
      "queue_alert_active",
      "avg_attention_score",
      "facing_ratio",
      "phone_usage_rate",
      "engaged_ratio",
      "group_count",
      "people_in_groups",
      "demographics_json",
    ],
    rows
  )

  return NextResponse.json({ accepted: rows.length })
}
