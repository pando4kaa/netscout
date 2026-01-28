import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material'
import { ScanResults } from '../../types'

interface OverviewPanelProps {
  scanResults: ScanResults
}

const OverviewPanel = ({ scanResults }: OverviewPanelProps) => {
  const { dns_info, whois_info, subdomains, target_domain, scan_date } = scanResults

  // Calculate statistics
  const totalDnsRecords =
    (dns_info.a_records?.length || 0) +
    (dns_info.aaaa_records?.length || 0) +
    (dns_info.mx_records?.length || 0) +
    (dns_info.txt_records?.length || 0) +
    (dns_info.ns_records?.length || 0) +
    (dns_info.cname_records?.length || 0)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Main Stats */}
      <Grid container spacing={3}>
        <Grid item xs={6} sm={3}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              textAlign: 'center',
              bgcolor: '#e3f2fd',
              borderRadius: 2,
            }}
          >
            <Typography variant="h3" color="primary" sx={{ fontWeight: 700 }}>
              {subdomains?.length || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Subdomains
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              textAlign: 'center',
              bgcolor: '#fff3e0',
              borderRadius: 2,
            }}
          >
            <Typography variant="h3" color="warning.dark" sx={{ fontWeight: 700 }}>
              {dns_info.a_records?.length || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              IP Addresses
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              textAlign: 'center',
              bgcolor: '#e8f5e9',
              borderRadius: 2,
            }}
          >
            <Typography variant="h3" color="success.dark" sx={{ fontWeight: 700 }}>
              {totalDnsRecords}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              DNS Records
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              textAlign: 'center',
              bgcolor: '#fce4ec',
              borderRadius: 2,
            }}
          >
            <Typography variant="h3" color="error.dark" sx={{ fontWeight: 700 }}>
              {dns_info.mx_records?.length || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Mail Servers
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Quick Info */}
      <Grid container spacing={3}>
        {/* Domain Info */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Domain Information
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Domain"
                    secondary={target_domain}
                    secondaryTypographyProps={{ fontFamily: 'monospace', fontWeight: 600 }}
                  />
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemText
                    primary="Registrar"
                    secondary={whois_info.registrar || 'N/A'}
                  />
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemText
                    primary="Created"
                    secondary={whois_info.creation_date || 'N/A'}
                  />
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemText
                    primary="Expires"
                    secondary={whois_info.expiration_date || 'N/A'}
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* IP Addresses */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                IP Addresses
              </Typography>
              {dns_info.a_records && dns_info.a_records.length > 0 ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {dns_info.a_records.map((ip, index) => (
                    <Chip
                      key={index}
                      label={ip}
                      color="primary"
                      variant="outlined"
                      sx={{ fontFamily: 'monospace' }}
                    />
                  ))}
                </Box>
              ) : (
                <Typography color="text.secondary">No IP addresses found</Typography>
              )}

              {dns_info.aaaa_records && dns_info.aaaa_records.length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                    IPv6
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {dns_info.aaaa_records.map((ip, index) => (
                      <Chip
                        key={index}
                        label={ip}
                        color="secondary"
                        variant="outlined"
                        size="small"
                        sx={{ fontFamily: 'monospace', maxWidth: '100%' }}
                      />
                    ))}
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Name Servers & Mail Servers */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Name Servers
              </Typography>
              {dns_info.ns_records && dns_info.ns_records.length > 0 ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {dns_info.ns_records.map((ns, index) => (
                    <Chip key={index} label={ns} variant="outlined" />
                  ))}
                </Box>
              ) : (
                <Typography color="text.secondary">No name servers found</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Mail Servers (MX)
              </Typography>
              {dns_info.mx_records && dns_info.mx_records.length > 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {dns_info.mx_records.map((mx, index) => (
                    <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip label={`P${mx.priority}`} size="small" color="info" />
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {mx.host}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography color="text.secondary">No mail servers found</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Top Subdomains Preview */}
      {subdomains && subdomains.length > 0 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Subdomains Preview
              </Typography>
              <Chip label={`${subdomains.length} total`} color="primary" size="small" />
            </Box>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {subdomains.slice(0, 20).map((sub, index) => (
                <Chip
                  key={index}
                  label={sub}
                  variant="outlined"
                  size="small"
                  sx={{ fontFamily: 'monospace' }}
                />
              ))}
              {subdomains.length > 20 && (
                <Chip
                  label={`+${subdomains.length - 20} more`}
                  color="default"
                  size="small"
                />
              )}
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}

export default OverviewPanel
