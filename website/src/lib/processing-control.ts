export type ProcessingState = "OFF" | "STARTING" | "RUNNING" | "STOPPING" | "ERROR"

export type ProcessingStatus = {
  state: ProcessingState
  session_id: string | null
  camera_ids: string[]
  worker_pid: number | null
  started_at: number | null
  updated_at: number
  error: string | null
  fresh: boolean
  video_freshness: Record<string, boolean>
}

const ALLOWED_EDGE_PATHS = new Set([
  "/api/v1/config/cameras",
  "/api/v1/processing/status",
  "/api/v1/processing/start",
  "/api/v1/processing/stop",
])

function isLoopback(hostname: string): boolean {
  const normalized = hostname.toLowerCase().replace(/^\[|\]$/g, "")
  if (normalized === "localhost" || normalized === "::1") return true
  const octets = normalized.split(".")
  return octets.length === 4
    && octets[0] === "127"
    && octets.every((octet) => /^\d{1,3}$/.test(octet) && Number(octet) <= 255)
}

export function processingStateLabel(state: ProcessingState | "UNAVAILABLE"): string {
  switch (state) {
    case "OFF": return "Stopped"
    case "STARTING": return "Starting"
    case "RUNNING": return "Running"
    case "STOPPING": return "Stopping"
    case "ERROR": return "Needs attention"
    case "UNAVAILABLE": return "Local EdgeSight unavailable"
  }
}

export function prepareLocalEdgeRequest(input: {
  host: string | null
  origin: string | null
  edgeUrl: string
  apiKey: string
  localDevelopment: boolean
  path: string
  method: "GET" | "POST"
  body?: unknown
}): { url?: string; init?: RequestInit; error?: string } {
  if (!input.localDevelopment) {
    return { error: "Processing control is disabled outside the local development dashboard." }
  }
  if (!input.host) return { error: "Local dashboard host is missing." }
  let dashboardUrl: URL
  try {
    dashboardUrl = new URL(`http://${input.host}`)
  } catch {
    return { error: "Invalid local dashboard host." }
  }
  if (!isLoopback(dashboardUrl.hostname)) {
    return { error: "Processing controls are available only from a local dashboard." }
  }
  if (input.origin) {
    try {
      const origin = new URL(input.origin)
      if (!isLoopback(origin.hostname) || origin.host !== dashboardUrl.host) {
        return { error: "Processing controls require a same-origin local dashboard request." }
      }
    } catch {
      return { error: "Invalid dashboard origin." }
    }
  } else if (input.method === "POST") {
    return { error: "A same-origin local dashboard request is required for processing changes." }
  }
  if (!input.apiKey) return { error: "Local EdgeSight control is not configured on this dashboard." }
  if (!ALLOWED_EDGE_PATHS.has(input.path)) return { error: "Unsupported EdgeSight control operation." }

  let edgeUrl: URL
  try {
    edgeUrl = new URL(input.edgeUrl)
  } catch {
    return { error: "Local EdgeSight API URL is not configured correctly." }
  }
  if (edgeUrl.protocol !== "http:" || !isLoopback(edgeUrl.hostname)) {
    return { error: "Dashboard controls can connect only to an HTTP EdgeSight API on this computer's loopback interface." }
  }
  edgeUrl.pathname = input.path
  edgeUrl.search = ""
  edgeUrl.hash = ""
  const headers: Record<string, string> = { "X-API-Key": input.apiKey }
  const init: RequestInit = { method: input.method, headers, cache: "no-store", redirect: "error" }
  if (input.method === "POST") {
    headers["Content-Type"] = "application/json"
    init.body = JSON.stringify(input.body ?? {})
  }
  return { url: edgeUrl.toString(), init }
}

export function buildProcessingStartPayload(cameraIds: unknown): { camera_ids: string[] } {
  if (!Array.isArray(cameraIds) || cameraIds.length === 0) {
    throw new Error("Select at least one camera before starting processing.")
  }
  if (cameraIds.some((value) => typeof value !== "string" || !/^[a-zA-Z0-9_-]{1,80}$/.test(value))) {
    throw new Error("Camera selection contains an invalid ID.")
  }
  if (new Set(cameraIds).size !== cameraIds.length) {
    throw new Error("Camera IDs must be unique.")
  }
  return { camera_ids: cameraIds }
}

export async function forwardLocalEdgeRequest(
  request: Request,
  path: string,
  method: "GET" | "POST",
  body?: unknown,
): Promise<Response> {
  let prepared: ReturnType<typeof prepareLocalEdgeRequest>
  try {
    prepared = prepareLocalEdgeRequest({
      host: request.headers.get("host"),
      origin: request.headers.get("origin"),
      edgeUrl: process.env.EDGESIGHT_API_URL || "http://127.0.0.1:8000",
      apiKey: process.env.EDGESIGHT_API_KEY || "",
      localDevelopment: process.env.NODE_ENV === "development",
      path,
      method,
      body,
    })
  } catch {
    return Response.json({ detail: "Local EdgeSight control is unavailable." }, { status: 503 })
  }
  if (prepared.error || !prepared.url || !prepared.init) {
    return Response.json({ detail: prepared.error || "Local EdgeSight control is unavailable." }, { status: 503 })
  }
  try {
    const upstream = await fetch(prepared.url, prepared.init)
    const contentType = upstream.headers.get("content-type") || "application/json"
    return new Response(await upstream.text(), { status: upstream.status, headers: { "content-type": contentType } })
  } catch {
    return Response.json({ detail: "Local EdgeSight is unavailable; processing state is unknown." }, { status: 503 })
  }
}
