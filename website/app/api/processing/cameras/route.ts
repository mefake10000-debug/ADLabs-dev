import { forwardLocalEdgeRequest } from "../../../../src/lib/processing-control"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

export async function GET(request: Request) {
  const upstream = await forwardLocalEdgeRequest(request, "/api/v1/config/cameras", "GET")
  if (!upstream.ok) return upstream
  try {
    const payload = await upstream.json()
    const cameras = Array.isArray(payload.cameras) ? payload.cameras : []
    return Response.json({ cameras: cameras
      .filter((camera: Record<string, unknown>) => camera.id && camera.enabled !== false)
      .map((camera: Record<string, unknown>) => ({ id: String(camera.id), name: String(camera.name || camera.id) }))
    })
  } catch {
    return Response.json({ detail: "EdgeSight returned an invalid camera list." }, { status: 502 })
  }
}
