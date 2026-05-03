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
import { useTranslation } from 'react-i18next'
import { ScanResults } from '../../types'
import AlertsPanel from '../dashboard/AlertsPanel'
import HelpTooltip from '../common/HelpTooltip'

interface OverviewPanelProps {
  scanResults: ScanResults
}

const OverviewPanel = ({ scanResults }: OverviewPanelProps) => {
  const { t } = useTranslation()
  const { dns_info = {}, whois_info = {}, subdomains = [], target_domain } = scanResults
  const riskBreakdown = scanResults.summary?.risk_breakdown || []
  const sortedRiskBreakdown = [...riskBreakdown].sort((a, b) => (b.contribution || 0) - (a.contribution || 0))
  const riskGroups = scanResults.summary?.risk_groups || []
  const sortedRiskGroups = [...riskGroups].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0))
  const v3Score = scanResults.summary?.risk_overall
  const compositeScore = scanResults.summary?.risk_composite ?? scanResults.summary?.risk_score ?? 0
  const displayRiskScore = v3Score ?? compositeScore
  const displayRiskLevel = scanResults.summary?.risk_level || (displayRiskScore >= 75 ? 'CRITICAL' : displayRiskScore >= 50 ? 'HIGH' : displayRiskScore >= 25 ? 'MEDIUM' : 'LOW')
  const hasV3Risk = v3Score !== null && v3Score !== undefined && sortedRiskGroups.length > 0
  const riskColor = displayRiskLevel === 'CRITICAL' || displayRiskLevel === 'HIGH' ? 'error' : displayRiskLevel === 'MEDIUM' ? 'warning' : 'success'

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
              {t('common.subdomains')}
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
              {t('results.ipAddresses')}
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
              {t('results.dnsRecords')}
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
              {t('results.mailServers')}
              <HelpTooltip topic="mx_records" size="small" />
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Risk Score */}
      {((scanResults.summary?.risk_score ?? 0) > 0 || (scanResults.summary?.risk_composite ?? 0) > 0 || (scanResults.summary?.risk_overall ?? 0) > 0) && (
        <Paper
          elevation={0}
          sx={{
            overflow: 'hidden',
            bgcolor: riskColor === 'error' ? '#ffebee' : riskColor === 'warning' ? '#fff8e1' : '#e8f5e9',
            borderRadius: 2,
            borderLeft: 4,
            borderLeftColor: `${riskColor}.main`,
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
                {t('results.overallRisk')}
              </Typography>
              <HelpTooltip topic="risk_score" />
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, ml: { sm: 'auto' } }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.8 }}>
                {hasV3Risk ? t('results.riskOwaspBadge') : t('results.riskCompositeBadge')}
              </Typography>
              <Typography variant="h3" sx={{ fontWeight: 800, lineHeight: 1 }}>
                {displayRiskScore.toFixed(2)}
              </Typography>
              {hasV3Risk && (
                <Chip
                  label={displayRiskLevel}
                  size="small"
                  color={riskColor}
                  sx={{ height: 24, fontSize: '0.72rem', fontWeight: 700 }}
                />
              )}
              <Tooltip
                arrow
                placement="top"
                title={
                  hasV3Risk ? t('results.riskTooltipOwasp') : t('results.riskTooltipComposite')
                }
              >
                <Chip
                  icon={<InfoOutlinedIcon sx={{ fontSize: 14 }} />}
                  label={hasV3Risk ? t('results.riskChipLikelihoodImpact') : t('results.riskChipSwl')}
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

          {hasV3Risk && (
            <Box
              sx={{
                px: 2.25,
                pb: 1.5,
                display: 'grid',
                gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(4, 1fr)' },
                gap: 1,
              }}
            >
              <Paper variant="outlined" sx={{ p: 1.25, bgcolor: 'rgba(255,255,255,0.55)' }}>
                <Typography variant="caption" color="text.secondary">{t('results.metricMaxSeverity')}</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                  {(scanResults.summary?.max_severity ?? 0).toFixed(1)} / 10
                </Typography>
              </Paper>
              <Paper variant="outlined" sx={{ p: 1.25, bgcolor: 'rgba(255,255,255,0.55)' }}>
                <Typography variant="caption" color="text.secondary">{t('results.metricExposure')}</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                  {(scanResults.summary?.exposure_score ?? 0).toFixed(1)} / 10
                </Typography>
              </Paper>
              <Paper variant="outlined" sx={{ p: 1.25, bgcolor: 'rgba(255,255,255,0.55)' }}>
                <Typography variant="caption" color="text.secondary">{t('results.metricConfidence')}</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 800, textTransform: 'capitalize' }}>
                  {scanResults.summary?.confidence || t('common.unknown')}
                </Typography>
              </Paper>
              <Paper variant="outlined" sx={{ p: 1.25, bgcolor: 'rgba(255,255,255,0.55)' }}>
                <Typography variant="caption" color="text.secondary">{t('results.metricGroups')}</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                  {sortedRiskGroups.length}
                </Typography>
              </Paper>
            </Box>
          )}

          {hasV3Risk ? (
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
                  View grouped risk contributors
                </Typography>
                <Chip
                  label={sortedRiskGroups.length}
                  size="small"
                  sx={{ height: 20, fontSize: '0.7rem', fontWeight: 700 }}
                />
              </AccordionSummary>
              <AccordionDetails sx={{ px: 2.25, pt: 0, pb: 1.5 }}>
                <List
                  dense
                  disablePadding
                  sx={{
                    maxHeight: 320,
                    overflowY: 'auto',
                    pr: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 1,
                  }}
                >
                  {sortedRiskGroups.map((group) => (
                    <ListItem
                      key={group.group_id}
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
                          <Box sx={{ display: 'flex', gap: 0.75, alignItems: 'center', flexWrap: 'wrap' }}>
                            <Chip
                              label={group.risk_level}
                              size="small"
                              color={group.risk_level === 'CRITICAL' || group.risk_level === 'HIGH' ? 'error' : group.risk_level === 'MEDIUM' ? 'warning' : 'success'}
                              sx={{ height: 20, fontSize: '0.65rem', fontWeight: 700 }}
                            />
                            <Typography variant="body2" sx={{ fontWeight: 650, lineHeight: 1.35 }}>
                              {group.title}
                            </Typography>
                          </Box>
                        }
                        secondary={
                          <Box component="span" sx={{ display: 'block' }}>
                            <Typography component="span" variant="caption" color="text.secondary">
                              Risk {group.risk_score.toFixed(2)} = Likelihood {group.likelihood.toFixed(2)} × Impact {group.impact.toFixed(2)}
                              {' '}× exposure {group.exposure_multiplier.toFixed(2)} × confidence {group.confidence_multiplier.toFixed(2)}
                              {' '}· {group.affected_assets} affected asset{group.affected_assets === 1 ? '' : 's'}
                            </Typography>
                            {group.representative_targets.length > 0 && (
                              <Typography component="span" variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                                Targets: {group.representative_targets.slice(0, 4).join(', ')}
                                {group.affected_assets > 4 ? ` and ${group.affected_assets - 4} more` : ''}
                              </Typography>
                            )}
                            {group.recommendation && (
                              <Typography component="span" variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                                Recommendation: {group.recommendation}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          ) : sortedRiskBreakdown.length > 0 && (
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
                  {t('results.sslCertificates')}
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
                  {t('results.openPorts')}
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
                  {t('results.techDetected')}
                  <HelpTooltip topic="tech_stack" size="small" />
                </Typography>
                <Typography variant="h5">{t('results.hosts', { count: Object.keys(scanResults.tech_stack).length })}</Typography>
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
                {t('results.domainInformation')}
                <HelpTooltip topic="domain_info" />
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemText
                    primary={t('common.domain')}
                    secondary={target_domain}
                    secondaryTypographyProps={{ fontFamily: 'monospace', fontWeight: 600 }}
                  />
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemText
                    primary={t('results.registrar')}
                    secondary={whois_info?.registrar || 'N/A'}
                  />
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemText
                    primary={t('results.created')}
                    secondary={whois_info?.creation_date || 'N/A'}
                  />
                </ListItem>
                <Divider component="li" />
                <ListItem>
                  <ListItemText
                    primary={t('results.expires')}
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
                {t('results.ipAddresses')}
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
                <Typography color="text.secondary">{t('results.noIpAddresses')}</Typography>
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
                {t('results.nameServers')}
                <HelpTooltip topic="name_servers" />
              </Typography>
              {dns_info?.ns_records && dns_info.ns_records.length > 0 ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {dns_info.ns_records.map((ns, index) => (
                    <Chip key={index} label={ns} variant="outlined" />
                  ))}
                </Box>
              ) : (
                <Typography color="text.secondary">{t('results.noNameServers')}</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {t('results.mailServersMx')}
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
                <Typography color="text.secondary">{t('results.noMailServers')}</Typography>
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
              {t('results.correlation')}
              <HelpTooltip topic="correlation" />
            </Typography>
            <Grid container spacing={2}>
              {scanResults.correlation.ip_to_subdomains && Object.keys(scanResults.correlation.ip_to_subdomains).length > 0 && (
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" color="text.secondary">{t('results.correlationIpToSubdomains')}</Typography>
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
                  <Typography variant="subtitle2" color="text.secondary">{t('results.reverseDns')}</Typography>
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
                  <Typography variant="subtitle2" color="text.secondary">{t('results.sharedSslCertificates')}</Typography>
                  <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {scanResults.correlation.shared_certificate_hosts?.slice(0, 5).map((group, index) => (
                      <Box key={`${group.certificate_key}-${index}`}>
                        <Chip
                          label={t('results.relatedHosts', { count: group.hosts.length })}
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
                {t('results.subdomainsPreview')}
                <HelpTooltip topic="subdomains_preview" />
              </Typography>
              <Chip label={t('results.total', { count: subdomains.length })} color="primary" size="small" />
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
