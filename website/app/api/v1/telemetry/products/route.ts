import { NextResponse } from "next/server"
import { bulkInsert, ensureSchema, ingestAuthorized, nullableMetric } from "../../../../../src/lib/telemetry-db"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

/**
 * Product interest ingest.
 *
 * Body: { batch_size, products: ProductInterestItem[], exported_at }
 *
 * One row per category per rollup window: how many distinct shoppers were
 * near the category, how many times it was detected and how long they
 * lingered. Aggregates only.
 */
export async function POST(request: Request) {
  const auth = ingestAuthorized(request)
  if (!auth.ok) {
    return NextResponse.json({ error: auth.reason }, { status: 401 })
  }

  let body: { batch_size?: number; products?: Record<string, unknown>[] }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 })
  }

  const products = Array.isArray(body.products) ? body.products : []
  if (products.length === 0) {
    return NextResponse.json({ error: "no products in payload" }, { status: 400 })
  }

  await ensureSchema()

  const rows = products.map((p) => ({
    store_id: p.store_id ?? null,
    device_id: p.device_id ?? null,
    camera_id: p.camera_id ?? null,
    category: p.category ?? null,
    viewers: nullableMetric(p.viewers),
    detections: nullableMetric(p.detections),
    total_dwell_seconds: nullableMetric(p.total_dwell_seconds),
    avg_dwell_seconds: nullableMetric(p.avg_dwell_seconds),
    timestamp_start: p.timestamp_start ?? null,
    timestamp_end: p.timestamp_end ?? null,
  }))

  await bulkInsert(
    "telemetry_products",
    [
      "store_id",
      "device_id",
      "camera_id",
      "category",
      "viewers",
      "detections",
      "total_dwell_seconds",
      "avg_dwell_seconds",
      "timestamp_start",
      "timestamp_end",
    ],
    rows
  )

  return NextResponse.json({ accepted: rows.length })
}
