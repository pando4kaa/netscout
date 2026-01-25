import { useState } from 'react'
import { Container, Box } from '@mui/material'
import Dashboard from '../components/dashboard/Dashboard'
import GraphView from '../components/graph/GraphView'
import GraphControls from '../components/graph/GraphControls'
import { ScanResults } from '../types'

const ScanPage = () => {
  const [scanResults, setScanResults] = useState<ScanResults | null>(null)
  const [cyInstance, setCyInstance] = useState<any>(null)

  // TODO: Load scan results from API or store

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 2 }}>
        <Dashboard scanResults={scanResults} />
        <Box sx={{ mt: 4 }}>
          <GraphControls cy={cyInstance} />
          <GraphView data={scanResults} />
        </Box>
      </Box>
    </Container>
  )
}

export default ScanPage
