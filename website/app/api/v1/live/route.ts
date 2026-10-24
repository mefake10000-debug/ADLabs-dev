import { NextResponse } from "next/server"
import { db, liveTelemetryAccess, nullableMetric, queryRows } from "../../../../src/lib/telemetry-db"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

type Row = Record<string, unknown>

/**
 * Live snapshot for the Live Demo.
 *
 * Reads back what the edge node actually pushed. If the edge node has never
 * reported, this returns { online: false } rather than invented numbers.
 */
export async function GET(request: Request) {
  const access = liveTelemetryAccess(process.env.NODE_ENV)
  if (!access.allowed) {
    return NextResponse.json({ online: false, state: "UNAVAILABLE", reason: access.reason }, { status: 503 })
  }
  const url = new URL(request.url)
  const minutes = Math.min(
    Math.max(Number(url.searchParams.get("minutes") ?? 15) || 15, 1),
    24 * 60
  )

  const sql = await db()

  let cameraRow: Row | undefined
  try {
    const rows = await sql`
      SELECT camera_id, store_id, device_id
      FROM telemetry_rollups
      GROUP BY camera_id, store_id, device_id
      ORDER BY MAX(received_at) DESC
      LIMIT 1
    `
    cameraRow = queryRows(rows)[0]
  } catch {
    // Schema not created yet -> nothing has ever been pushed.
    return NextResponse.json({
      online: false,
      reason: "no telemetry received yet",
      received: 0,
    })
  }

  if (!cameraRow) {
    return NextResponse.json({
      online: false,
      reason: "no telemetry received yet",
      received: 0,
    })
  }

  const cameraId = cameraRow.camera_id as string
  const windowSeconds = minutes * 60

  const [rollupRows, eventRows, productRows, freshness] = await Promise.all([
    sql`
      SELECT
        COUNT(*)::int                                   AS rollup_windows,
        SUM(in_count)::int                              AS entries,
        SUM(out_count)::int                             AS exits,
        MAX(current_occupancy)::int                     AS peak_occupancy,
        AVG(avg_dwell_seconds)::float                   AS avg_dwell_seconds,
        MAX(queue_length)::int                          AS queue_length,
        MAX(queue_alert_active)::int                    AS queue_alert_active,
        AVG(avg_attention_score)::float                 AS attention_score,
        AVG(facing_ratio)::float                        AS facing_ratio,
        AVG(phone_usage_rate)::float                    AS phone_usage_rate,
        AVG(engaged_ratio)::float                       AS engaged_ratio,
        AVG(group_count)::float                         AS group_count,
        AVG(people_in_groups)::float                    AS people_in_groups
      FROM telemetry_rollups
      WHERE camera_id = ${cameraId}
        AND received_at > NOW() - (${windowSeconds} * INTERVAL '1 second')
    `,
    sql`
      SELECT
        COUNT(*) FILTER (WHERE direction = 'in')::int   AS entries,
        COUNT(*) FILTER (WHERE direction = 'out')::int  AS exits,
        COUNT(*)::int                                  AS total
      FROM telemetry_events
      WHERE camera_id = ${cameraId}
        AND received_at > NOW() - (${windowSeconds} * INTERVAL '1 second')
    `,
    sql`
      SELECT
        category,
        AVG(viewers)::float                            AS avg_viewers,
        SUM(viewers)::int                              AS viewer_observations,
        SUM(detections)::int                           AS detections,
        SUM(total_dwell_seconds)::float                AS total_dwell_seconds,
        COUNT(*)::int                                  AS windows
      FROM telemetry_products
      WHERE camera_id = ${cameraId}
        AND received_at > NOW() - (${windowSeconds} * INTERVAL '1 second')
      GROUP BY category
      ORDER BY viewer_observations DESC
      LIMIT 12
    `,
    sql`
      SELECT
        MAX(received_at)                              AS last_received,
        EXTRACT(EPOCH FROM (NOW() - MAX(received_at)))::float AS seconds_since
      FROM telemetry_rollups
      WHERE camera_id = ${cameraId}
    `,
  ])

  const rollup = queryRows(rollupRows)[0] ?? {}
  const events = queryRows(eventRows)[0] ?? {}
  const fresh = queryRows(freshness)[0] ?? {}
  const secondsSince = Number(fresh.seconds_since ?? 0)
  const rollupEntries = nullableMetric(rollup.entries)
  const rollupExits = nullableMetric(rollup.exits)
  const hasWindowEvents = Number(events.total ?? 0) > 0
  const eventEntries = hasWindowEvents ? nullableMetric(events.entries) : null
  const eventExits = hasWindowEvents ? nullableMetric(events.exits) : null
  const queueAlertValue = nullableMetric(rollup.queue_alert_active)

  // Occupancy right now comes from the most recent rollup, not from the window
  // average, so the demo does not show a historical mean as if it were live.
  const latest = await sql`
    SELECT current_occupancy, timestamp_end, demographics_json
    FROM telemetry_rollups
    WHERE camera_id = ${cameraId}
    ORDER BY received_at DESC
    LIMIT 1
  `
  const last = queryRows(latest)[0] ?? {}

  let demographics: Row = {
    sample_size: null,
    k_anonymity: 10,
    age_bands: [],
    gender_split: [],
    suppressed_count: null,
    publishable: false,
    note: "no demographics published yet",
  }
  if (typeof last.demographics_json === "string" && last.demographics_json) {
    try {
      demographics = JSON.parse(last.demographics_json)
    } catch {
      /* keep the empty default */
    }
  }

  const series = await sql`
    SELECT
      timestamp_start,
      current_occupancy,
      in_count,
      out_count,
      engaged_ratio,
      avg_attention_score
    FROM telemetry_rollups
    WHERE camera_id = ${cameraId}
      AND received_at > NOW() - (${windowSeconds} * INTERVAL '1 second')
    ORDER BY received_at ASC
  `

  return NextResponse.json({
    online: secondsSince < 60,
    received: Number(rollup.rollup_windows ?? 0) + Number(events.total ?? 0),
    camera: {
      id: cameraId,
      store_id: cameraRow.store_id,
      device_id: cameraRow.device_id,
    },
    window_minutes: minutes,
    last_update: fresh.last_received ? new Date(String(fresh.last_received)).toISOString() : null,
    seconds_since_update: Math.round(secondsSince),
    traffic: {
      entries: eventEntries ?? rollupEntries,
      exits: eventExits ?? rollupExits,
      occupancy_now: nullableMetric(last.current_occupancy),
      peak_occupancy: nullableMetric(rollup.peak_occupancy),
      avg_dwell_seconds: nullableMetric(rollup.avg_dwell_seconds),
      queue_length: nullableMetric(rollup.queue_length),
      queue_alert_active: queueAlertValue === null ? null : queueAlertValue > 0,
    },
    engagement: {
      attention_score: nullableMetric(rollup.attention_score),
      facing_ratio: nullableMetric(rollup.facing_ratio),
      phone_usage_rate: nullableMetric(rollup.phone_usage_rate),
      engaged_ratio: nullableMetric(rollup.engaged_ratio),
      group_count: rollup.group_count === null ? null : Math.round(Number(rollup.group_count)),
      people_in_groups: rollup.people_in_groups === null ? null : Math.round(Number(rollup.people_in_groups)),
    },
    demographics,
    products: queryRows(productRows).map((p) => ({
      category: p.category,
      viewers: p.avg_viewers === null ? null : Math.round(Number(p.avg_viewers)),
      viewer_observations: nullableMetric(p.viewer_observations),
      detections: nullableMetric(p.detections),
      total_dwell_seconds: nullableMetric(p.total_dwell_seconds),
      windows: nullableMetric(p.windows),
    })),
    series: queryRows(series).map((s) => ({
      t: s.timestamp_start,
      occupancy: nullableMetric(s.current_occupancy),
      in: nullableMetric(s.in_count),
      out: nullableMetric(s.out_count),
      engaged: nullableMetric(s.engaged_ratio),
      attention: nullableMetric(s.avg_attention_score),
    })),
    provenance: {
      source: "EdgeSight edge node",
      transport: "HTTPS POST -> Vercel route handler -> Neon Postgres",
      note: "values are read from the telemetry database and are not independently model-validated by this route",
    },
  })
}
