import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TextField, Button, Box, Alert, LinearProgress } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { translateScanProgressMessage } from '../../i18n/scanProgress'
import { runScanViaWebSocket } from '../../services/websocket'
import { useScanStore } from '../../store/useScanStore'
import { useAuth } from '../../contexts/AuthContext'
import { ScanResults } from '../../types'
import { isValidDomain, normalizeDomain } from '../../utils/domainValidator'

const DomainInput = () => {
  const { t } = useTranslation()
  const [domain, setDomain] = useState('')
  const [isScanning, setIsScanning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const { setCurrentScan, addToHistory } = useScanStore()
  const { token, isAuthenticated } = useAuth()

  const validDomain = isValidDomain(domain)

  const handleScan = () => {
    if (!validDomain) {
      setError(t('validation.validDomain'))
      return
    }

    const normalized = normalizeDomain(domain)
    setIsScanning(true)
    setError(null)
    setProgress(0)
    setProgressMessage(t('scan.connecting'))

    const cancel = runScanViaWebSocket(normalized, {
      onProgress: (p, msg) => {
        setProgress(p)
        setProgressMessage(translateScanProgressMessage(msg, t))
      },
      onDone: (scanId, results) => {
        try {
          const resultDomain =
            typeof results?.target_domain === 'string' ? results.target_domain : normalized
          const scanResults: ScanResults = {
            target_domain: resultDomain,
            subdomains: Array.isArray(results?.subdomains) ? results.subdomains : [],
            ...results,
            scan_id: scanId,
            scan_date: new Date().toISOString(),
          }
          setCurrentScan(scanResults)
          addToHistory(scanResults)
          setIsScanning(false)
          setProgress(100)
          navigate('/scan')
        } catch (e) {
          setError(e instanceof Error ? e.message : t('scan.processingResultsError'))
          setIsScanning(false)
        }
      },
      onError: (err) => {
        setError(err)
        setIsScanning(false)
      },
    }, token)

    return cancel
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 600 }}>
      {!isAuthenticated && (
        <Alert severity="info" sx={{ mb: 1 }}>
          {t('scan.anonymousNotice')}
        </Alert>
      )}
      <TextField
        label={t('common.domain')}
        value={domain}
        onChange={(e) => setDomain(e.target.value)}
        onKeyPress={(e) => {
          if (e.key === 'Enter' && !isScanning && validDomain) {
            handleScan()
          }
        }}
        disabled={isScanning}
        placeholder="example.com"
        fullWidth
      />
      {isScanning && (
        <Box>
          <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 1 }} />
          <Box sx={{ mt: 1 }}>
            <small style={{ color: 'var(--mui-palette-text-secondary)' }}>{progressMessage}</small>
          </Box>
        </Box>
      )}
      {error && <Alert severity="error">{error}</Alert>}
      <Button
        variant="contained"
        onClick={handleScan}
        disabled={isScanning || !validDomain}
        sx={{ alignSelf: 'flex-start' }}
      >
        {isScanning ? t('scan.scanning') : t('scan.start')}
      </Button>
    </Box>
  )
}

export default DomainInput
