import { Grid, Card, CardContent, Typography } from '@mui/material'
import { ScanResults } from '../../types'

interface StatsCardsProps {
  scanResults: ScanResults
}

const StatsCards = ({ scanResults }: StatsCardsProps) => {
  const stats = [
    {
      title: 'Subdomains',
      value: scanResults.subdomains?.length || 0,
      color: '#2e7d32',
    },
    {
      title: 'IP Addresses',
      value: scanResults.dns_info?.a_records?.length || 0,
      color: '#ed6c02',
    },
    {
      title: 'MX Records',
      value: scanResults.dns_info?.mx_records?.length || 0,
      color: '#1976d2',
    },
    {
      title: 'Risk Score',
      value: 'N/A', // TODO: Calculate risk score
      color: '#d32f2f',
    },
  ]

  return (
    <Grid container spacing={3}>
      {stats.map((stat) => (
        <Grid item xs={12} sm={6} md={3} key={stat.title}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                {stat.title}
              </Typography>
              <Typography variant="h4" component="div" sx={{ color: stat.color }}>
                {stat.value}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  )
}

export default StatsCards
