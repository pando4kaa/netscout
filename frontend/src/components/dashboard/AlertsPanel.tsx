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
