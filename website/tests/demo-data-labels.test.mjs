import test from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import { formatDemoAnswer } from "../src/lib/demo-copy.ts"

const root = new URL("../src/app/", import.meta.url)

test("voice assistant answers identify dashboard fixtures as examples", () => {
  assert.equal(
    formatDemoAnswer("Today: 120 people visited."),
    "Sample data — not a live camera measurement. Today: 120 people visited.",
  )
})

test("business dashboard screens do not label fixture data as live or verified", async () => {
  const files = [
    "screens/Overview.tsx",
    "screens/Storefront.tsx",
    "screens/Manager.tsx",
    "screens/Alerts.tsx",
    "screens/Stores.tsx",
    "screens/History.tsx",
    "screens/Tour.tsx",
    "screens/Product.tsx",
    "screens/Campaigns.tsx",
    "screens/Demographics.tsx",
    "screens/Brief.tsx",
    "screens/Ads.tsx",
    "Business.tsx",
    "VoiceAssistant.tsx",
    "PresentMode.tsx",
    "ui.tsx",
  ]
  const contents = await Promise.all(files.map((file) => readFile(new URL(file, root), "utf8")))
  const combined = contents.join("\n")

  for (const claim of [
    'tone="live">Live',
    'tone="live">Live now',
    'verified="Edge video"',
    'verified="12 weeks measured"',
    'Verified on the edge device',
    'Edge video verified',
    'Live day view · Edge device online',
    'sales-linked',
    'Answers come from your live data',
    'I answer from your live data',
    'I know the live numbers',
    'all live',
    'Every stage is measured on the store\'s edge device',
    'verified 14-day A/B',
    'VERIFIED',
    'verified="Blur at the edge"',
    'verified="Attributed · 7-day window"',
    'Anonymised gender inference',
    'ENGINE-GENERATED',
    '>\n      VERIFIED\n',
  ]) {
    assert.equal(combined.includes(claim), false, `misleading sample-data claim remains: ${claim}`)
  }
})

test("marketing funnel illustration does not present fabricated store counts as measured facts", async () => {
  const page = await readFile(new URL("../src/site/BlindSpot.tsx", import.meta.url), "utf8")
  assert.equal(/metric:\s*"[\d,]+"/.test(page), false)
  assert.match(page, /Illustrative example|Illustration only/i)
})
