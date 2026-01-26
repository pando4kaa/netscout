import { Grid, Alert } from '@mui/material'
import StatsCards from './StatsCards'
import SummaryTable from './SummaryTable'
import { ScanResults } from '../../types'

interface DashboardProps {
  scanResults: ScanResults | null
}

const Dashboard = ({ scanResults }: DashboardProps) => {
  if (!scanResults) {
    return <div>No scan results available</div>
  }

  const hasErrors = 
    (scanResults.dns_info?.error) || 
    (scanResults.whois_info?.error)

  return (
    <Grid container spacing={3}>
      {hasErrors && (
        <Grid item xs={12}>
          <Alert severity="warning">
            Some modules encountered errors during scanning. Results may be incomplete.
            {scanResults.dns_info?.error && ` DNS: ${scanResults.dns_info.error}`}
            {scanResults.whois_info?.error && ` WHOIS: ${scanResults.whois_info.error}`}
          </Alert>
        </Grid>
      )}
      <Grid item xs={12}>
        <StatsCards scanResults={scanResults} />
      </Grid>
      <Grid item xs={12}>
        <SummaryTable scanResults={scanResults} />
      </Grid>
    </Grid>
  )
}

export default Dashboard
