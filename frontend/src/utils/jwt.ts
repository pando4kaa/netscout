/**
 * Decode JWT payload (no signature verification — for UX expiry check only).
 */

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split('.')
  if (parts.length !== 3) return null
  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const pad = (4 - (base64.length % 4)) % 4
    const padded = base64 + '='.repeat(pad)
    const json = atob(padded)
    return JSON.parse(json) as Record<string, unknown>
  } catch {
    return null
  }
}

/** True if token is missing, malformed, has no exp, or exp is in the past (with small clock skew). */
export function isJwtExpired(token: string, skewSeconds = 60): boolean {
  const payload = decodeJwtPayload(token)
  if (!payload || typeof payload.exp !== 'number') return true
  const now = Math.floor(Date.now() / 1000)
  return payload.exp <= now + skewSeconds
}
