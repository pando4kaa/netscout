import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TextField, Button, Box, Alert, LinearProgress } from '@mui/material'
import { runScanViaWebSocket } from '../../services/websocket'
import { useScanStore } from '../../store/useScanStore'
import { useAuth } from '../../contexts/AuthContext'
import { ScanResults } from '../../types'
import { isValidDomain, normalizeDomain } from '../../utils/domainValidator'

const DomainInput = () => {
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
      setError('Please enter a valid domain')
      return
    }

    const normalized = normalizeDomain(domain)
    setIsScanning(true)
    setError(null)
    setProgress(0)
    setProgressMessage('Connecting...')

    const cancel = runScanViaWebSocket(normalized, {
      onProgress: (p, msg) => {
        setProgress(p)
        setProgressMessage(msg)
      },
      onDone: (scanId, results) => {
        const scanResults: ScanResults = {
          ...results,
          scan_id: scanId,
          scan_date: new Date().toISOString(),
        }
        setCurrentScan(scanResults)
        addToHistory(scanResults)
        setIsScanning(false)
        setProgress(100)
        navigate('/scan')
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
          You can scan without signing in, but results won&apos;t be saved to history. Sign in to save scans and schedule recurring scans.
        </Alert>
      )}
      <TextField
        label="Domain"
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
        {isScanning ? 'Scanning...' : 'Start Scan'}
      </Button>
    </Box>
  )
}

export default DomainInput
