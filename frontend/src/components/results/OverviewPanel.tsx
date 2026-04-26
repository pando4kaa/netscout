import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import { ScanResults } from '../../types'
import AlertsPanel from '../dashboard/AlertsPanel'
import HelpTooltip from '../common/HelpTooltip'

interface OverviewPanelProps {
  scanResults: ScanResults
}

const OverviewPanel = ({ scanResults }: OverviewPanelProps) => {
  const { dns_info = {}, whois_info = {}, subdomains = [], target_domain } = scanResults
  const riskBreakdown = scanResults.summary?.risk_breakdown || []
  const sortedRiskBreakdown = [...riskBreakdown].sort((a, b) => (b.contribution || 0) - (a.contribution || 0))
  const compositeScore = scanResults.summary?.risk_composite ?? scanResults.summary?.risk_score ?? 0

  // Calculate statistics
  const totalDnsRecords =
    (dns_info?.a_records?.length || 0) +
    (dns_info?.aaaa_records?.length || 0) +
    (dns_info?.mx_records?.length || 0) +
    (dns_info?.txt_records?.length || 0) +
    (dns_info?.ns_records?.length || 0) +
    (dns_info?.cname_records?.length || 0)

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
            <Typography variant="body2" color="text.secondary" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
              Subdomains
              <HelpTooltip topic="subdomains" size="small" />
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
              {dns_info?.a_records?.length || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
              IP Addresses
              <HelpTooltip topic="ip_addresses" size="small" />
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
            <Typography variant="body2" color="text.secondary" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
              DNS Records
              <HelpTooltip topic="dns" size="small" />
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
              {dns_info?.mx_records?.length || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
              Mail Servers
              <HelpTooltip topic="mx_records" size="small" />
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Risk Score */}
      {((scanResults.summary?.risk_score ?? 0) > 0 || (scanResults.summary?.risk_composite ?? 0) > 0) && (
        <Paper
          elevation={0}
          sx={{
            overflow: 'hidden',
            bgcolor: compositeScore >= 20 ? '#ffebee' : '#fff8e1',
            borderRadius: 2,
            borderLeft: 4,
            borderLeftColor: compositeScore >= 20 ? 'error.main' : 'warning.main',
          }}
        >
          <Box
            sx={{
              px: 2.25,
              py: 1.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 2,
              flexWrap: 'wrap',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="subtitle2" color="text.secondary" sx={{ fontWeight: 700, letterSpacing: 0.2 }}>
                Risk Score
              </Typography>
              <HelpTooltip topic="risk_score" />
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, ml: { sm: 'auto' } }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.8 }}>
                Composite
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: 800, lineHeight: 1 }}>
                {compositeScore.toFixed(2)}
              </Typography>
              <Tooltip
                arrow
                placement="top"
                title="Composite risk is calculated as S × w × L, where S is technical severity (CVSS when available), w is asset criticality, and L is exploitation likelihood."
              >
                <Chip
                  icon={<InfoOutlinedIcon sx={{ fontSize: 14 }} />}
                  label="S × w × L"
                  size="small"
                  variant="outlined"
                  sx={{
                    height: 24,
                    borderColor: 'warning.light',
                    bgcolor: 'rgba(255,255,255,0.55)',
                    '& .MuiChip-label': { px: 0.75, fontSize: '0.72rem', fontWeight: 700 },
                    '& .MuiChip-icon': { ml: 0.75 },
                  }}
                />
              </Tooltip>
            </Box>
          </Box>

          {sortedRiskBreakdown.length > 0 && (
            <Accordion
              disableGutters
              elevation={0}
              sx={{
                bgcolor: 'transparent',
                borderTop: '1px solid rgba(0,0,0,0.06)',
                '&:before': { display: 'none' },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{
                  minHeight: 42,
                  px: 2.25,
                  '& .MuiAccordionSummary-content': { my: 0.75, alignItems: 'center', gap: 1 },
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" sx={{ fontWeight: 700 }}>
                  View top risk contributors
                </Typography>
                <Chip
                  label={sortedRiskBreakdown.length}
                  size="small"
                  sx={{ height: 20, fontSize: '0.7rem', fontWeight: 700 }}
                />
              </AccordionSummary>
              <AccordionDetails sx={{ px: 2.25, pt: 0, pb: 1.5 }}>
                <List
                  dense
                  disablePadding
                  sx={{
                    maxHeight: 220,
                    overflowY: 'auto',
                    pr: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 1,
                  }}
                >
                  {sortedRiskBreakdown.map((item, index) => (
                    <ListItem
                      key={`${item.type}-${item.target || 'target'}-${index}`}
                      disableGutters
                      sx={{
                        alignItems: 'flex-start',
                        px: 1.25,
                        py: 1,
                        borderRadius: 1.5,
                        bgcolor: 'rgba(255,255,255,0.55)',
                      }}
                    >
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', gap: 0.75, alignItems: 'center' }}>
                            <Chip
                              label={item.level}
                              size="small"
                              color={item.level === 'HIGH' ? 'error' : item.level === 'MEDIUM' ? 'warning' : 'default'}
                              sx={{
                                height: 20,
                                fontSize: '0.65rem',
                                fontWeight: 700,
                                bgcolor: item.level === 'LOW' ? 'grey.200' : undefined,
                                color: item.level === 'LOW' ? 'text.secondary' : undefined,
                              }}
                            />
                            <Typography variant="body2" sx={{ fontWeight: 650, lineHeight: 1.35 }}>
                              {item.message}
                            </Typography>
                          </Box>
                        }
                        secondary={
                          <Typography component="span" variant="caption" color="text.secondary">
                            Contribution {item.contribution.toFixed(2)} = S {item.severity_score.toFixed(2)}
                            {item.severity_source === 'cvss' ? ' (CVSS)' : ''} × w {item.asset_weight.toFixed(2)} × L {item.likelihood.toFixed(2)}
                            {item.asset_class ? ` · ${item.asset_class}` : ''}
                          </Typography>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          )}
        </Paper>
      )}

      {/* SSL, Ports, Tech summary */}
      {(scanResults.ssl_info?.certificates?.length || scanResults.port_scan?.length || Object.keys(scanResults.tech_stack || {}).length) > 0 && (
        <Grid container spacing={3}>
          {scanResults.ssl_info?.certificates && scanResults.ssl_info.certificates.length > 0 && (
            <Grid item xs={12} sm={4}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  SSL Certificates
                  <HelpTooltip topic="ssl_certificates" size="small" />
                </Typography>
                <Typography variant="h5">{scanResults.ssl_info.certificates.length}</Typography>
              </Paper>
            </Grid>
          )}
          {scanResults.port_scan && scanResults.port_scan.length > 0 && (
            <Grid item xs={12} sm={4}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  Open Ports
                  <HelpTooltip topic="port_scan" size="small" />
                </Typography>
                <Typography variant="h5">
                  {scanResults.port_scan.reduce((sum, ps) => sum + (ps.open_ports?.length ?? 0), 0)}
                </Typography>
              </Paper>
            </Grid>
          )}
          {scanResults.tech_stack && Object.keys(scanResults.tech_stack).length > 0 && (
            <Grid item xs={12} sm={4}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  Tech Detected
                  <HelpTooltip topic="tech_stack" size="small" />
                </Typography>
                <Typography variant="h5">{Object.keys(scanResults.tech_stack).length} hosts</Typography>
              </Paper>
            </Grid>
          )}
        </Grid>
      )}

      {/* Quick Info */}
      <Grid container spacing={3}>
        {/* Domain Info */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                Domain Information
                <HelpTooltip topic="domain_info" />
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
                    secondary={whois_info?.registrar || 'N/A'}
                  />
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemText
                    primary="Created"
                    secondary={whois_info?.creation_date || 'N/A'}
                  />
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemText
                    primary="Expires"
                    secondary={whois_info?.expiration_date || 'N/A'}
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
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                IP Addresses
                <HelpTooltip topic="ip_addresses" />
              </Typography>
              {dns_info?.a_records && dns_info.a_records.length > 0 ? (
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

              {dns_info?.aaaa_records && dns_info.aaaa_records.length > 0 && (
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
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                Name Servers
                <HelpTooltip topic="name_servers" />
              </Typography>
              {dns_info?.ns_records && dns_info.ns_records.length > 0 ? (
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
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                Mail Servers (MX)
                <HelpTooltip topic="mx_records" />
              </Typography>
              {dns_info?.mx_records && dns_info.mx_records.length > 0 ? (
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

      {/* Correlation (IP → Subdomains, PTR) */}
      {scanResults.correlation && (scanResults.correlation.ip_to_subdomains && Object.keys(scanResults.correlation.ip_to_subdomains).length > 0 || scanResults.correlation.ptr_records && Object.keys(scanResults.correlation.ptr_records).length > 0 || (scanResults.correlation.shared_certificate_hosts?.length ?? 0) > 0) && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              Correlation
              <HelpTooltip topic="correlation" />
            </Typography>
            <Grid container spacing={2}>
              {scanResults.correlation.ip_to_subdomains && Object.keys(scanResults.correlation.ip_to_subdomains).length > 0 && (
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" color="text.secondary">IP → Subdomains</Typography>
                  <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {Object.entries(scanResults.correlation.ip_to_subdomains).slice(0, 10).map(([ip, subs]) => (
                      <Box key={ip}>
                        <Chip label={ip} size="small" sx={{ fontFamily: 'monospace', mb: 0.5 }} />
                        <Typography variant="caption" display="block" sx={{ ml: 1 }}>
                          {subs.slice(0, 5).join(', ')}{subs.length > 5 ? ` +${subs.length - 5}` : ''}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Grid>
              )}
              {scanResults.correlation.ptr_records && Object.keys(scanResults.correlation.ptr_records).length > 0 && (
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" color="text.secondary">Reverse DNS (PTR)</Typography>
                  <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {Object.entries(scanResults.correlation.ptr_records).map(([ip, host]) => (
                      <Chip
                        key={ip}
                        label={`${ip} → ${host}`}
                        size="small"
                        variant="outlined"
                        sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                      />
                    ))}
                  </Box>
                </Grid>
              )}
              {(scanResults.correlation.shared_certificate_hosts?.length ?? 0) > 0 && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2" color="text.secondary">Shared SSL certificates</Typography>
                  <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {scanResults.correlation.shared_certificate_hosts?.slice(0, 5).map((group, index) => (
                      <Box key={`${group.certificate_key}-${index}`}>
                        <Chip
                          label={`${group.hosts.length} related hosts`}
                          size="small"
                          color="info"
                          sx={{ mb: 0.5 }}
                        />
                        <Typography variant="caption" display="block" sx={{ ml: 1, fontFamily: 'monospace' }}>
                          {group.hosts.slice(0, 8).join(', ')}{group.hosts.length > 8 ? ` +${group.hosts.length - 8}` : ''}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Grid>
              )}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Alerts */}
      {(scanResults.alerts?.length ?? 0) > 0 && (
        <AlertsPanel scanResults={scanResults} />
      )}

      {/* Top Subdomains Preview */}
      {subdomains && subdomains.length > 0 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                Subdomains Preview
                <HelpTooltip topic="subdomains_preview" />
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
