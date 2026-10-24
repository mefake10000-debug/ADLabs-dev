import test from "node:test"
import assert from "node:assert/strict"
import {
  buildProcessingStartPayload,
  processingStateLabel,
  prepareLocalEdgeRequest,
} from "../src/lib/processing-control.ts"

test("local processing controls accept only a loopback dashboard and edge endpoint", () => {
  const prepared = prepareLocalEdgeRequest({
    host: "localhost:3000",
    origin: "http://localhost:3000",
    edgeUrl: "http://127.0.0.1:8000",
    apiKey: "secret",
    localDevelopment: true,
    path: "/api/v1/processing/status",
    method: "GET",
  })
  assert.equal(prepared.error, undefined)
  assert.equal(prepared.url, "http://127.0.0.1:8000/api/v1/processing/status")
  assert.equal(prepared.init.headers["X-API-Key"], "secret")
  assert.equal(prepared.init.cache, "no-store")
})

test("processing states stay distinct and missing status is never shown as stopped", () => {
  assert.equal(processingStateLabel("OFF"), "Stopped")
  assert.equal(processingStateLabel("STARTING"), "Starting")
  assert.equal(processingStateLabel("RUNNING"), "Running")
  assert.equal(processingStateLabel("STOPPING"), "Stopping")
  assert.equal(processingStateLabel("ERROR"), "Needs attention")
  assert.equal(processingStateLabel("UNAVAILABLE"), "Local EdgeSight unavailable")
})

test("hosted dashboards and remote EdgeSight URLs are rejected", () => {
  const remoteDashboard = prepareLocalEdgeRequest({
    host: "adlabs.example.com",
    origin: "https://adlabs.example.com",
    edgeUrl: "http://127.0.0.1:8000",
    apiKey: "secret",
    localDevelopment: true,
    path: "/api/v1/processing/status",
    method: "GET",
  })
  const remoteEdge = prepareLocalEdgeRequest({
    host: "localhost:3000",
    origin: "http://localhost:3000",
    edgeUrl: "https://edge.example.com",
    apiKey: "secret",
    localDevelopment: true,
    path: "/api/v1/processing/status",
    method: "GET",
  })
  assert.match(remoteDashboard.error, /local dashboard/i)
  assert.match(remoteEdge.error, /loopback/i)
  const invalidLoopback = prepareLocalEdgeRequest({
    host: "127.999.0.1:3000",
    origin: "http://127.999.0.1:3000",
    edgeUrl: "http://127.0.0.1:8000",
    apiKey: "secret",
    localDevelopment: true,
    path: "/api/v1/processing/status",
    method: "GET",
  })
  assert.match(invalidLoopback.error, /local dashboard/i)
})

test("control secret is required and never included in client-visible payload", () => {
  const prepared = prepareLocalEdgeRequest({
    host: "127.0.0.1:3000",
    origin: "http://127.0.0.1:3000",
    edgeUrl: "http://localhost:8000",
    apiKey: "",
    localDevelopment: true,
    path: "/api/v1/processing/status",
    method: "GET",
  })
  assert.match(prepared.error, /not configured/i)
})

test("production and hosted dashboards cannot proxy local controls", () => {
  const prepared = prepareLocalEdgeRequest({
    host: "localhost:3000",
    origin: "http://localhost:3000",
    edgeUrl: "http://127.0.0.1:8000",
    apiKey: "secret",
    localDevelopment: false,
    path: "/api/v1/processing/status",
    method: "GET",
  })
  assert.match(prepared.error, /disabled outside the local development/i)
})

test("start payload accepts only unique, non-empty camera IDs", () => {
  assert.deepEqual(buildProcessingStartPayload(["cam_1"]), { camera_ids: ["cam_1"] })
  assert.throws(() => buildProcessingStartPayload([]), /select at least one/i)
  assert.throws(() => buildProcessingStartPayload(["cam_1", "cam_1"]), /unique/i)
  assert.throws(() => buildProcessingStartPayload(["../other"]), /invalid/i)
})
