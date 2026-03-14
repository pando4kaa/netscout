/**
 * Domain validation utilities (mirrors backend src/utils/validators.py).
 */

const DOMAIN_PATTERN = /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/

/**
 * Normalizes domain: removes protocol, www, path, port.
 */
export function normalizeDomain(input: string): string {
  if (!input?.trim()) return ''
  let domain = input.trim()
  domain = domain.replace(/^https?:\/\//, '')
  domain = domain.replace(/^www\./, '')
  domain = domain.split('/')[0]
  domain = domain.split(':')[0]
  return domain.toLowerCase().trim()
}

/**
 * Checks if input looks like a valid domain (after normalization).
 */
export function isValidDomain(input: string): boolean {
  if (!input?.trim() || input.length > 253) return false
  const domain = normalizeDomain(input)
  if (!domain) return false
  if (!DOMAIN_PATTERN.test(domain)) return false
  if (domain.includes('..')) return false
  return true
}
