import { BRAND } from "../data/site"

/**
 * Builds a mailto: link that composes an email from form data and opens it
 * in the visitor's email client. Real submission with no backend — works on
 * any static host. Keeps a plain-text readable layout in the body.
 */
export function composeMailto(
  subject: string,
  fields: { label: string; value: string | undefined }[],
): string {
  const lines = fields
    .filter((f) => f.value && f.value.trim().length > 0)
    .map((f) => `${f.label}: ${f.value}`)
    .join("\n")

  const body = `Hi AdLabs team,\n\n${lines}\n\n`
  const params = new URLSearchParams({
    subject,
    body,
  })
  return `mailto:${BRAND.email}?${params.toString()}`
}

/** Opens a composed email in the visitor's mail client. Returns a truthy state. */
export function submitViaEmail(subject: string, fields: { label: string; value: string | undefined }[]): boolean {
  const href = composeMailto(subject, fields)
  window.location.href = href
  return true
}
