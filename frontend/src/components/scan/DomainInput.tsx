import { useState } from 'react'
import { TextField, Button, Box, Alert } from '@mui/material'
import { scanApi } from '../../services/api'

const DomainInput = () => {
  const [domain, setDomain] = useState('')
  const [isScanning, setIsScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleScan = async () => {
    if (!domain.trim()) {
      setError('Please enter a domain')
      return
    }

    setIsScanning(true)
    setError(null)

    try {
      const result = await scanApi.startScan(domain)
      if (result.success) {
        // TODO: Handle successful scan
        console.log('Scan started:', result)
      } else {
        setError(result.error || 'Scan failed')
      }
    } catch (err) {
      setError('Failed to start scan')
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
