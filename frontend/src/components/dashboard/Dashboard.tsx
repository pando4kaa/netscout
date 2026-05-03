import { Grid, Alert } from '@mui/material'
import { useTranslation } from 'react-i18next'
import StatsCards from './StatsCards'
import SummaryTable from './SummaryTable'
import AlertsPanel from './AlertsPanel'
import { ScanResults } from '../../types'

interface DashboardProps {
  scanResults: ScanResults | null
}

const Dashboard = ({ scanResults }: DashboardProps) => {
  const { t } = useTranslation()
  if (!scanResults) {
    return <div>{t('results.noScanResultsAvailable')}</div>
  }

  const hasErrors = 
    (scanResults.dns_info?.error) || 
    (scanResults.whois_info?.error)

  return (
    <Grid container spacing={3}>
      {hasErrors && (
        <Grid item xs={12}>
          <Alert severity="warning">
            {t('results.modulesPartialWarning')}
            {scanResults.dns_info?.error &&
              ` ${t('scan.progress.labels.dns')}: ${scanResults.dns_info.error}`}
            {scanResults.whois_info?.error &&
              ` ${t('scan.progress.labels.whois')}: ${scanResults.whois_info.error}`}
          </Alert>
        </Grid>
      )}
      <Grid item xs={12}>
        <StatsCards scanResults={scanResults} />
      </Grid>
      <Grid item xs={12}>
        <SummaryTable scanResults={scanResults} />
      </Grid>
      {(scanResults.alerts?.length ?? 0) > 0 && (
        <Grid item xs={12}>
          <AlertsPanel scanResults={scanResults} />
        </Grid>
      )}
    </Grid>
  )
}

export default Dashboard
