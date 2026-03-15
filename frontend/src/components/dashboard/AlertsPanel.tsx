import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  Chip,
} from '@mui/material'
import WarningIcon from '@mui/icons-material/Warning'
import { Alert, ScanResults } from '../../types'
import HelpTooltip from '../common/HelpTooltip'

interface AlertsPanelProps {
  scanResults: ScanResults
}

const levelColor = (level: string) => {
  switch (level) {
    case 'HIGH':
      return 'error'
    case 'MEDIUM':
      return 'warning'
    case 'LOW':
      return 'info'
    default:
      return 'default'
  }
}

const AlertsPanel = ({ scanResults }: AlertsPanelProps) => {
  const alerts: Alert[] = scanResults.alerts || []

  if (alerts.length === 0) {
    return null
  }

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <WarningIcon color="warning" />
          <Typography variant="h6">Security Alerts ({alerts.length})</Typography>
          <HelpTooltip topic="security_alerts" />
        </Box>
        <List dense>
          {alerts.map((alert, idx) => (
            <ListItem key={idx} sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                <Chip
                  label={alert.level}
                  color={levelColor(alert.level) as any}
                  size="small"
                />
                {['subdomain_takeover', 'ssl_expired', 'expired_ssl', 'open_port', 'outdated_tech'].includes(alert.type) && (
                  <HelpTooltip
                    topic={alert.type === 'expired_ssl' ? 'ssl_expired' : alert.type as 'subdomain_takeover' | 'ssl_expired' | 'open_port' | 'outdated_tech'}
                    size="small"
                  />
                )}
                {alert.target && (
                  <Typography variant="caption" color="text.secondary">
                    {alert.target}
                  </Typography>
                )}
              </Box>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {alert.message}
              </Typography>
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  )
}

export default AlertsPanel
