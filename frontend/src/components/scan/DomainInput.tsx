import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TextField, Button, Box, Alert } from '@mui/material'
import { scanApi } from '../../services/api'
import { useScanStore } from '../../store/useScanStore'
import { ScanResults } from '../../types'

const DomainInput = () => {
  const [domain, setDomain] = useState('')
  const [isScanning, setIsScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const { setCurrentScan, addToHistory } = useScanStore()

  const handleScan = async () => {
    if (!domain.trim()) {
      setError('Please enter a domain')
      return
    }

    setIsScanning(true)
    setError(null)

    try {
      const result = await scanApi.startScan(domain)
      if (result.success && result.results) {
        // Store results
        const scanResults: ScanResults = {
          ...result.results,
          scan_date: new Date().toISOString(),
        }
        setCurrentScan(scanResults)
        addToHistory(scanResults)
        
        // Navigate to scan results page
        navigate('/scan')
      } else {
        setError(result.error || 'Scan failed')
      }
    } catch (err) {
      setError('Failed to start scan. Make sure backend is running.')
      console.error(err)
    } finally {
      setIsScanning(false)
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 600 }}>
      <TextField
        label="Domain"
        value={domain}
        onChange={(e) => setDomain(e.target.value)}
        onKeyPress={(e) => {
          if (e.key === 'Enter' && !isScanning && domain.trim()) {
            handleScan()
          }
        }}
        disabled={isScanning}
        placeholder="example.com"
        fullWidth
      />
      {error && <Alert severity="error">{error}</Alert>}
      <Button
        variant="contained"
        onClick={handleScan}
        disabled={isScanning || !domain.trim()}
        sx={{ alignSelf: 'flex-start' }}
      >
        {isScanning ? 'Scanning...' : 'Start Scan'}
      </Button>
    </Box>
  )
}

export default DomainInput
