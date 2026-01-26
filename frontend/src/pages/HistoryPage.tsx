import { Container, Typography, Box } from '@mui/material'
import DataTable from '../components/common/DataTable'

const HistoryPage = () => {
  // TODO: Load history from API
  const columns = [
    { id: 'domain', label: 'Domain' },
    { id: 'date', label: 'Date' },
    { id: 'subdomains', label: 'Subdomains' },
    { id: 'status', label: 'Status' },
  ]

  const rows: any[] = [] // TODO: Load from API

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
          Scan History
        </Typography>
        {rows.length > 0 ? (
          <DataTable columns={columns} rows={rows} />
        ) : (
          <Box sx={{ 
            textAlign: 'center', 
            py: 8,
            bgcolor: 'background.paper',
            borderRadius: 2,
            border: '1px dashed',
            borderColor: 'divider',
          }}>
            <Typography variant="body1" color="text.secondary" sx={{ fontSize: '1.1rem' }}>
              No scan history available
            </Typography>
          </Box>
        )}
      </Box>
    </Container>
  )
}

export default HistoryPage
