import type { TFunction } from 'i18next'

/** Messages emitted by src/core/pipeline.py and src/core/orchestrator.py over WebSocket */
const FIXED_MESSAGE_KEYS: Record<string, string> = {
  'Running DNS, WHOIS, Subdomains...': 'scan.progress.phase1',
  'Running SSL, Port, Tech...': 'scan.progress.phase2',
  'Running GeoIP, External APIs...': 'scan.progress.phase3',
  'Enrichment complete': 'scan.progress.enrichmentComplete',
  'Analyzing risks and correlations...': 'scan.progress.analyzingRisks',
  'Building scan summary...': 'scan.progress.buildingSummary',
}

const ENRICHER_LABEL_PREFIX = 'scan.progress.labels.' as const

export function translateScanProgressMessage(message: string, t: TFunction): string {
  const trimmed = message.trim()
  const fixedKey = FIXED_MESSAGE_KEYS[trimmed]
  if (fixedKey) return t(fixedKey)

  const completeMatch = /^([\w]+) complete$/.exec(trimmed)
  if (completeMatch) {
    const name = completeMatch[1]
    const labelKey = `${ENRICHER_LABEL_PREFIX}${name}`
    const label = t(labelKey)
    if (label === labelKey) return trimmed
    return t('scan.progress.enricherDone', { label })
  }

  if (trimmed.startsWith('Error: ')) {
    return t('scan.progress.errorWithDetail', { detail: trimmed.slice(7) })
  }

  return message
}
