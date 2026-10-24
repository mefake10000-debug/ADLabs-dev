import { forwardLocalEdgeRequest, buildProcessingStartPayload } from "../../../../src/lib/processing-control"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

export async function POST(request: Request) {
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return Response.json({ detail: "Request must contain valid JSON." }, { status: 400 })
  }
  if (!body || typeof body !== "object" || !("camera_ids" in body)) {
    return Response.json({ detail: "Start requires a camera_ids array." }, { status: 400 })
  }
  try {
    return await forwardLocalEdgeRequest(
      request,
      "/api/v1/processing/start",
      "POST",
      buildProcessingStartPayload((body as { camera_ids: unknown }).camera_ids),
    )
  } catch (error) {
    return Response.json({ detail: error instanceof Error ? error.message : "Invalid camera selection." }, { status: 400 })
  }
}
