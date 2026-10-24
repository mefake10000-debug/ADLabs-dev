import { NextResponse } from "next/server"
import { bulkInsert, ensureSchema, ingestAuthorized } from "../../../../../src/lib/telemetry-db"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

/**
 * EdgeSight tripwire event ingest.
 *
 * Body: { batch_size, events: EventItem[], exported_at }
 *
 * A tripwire event is "someone crossed this line in this direction". The
 * track_id is a per-camera integer that the edge node reuses inside a single
 * session; it is not an identifier and it is not carried across sessions.
 */
export async function POST(request: Request) {
  const auth = ingestAuthorized(request)
  if (!auth.ok) {
    return NextResponse.json({ error: auth.reason }, { status: 401 })
  }

  let body: { batch_size?: number; events?: Record<string, unknown>[] }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 })
  }

  const events = Array.isArray(body.events) ? body.events : []
  if (events.length === 0) {
    return NextResponse.json({ error: "no events in payload" }, { status: 400 })
  }

  await ensureSchema()

  const rows = events.map((e) => ({
    store_id: e.store_id ?? null,
    device_id: e.device_id ?? null,
    camera_id: e.camera_id ?? null,
    wire_id: e.wire_id ?? null,
    track_id: e.track_id ?? null,
    direction: e.direction ?? null,
    event_timestamp: e.event_timestamp ?? null,
  }))

  await bulkInsert(
    "telemetry_events",
    [
      "store_id",
      "device_id",
      "camera_id",
      "wire_id",
      "track_id",
      "direction",
      "event_timestamp",
    ],
    rows
  )

  return NextResponse.json({ accepted: rows.length })
}
