import { Grid, Card, CardContent, Typography, Box } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { ScanResults } from '../../types'
import HelpTooltip from '../common/HelpTooltip'

interface StatsCardsProps {
  scanResults: ScanResults
}

const StatsCards = ({ scanResults }: StatsCardsProps) => {
  const { t } = useTranslation()
  const riskScore = scanResults.summary?.risk_score ?? 0
  const stats = [
    {
      title: t('common.subdomains'),
      value: scanResults.subdomains?.length || 0,
      color: '#2e7d32',
      topic: 'subdomains' as const,
    },
    {
      title: t('results.ipAddresses'),
      value: scanResults.dns_info?.a_records?.length || 0,
      color: '#ed6c02',
      topic: 'ip_addresses' as const,
    },
    {
      title: t('results.mxRecordsShort'),
      value: scanResults.dns_info?.mx_records?.length || 0,
      color: '#1976d2',
      topic: 'mx_records' as const,
    },
    {
      title: t('common.alerts'),
      value: scanResults.summary?.total_alerts ?? scanResults.alerts?.length ?? 0,
      color: '#d32f2f',
      topic: 'security_alerts' as const,
    },
    {
      title: t('results.riskScoreShort'),
      value: riskScore,
      color: riskScore >= 20 ? '#d32f2f' : riskScore >= 10 ? '#ed6c02' : '#2e7d32',
      topic: 'risk_score' as const,
    },
  ]

  return (
    <Grid container spacing={3}>
      {stats.map((stat) => (
        <Grid item xs={12} sm={6} md={4} lg={2} key={stat.topic}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                <Typography color="text.secondary">
                  {stat.title}
                </Typography>
                <HelpTooltip topic={stat.topic} size="small" />
              </Box>
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
