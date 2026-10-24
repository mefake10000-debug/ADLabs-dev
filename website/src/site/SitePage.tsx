"use client"

import { useState } from "react"
import { Nav } from "./Nav"
import { Hero } from "./Hero"
import { Demo } from "./Demo"
import { Sensor } from "./Sensor"
import { BlindSpot } from "./BlindSpot"
import { Journey } from "./Journey"
import { Pillars } from "./Pillars"
import { Atelier } from "./Atelier"
import { Proof } from "./Proof"
import { System } from "./System"
import { Metrics } from "./Metrics"
import { Sectors } from "./Sectors"
import { Flow } from "./Flow"
import { Privacy } from "./Privacy"
import { WhyUs } from "./WhyUs"
import { Mission } from "./Mission"
import { Team } from "./Team"
import { How } from "./How"
import { Pricing } from "./Pricing"
import { Faq } from "./Faq"
import { Contact } from "./Contact"
import { Footer } from "./Footer"
import { PilotModal } from "./PilotModal"

export function SitePage() {
  const [pilot, setPilot] = useState(false)
  const openPilot = () => setPilot(true)

  return (
    <div className="site-scope min-h-screen text-[var(--ds-text-primary)] page-in" style={{ background: "var(--ds-bg-primary)" }}>
      <Nav onPilot={openPilot} />
      <main className="overflow-x-hidden">
        {/* HOOK: The Problem */}
        <Hero onPilot={openPilot} />

        <BlindSpot />

        {/* MESSAGE: The Solution */}
        <Sensor />

        {/* PROOF: The Story */}
        <Demo />

        {/* EVIDENCE: The Data */}
        <Journey />
        <Pillars />
        <Atelier />
        <Proof />
        <System />
        <Metrics />

        {/* HOW IT WORKS */}
        <Flow />
        <Privacy />

        {/* WHO IT IS FOR */}
        <WhyUs />
        <Sectors />

        {/* THE TEAM */}
        <Mission />
        <Team />

        {/* ACTION */}
        <How onPilot={openPilot} />
        <Pricing />
        <Faq />
        <Contact onPilot={openPilot} />
      </main>
      <Footer />
      <PilotModal open={pilot} onClose={() => setPilot(false)} />
    </div>
  )
}
