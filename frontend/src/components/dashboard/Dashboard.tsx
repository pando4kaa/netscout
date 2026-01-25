import { Grid } from '@mui/material'
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

  return (
    <Grid container spacing={3}>
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
