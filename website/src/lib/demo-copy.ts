/** Make fixture-backed assistant answers unmistakable as examples, not live measurements. */
export function formatDemoAnswer(text: string): string {
  return `Sample data — not a live camera measurement. ${text}`
}
