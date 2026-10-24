import type { Metadata } from "next"
import "@fontsource-variable/inter"
import "../src/index.css"

// oxlint-disable-next-line react/only-export-components
export const metadata: Metadata = {
  metadataBase: new URL("https://adlabs.in"),
  title: "AD Labs — Intelligence for the storefront",
  description:
    "AD Labs puts a sensor in every retail store: real-time consumer intelligence for offline retail — who passed, who paused, who entered, and why windows work.",
  openGraph: {
    title: "AD Labs — Intelligence for the storefront",
    description:
      "Physical retail is the world's largest market and the least measured. AD Labs turns the cameras you already own into a live brain for your store.",
    url: "https://adlabs.in",
    images: ["/images/hero-storefront.jpg"],
    type: "website",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <head>
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
      </head>
      <body className="bg-[#05050a] text-[#f5f5f7] antialiased selection:bg-[#8B7CF6] selection:text-[#05050a]">
        {children}
      </body>
    </html>
  )
}
