import { useState, useEffect } from 'react'
import { Container, Box, Typography, Alert } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import Dashboard from '../components/dashboard/Dashboard'
import GraphView from '../components/graph/GraphView'
import GraphControls from '../components/graph/GraphControls'
import { useScanStore } from '../store/useScanStore'

const ScanPage = () => {
  const [cyInstance, setCyInstance] = useState<any>(null)
  const { currentScan } = useScanStore()
  const navigate = useNavigate()

  useEffect(() => {
    // Redirect to home if no scan results
    if (!currentScan) {
      navigate('/')
    }
  }, [currentScan, navigate])

  if (!currentScan) {
    return (
      <Container maxWidth="xl">
        <Box sx={{ py: 4 }}>
          <Alert severity="info">
            No scan results available. Please start a scan from the home page.
          </Alert>
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
          Scan Results: {currentScan.target_domain}
        </Typography>
        <Dashboard scanResults={currentScan} />
        <Box sx={{ mt: 5 }}>
          <GraphControls cy={cyInstance} />
          <Box sx={{ mt: 2 }}>
            <GraphView data={currentScan} setCyInstance={setCyInstance} />
          </Box>
        </Box>
      </Box>
    </Container>
  )
}

export default ScanPage
