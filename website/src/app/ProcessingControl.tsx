"use client"

import { useCallback, useEffect, useState } from "react"
import { Activity, Play, RefreshCw, Square, TriangleAlert } from "lucide-react"
import { processingStateLabel, type ProcessingStatus } from "../lib/processing-control"

type Camera = { id: string; name: string }
type ApiError = { detail?: string }

async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" })
  const payload = await response.json().catch(() => ({})) as T & ApiError
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status}).`)
  return payload
}

export function ProcessingControl() {
  const [status, setStatus] = useState<ProcessingStatus | null>(null)
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true)
    try {
      const [nextStatus, cameraList] = await Promise.all([
        readJson<ProcessingStatus>("/api/processing/status"),
        readJson<{ cameras: Camera[] }>("/api/processing/cameras"),
      ])
      setStatus(nextStatus)
      setCameras(cameraList.cameras)
      if (nextStatus.camera_ids?.length) setSelected(nextStatus.camera_ids)
      else setSelected((current) => current.length ? current : cameraList.cameras.map((camera) => camera.id))
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Local EdgeSight is unavailable.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void refresh(true), 0)
    const timer = window.setInterval(() => void refresh(true), 5000)
    return () => {
      window.clearTimeout(initialRefresh)
      window.clearInterval(timer)
    }
  }, [refresh])

  const runAction = async (action: "start" | "stop") => {
    setBusy(true)
    setError(null)
    try {
      const next = action === "start"
        ? await readJson<ProcessingStatus>("/api/processing/start", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ camera_ids: selected }),
          })
        : await readJson<ProcessingStatus>("/api/processing/stop", { method: "POST" })
      setStatus(next)
      setError(next.error || null)
      await refresh(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update processing state.")
      await refresh(true)
    } finally {
      setBusy(false)
    }
  }

  const state = status?.state ?? "UNAVAILABLE"
  const active = state === "STARTING" || state === "RUNNING" || state === "STOPPING"
  const label = loading && !status ? "Checking local EdgeSight…" : processingStateLabel(state)

  return (
    <section className="mb-6 rounded-2xl border border-[var(--app-line)] bg-[var(--app-card)] p-5 sm:p-6" aria-labelledby="processing-control-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl" style={{ background: "var(--app-accent-soft)", color: "var(--app-accent)" }}>
            <Activity size={18} />
          </span>
          <div>
            <h2 id="processing-control-title" className="font-inter cosmic-text-base font-semibold text-[var(--app-text)]">Edge processing</h2>
            <p className="mt-1 font-inter cosmic-text-xs text-[var(--app-sub)]">Video and models stay stopped until you start a selected camera.</p>
            <p className="mt-1 font-inter cosmic-text-2xs text-[var(--app-faint)]">Local dashboard control only. A hosted website cannot start an edge machine.</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-[var(--app-line)] px-3 py-1.5 font-inter cosmic-text-xs font-semibold text-[var(--app-sub)]" aria-live="polite">
          <span className={`h-2 w-2 rounded-full ${state === "RUNNING" ? "bg-[var(--app-pos)]" : state === "ERROR" ? "bg-[var(--app-neg)]" : "bg-[var(--app-faint)]"}`} />
          {label}
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <fieldset disabled={active || busy || loading || cameras.length === 0}>
          <legend className="mb-2 font-inter cosmic-text-xs font-semibold text-[var(--app-sub)]">Choose camera(s)</legend>
          <div className="flex flex-wrap gap-2">
            {cameras.map((camera) => (
              <label key={camera.id} className="flex cursor-pointer items-center gap-2 rounded-xl border border-[var(--app-line)] px-3 py-2 font-inter cosmic-text-xs text-[var(--app-text)]">
                <input
                  type="checkbox"
                  checked={selected.includes(camera.id)}
                  onChange={(event) => setSelected((current) => event.target.checked
                    ? [...current, camera.id]
                    : current.filter((id) => id !== camera.id))}
                />
                {camera.name}
              </label>
            ))}
            {!loading && cameras.length === 0 && <span className="font-inter cosmic-text-xs text-[var(--app-faint)]">No enabled cameras are configured.</span>}
          </div>
        </fieldset>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--app-line)] px-3.5 py-2.5 font-inter cosmic-text-xs font-semibold text-[var(--app-sub)] disabled:opacity-50"
          >
            <RefreshCw size={14} /> Refresh status
          </button>
          <button
            type="button"
            onClick={() => void runAction("start")}
            disabled={busy || loading || active || selected.length === 0 || cameras.length === 0 || !!error}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 font-inter cosmic-text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-45"
            style={{ background: "var(--app-accent)" }}
          >
            <Play size={14} /> Start processing
          </button>
          <button
            type="button"
            onClick={() => void runAction("stop")}
            disabled={busy || !active}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--app-line)] px-4 py-2.5 font-inter cosmic-text-xs font-semibold text-[var(--app-text)] disabled:cursor-not-allowed disabled:opacity-45"
          >
            <Square size={13} /> Stop processing
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-[var(--app-line)] pt-3 font-inter cosmic-text-2xs text-[var(--app-faint)]" aria-live="polite">
        <span>Session: {status?.session_id ?? "—"}</span>
        <span>Video freshness: {status?.fresh ? "recent frame received" : state === "RUNNING" ? "waiting for a recent frame" : "not active"}</span>
        {error && <span className="inline-flex items-center gap-1.5 text-[var(--app-neg)]"><TriangleAlert size={13} />{error}</span>}
        {status?.error && !error && <span className="text-[var(--app-neg)]">{status.error}</span>}
      </div>
      <p className="mt-3 rounded-xl border border-[var(--app-line)] px-3 py-2.5 font-inter cosmic-text-2xs text-[var(--app-faint)]">
        The dashboard’s Demo-tagged analytics remain sample data. Starting processing shows runtime state; it does not convert those sample charts into live measurements.
      </p>
    </section>
  )
}
