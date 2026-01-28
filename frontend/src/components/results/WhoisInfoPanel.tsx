import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Paper,
  Divider,
} from '@mui/material'
import { WhoisInfo } from '../../types'

interface WhoisInfoPanelProps {
  whoisInfo: WhoisInfo
}

const WhoisInfoPanel = ({ whoisInfo }: WhoisInfoPanelProps) => {
  if (whoisInfo.error) {
    return (
      <Card>
        <CardContent>
          <Typography color="error">WHOIS Error: {whoisInfo.error}</Typography>
        </CardContent>
      </Card>
    )
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'N/A'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('uk-UA', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  const calculateDaysUntilExpiry = (expiryDate: string | null | undefined) => {
    if (!expiryDate) return null
    try {
      const expiry = new Date(expiryDate)
      const now = new Date()
      const diffTime = expiry.getTime() - now.getTime()
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      return diffDays
    } catch {
      return null
    }
  }

  const daysUntilExpiry = calculateDaysUntilExpiry(whoisInfo.expiration_date)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Main Info */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Registration Information
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Registrar
                </Typography>
                <Typography variant="body1" sx={{ mt: 0.5 }}>
                  {whoisInfo.registrar || 'N/A'}
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Status
                </Typography>
                <Typography variant="body1" sx={{ mt: 0.5 }}>
                  {whoisInfo.status || 'N/A'}
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Dates */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Important Dates
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'success.light', color: 'success.contrastText' }}>
                <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                  Created
                </Typography>
                <Typography variant="h6" sx={{ mt: 0.5 }}>
                  {formatDate(whoisInfo.creation_date)}
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  bgcolor: daysUntilExpiry && daysUntilExpiry < 30 ? 'error.light' : 'warning.light',
                  color: daysUntilExpiry && daysUntilExpiry < 30 ? 'error.contrastText' : 'warning.contrastText',
                }}
              >
                <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                  Expires
                </Typography>
                <Typography variant="h6" sx={{ mt: 0.5 }}>
                  {formatDate(whoisInfo.expiration_date)}
                </Typography>
                {daysUntilExpiry !== null && (
                  <Typography variant="caption" sx={{ opacity: 0.9 }}>
                    {daysUntilExpiry > 0 ? `${daysUntilExpiry} days left` : 'Expired!'}
                  </Typography>
                )}
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
                <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                  Domain Age
                </Typography>
                <Typography variant="h6" sx={{ mt: 0.5 }}>
                  {whoisInfo.creation_date
                    ? `${Math.floor(
                        (new Date().getTime() - new Date(whoisInfo.creation_date).getTime()) /
                          (1000 * 60 * 60 * 24 * 365)
                      )} years`
                    : 'N/A'}
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Name Servers */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            Name Servers
            <Chip label={whoisInfo.name_servers?.length || 0} size="small" color="primary" />
          </Typography>
          {whoisInfo.name_servers && whoisInfo.name_servers.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {whoisInfo.name_servers.map((ns, index) => (
                <Chip key={index} label={ns} variant="outlined" color="primary" />
              ))}
            </Box>
          ) : (
            <Typography color="text.secondary">No name servers found</Typography>
          )}
        </CardContent>
      </Card>

      {/* Contact Emails */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            Contact Emails
            <Chip label={whoisInfo.emails?.length || 0} size="small" color="secondary" />
          </Typography>
          {whoisInfo.emails && whoisInfo.emails.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {whoisInfo.emails.map((email, index) => (
                <Chip
                  key={index}
                  label={email}
                  variant="outlined"
                  color="secondary"
                  component="a"
                  href={`mailto:${email}`}
                  clickable
                />
              ))}
            </Box>
          ) : (
            <Typography color="text.secondary">No emails found (possibly hidden by privacy protection)</Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}

export default WhoisInfoPanel
