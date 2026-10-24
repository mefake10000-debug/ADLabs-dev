import { forwardLocalEdgeRequest } from "../../../../src/lib/processing-control"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

export function POST(request: Request) {
  return forwardLocalEdgeRequest(request, "/api/v1/processing/stop", "POST", {})
}
