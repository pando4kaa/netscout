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
      <Box sx={{ py: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Scan History
        </Typography>
        {rows.length > 0 ? (
          <DataTable columns={columns} rows={rows} />
        ) : (
          <Typography variant="body1" color="text.secondary">
            No scan history available
          </Typography>
        )}
      </Box>
    </Container>
  )
}

export default HistoryPage
