import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableRow,
  TableHead,
  TableContainer,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocaleFormatters } from '../../i18n/format'

export interface CompareResultData {
  scan_1: { scan_id?: string; domain?: string; date?: string; risk_score?: number; subdomains_count?: number; ips_count?: number; alerts_count?: number }
  scan_2: { scan_id?: string; domain?: string; date?: string; risk_score?: number; subdomains_count?: number; ips_count?: number; alerts_count?: number }
  summary: {
    risk_1: number
    risk_2: number
    risk_delta?: number
    alerts_1: number
    alerts_2: number
    subdomains_count_1: number
    subdomains_count_2: number
    subdomains_added?: number
    subdomains_removed?: number
    ips_count_1: number
    ips_count_2: number
    ips_added?: number
    ips_removed?: number
  }
  subdomains: { only_in_1: string[]; only_in_2: string[]; in_both: string[]; count_1: number; count_2: number }
  ips: { only_in_1: string[]; only_in_2: string[]; in_both: string[] }
  dns?: Record<string, { only_in_1: string[]; only_in_2: string[]; in_both: string[] }>
  whois?: Record<string, unknown>
  ssl?: { hosts_only_in_1: string[]; hosts_only_in_2: string[]; hosts_in_both: string[]; expired_changes: Array<{ host: string; was_expired_1: boolean; is_expired_2: boolean }>; count_1: number; count_2: number }
  ports?: { by_ip: Record<string, { only_in_1: string[]; only_in_2: string[]; in_both: string[] }>; new_ports_count: number; closed_ports_count: number; ips_with_changes: number }
  tech_stack?: { only_in_1: string[]; only_in_2: string[]; in_both: string[]; value_changes?: Array<{ tech: string; value_1: unknown; value_2: unknown }> }
  alerts?: { only_in_1: Array<{ type?: string; level?: string; message?: string; target?: string }>; only_in_2: Array<{ type?: string; level?: string; message?: string; target?: string }>; in_both: unknown[]; count_1: number; count_2: number }
}

interface CompareResultDialogProps {
  open: boolean
  onClose: () => void
  result: CompareResultData | null
  error: string | null
  loading: boolean
}

function ListBlock({ items, max = 30 }: { items: string[]; max?: number }) {
  const { t } = useTranslation()

  return (
    <Box sx={{ maxHeight: 150, overflow: 'auto' }}>
      {items.slice(0, max).map((s, i) => (
        <Typography key={i} variant="caption" component="div" sx={{ fontFamily: 'monospace' }}>{s}</Typography>
      ))}
      {items.length > max && (
        <Typography variant="caption" color="text.secondary">
          {t('results.moreItems', { count: items.length - max })}
        </Typography>
      )}
    </Box>
  )
}

const CompareResultDialog = ({ open, onClose, result, error, loading }: CompareResultDialogProps) => {
  const { t } = useTranslation()
  const { formatDateTime } = useLocaleFormatters()
  const [tab, setTab] = useState(0)

  if (loading) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
        <DialogTitle>{t('history.compareScans')}</DialogTitle>
        <DialogContent>
          <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
            <Typography color="text.secondary">{t('common.loading')}</Typography>
          </Box>
        </DialogContent>
      </Dialog>
    )
  }

  if (error) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle>{t('history.compareScans')}</DialogTitle>
        <DialogContent>
          <Typography color="error">{error}</Typography>
        </DialogContent>
      </Dialog>
    )
  }

  if (!result) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle>{t('history.compareScans')}</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary">{t('history.compareScans')}</Typography>
        </DialogContent>
      </Dialog>
    )
  }

  const { scan_1, scan_2, summary, subdomains, ips, dns, whois, ssl, ports, tech_stack, alerts } = result

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>{t('history.compareScans')}: {scan_1.domain}</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="primary">{t('history.scanOne')}</Typography>
                <Typography variant="body2">{formatDateTime(scan_1.date)}</Typography>
                <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip size="small" label={`${t('common.risk')}: ${scan_1.risk_score ?? summary.risk_1}`} />
                  <Chip size="small" label={`${t('common.subdomains')}: ${scan_1.subdomains_count ?? subdomains.count_1}`} />
                  <Chip size="small" label={`${t('common.alerts')}: ${scan_1.alerts_count ?? summary.alerts_1}`} />
                </Box>
              </Paper>
            </Grid>
            <Grid item xs={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="secondary">{t('history.scanTwo')}</Typography>
                <Typography variant="body2">{formatDateTime(scan_2.date)}</Typography>
                <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip size="small" label={`${t('common.risk')}: ${scan_2.risk_score ?? summary.risk_2}`} />
                  <Chip size="small" label={`${t('common.subdomains')}: ${scan_2.subdomains_count ?? subdomains.count_2}`} />
                  <Chip size="small" label={`${t('common.alerts')}: ${scan_2.alerts_count ?? summary.alerts_2}`} />
                </Box>
              </Paper>
            </Grid>
          </Grid>

          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>{t('notifications.subtitle')}</Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip
                size="small"
                icon={summary.risk_delta !== undefined && summary.risk_delta > 0 ? <TrendingUpIcon /> : summary.risk_delta !== undefined && summary.risk_delta < 0 ? <TrendingDownIcon /> : undefined}
                color={summary.risk_delta !== undefined && summary.risk_delta > 0 ? 'error' : summary.risk_delta !== undefined && summary.risk_delta < 0 ? 'success' : 'default'}
                label={`${t('common.risk')}: ${summary.risk_1} → ${summary.risk_2}${summary.risk_delta !== undefined ? ` (${summary.risk_delta >= 0 ? '+' : ''}${summary.risk_delta})` : ''}`}
              />
              <Chip size="small" label={`${t('common.subdomains')}: +${summary.subdomains_added ?? 0}, −${summary.subdomains_removed ?? 0}`} />
              <Chip
                size="small"
                label={t('history.ipsDelta', {
                  added: summary.ips_added ?? 0,
                  removed: summary.ips_removed ?? 0,
                })}
              />
              <Chip size="small" label={`${t('common.alerts')}: ${summary.alerts_1} → ${summary.alerts_2}`} />
            </Box>
          </Paper>

          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tab label={t('common.subdomains')} />
            <Tab label={t('results.ipAddresses')} />
            <Tab label={t('history.compareTabDns')} />
            <Tab label={t('history.compareTabSsl')} />
            <Tab label={t('scan.tabs.ports')} />
            <Tab label={t('results.technologies')} />
            <Tab label={t('common.alerts')} />
            <Tab label={t('history.compareTabWhois')} />
          </Tabs>

          {tab === 0 && (
            <Grid container spacing={2}>
              <Grid item xs={4}>
                <Typography variant="body2" color="primary" gutterBottom>{t('history.onlyInScan', { scan: 1, count: subdomains.only_in_1.length })}</Typography>
                <ListBlock items={subdomains.only_in_1} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="secondary" gutterBottom>{t('history.onlyInScan', { scan: 2, count: subdomains.only_in_2.length })}</Typography>
                <ListBlock items={subdomains.only_in_2} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary" gutterBottom>{t('history.inBoth', { count: subdomains.in_both.length })}</Typography>
                <ListBlock items={subdomains.in_both} />
              </Grid>
            </Grid>
          )}

          {tab === 1 && (
            <Grid container spacing={2}>
              <Grid item xs={4}>
                <Typography variant="body2" color="primary" gutterBottom>{t('history.onlyInScan', { scan: 1, count: ips.only_in_1.length })}</Typography>
                <ListBlock items={ips.only_in_1} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="secondary" gutterBottom>{t('history.onlyInScan', { scan: 2, count: ips.only_in_2.length })}</Typography>
                <ListBlock items={ips.only_in_2} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary" gutterBottom>{t('history.inBoth', { count: ips.in_both.length })}</Typography>
                <ListBlock items={ips.in_both} />
              </Grid>
            </Grid>
          )}

          {tab === 2 && (
            <Box>
              {dns && Object.keys(dns).length > 0 ? (
                Object.entries(dns).map(([key, diff]) => (
                  <Accordion key={key} defaultExpanded>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="body2">{key.replace(/_/g, ' ')}</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Grid container spacing={2}>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="primary">{t('history.onlyInScanShort', { scan: 1 })}</Typography>
                          <ListBlock items={diff.only_in_1} />
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="secondary">{t('history.onlyInScanShort', { scan: 2 })}</Typography>
                          <ListBlock items={diff.only_in_2} />
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">{t('history.inBothShort')}</Typography>
                          <ListBlock items={diff.in_both} />
                        </Grid>
                      </Grid>
                    </AccordionDetails>
                  </Accordion>
                ))
              ) : (
                <Typography color="text.secondary">{t('history.noDnsChanges')}</Typography>
              )}
            </Box>
          )}

          {tab === 3 && ssl && (
            <Box>
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="primary" gutterBottom>{t('history.hostsOnlyInScan', { scan: 1, count: ssl.hosts_only_in_1.length })}</Typography>
                  <ListBlock items={ssl.hosts_only_in_1} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="secondary" gutterBottom>{t('history.hostsOnlyInScan', { scan: 2, count: ssl.hosts_only_in_2.length })}</Typography>
                  <ListBlock items={ssl.hosts_only_in_2} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>{t('history.hostsInBoth', { count: ssl.hosts_in_both.length })}</Typography>
                  <ListBlock items={ssl.hosts_in_both} />
                </Grid>
              </Grid>
              {ssl.expired_changes && ssl.expired_changes.length > 0 && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="body2">{t('history.certificateExpiryChanges', { count: ssl.expired_changes.length })}</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>{t('results.host')}</TableCell>
                            <TableCell>{t('history.scanOne')}</TableCell>
                            <TableCell>{t('history.scanTwo')}</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {ssl.expired_changes.map((c, i) => (
                            <TableRow key={i}>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{c.host}</TableCell>
                              <TableCell>{c.was_expired_1 ? t('results.expired') : t('results.valid')}</TableCell>
                              <TableCell>{c.is_expired_2 ? t('results.expired') : t('results.valid')}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </AccordionDetails>
                </Accordion>
              )}
            </Box>
          )}

          {tab === 4 && ports && (
            <Box>
              <Typography variant="body2" gutterBottom>
                {t('history.portChangesSummary', {
                  newPorts: ports.new_ports_count,
                  closedPorts: ports.closed_ports_count,
                  ips: ports.ips_with_changes,
                })}
              </Typography>
              {ports.by_ip && Object.keys(ports.by_ip).length > 0 ? (
                Object.entries(ports.by_ip).map(([ip, diff]) => (
                  <Accordion key={ip}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>{ip}</Typography>
                      <Chip size="small" label={`−${diff.only_in_1.length}`} color="error" sx={{ ml: 1 }} />
                      <Chip size="small" label={`+${diff.only_in_2.length}`} color="success" sx={{ ml: 0.5 }} />
                    </AccordionSummary>
                    <AccordionDetails>
                      <Grid container spacing={2}>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="error">{t('history.closedScanOneOnly')}</Typography>
                          <ListBlock items={diff.only_in_1} />
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="success.main">{t('history.newScanTwoOnly')}</Typography>
                          <ListBlock items={diff.only_in_2} />
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">{t('history.unchanged')}</Typography>
                          <ListBlock items={diff.in_both} />
                        </Grid>
                      </Grid>
                    </AccordionDetails>
                  </Accordion>
                ))
              ) : (
                <Typography color="text.secondary">{t('history.noPortChanges')}</Typography>
              )}
            </Box>
          )}

          {tab === 5 && tech_stack && (
            <Grid container spacing={2}>
              <Grid item xs={4}>
                <Typography variant="body2" color="primary" gutterBottom>{t('history.removed', { count: tech_stack.only_in_1.length })}</Typography>
                <ListBlock items={tech_stack.only_in_1} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="secondary" gutterBottom>{t('history.added', { count: tech_stack.only_in_2.length })}</Typography>
                <ListBlock items={tech_stack.only_in_2} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary" gutterBottom>{t('history.unchangedWithCount', { count: tech_stack.in_both.length })}</Typography>
                <ListBlock items={tech_stack.in_both} />
              </Grid>
              {tech_stack.value_changes && tech_stack.value_changes.length > 0 && (
                <Grid item xs={12}>
                  <Typography variant="body2" gutterBottom sx={{ mt: 2 }}>{t('history.valueChanges')}</Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>{t('investigations.types.technology')}</TableCell>
                          <TableCell>{t('history.scanOne')}</TableCell>
                          <TableCell>{t('history.scanTwo')}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {tech_stack.value_changes.map((v, i) => (
                          <TableRow key={i}>
                            <TableCell>{v.tech}</TableCell>
                            <TableCell>{String(v.value_1 ?? '-')}</TableCell>
                            <TableCell>{String(v.value_2 ?? '-')}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Grid>
              )}
            </Grid>
          )}

          {tab === 6 && alerts && (
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="body2" color="primary" gutterBottom>{t('history.resolvedOnlyInScan', { scan: 1, count: alerts.only_in_1.length })}</Typography>
                <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                  {alerts.only_in_1.map((a, i) => (
                    <Paper key={i} variant="outlined" sx={{ p: 1, mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">[{a.type}] {a.level}</Typography>
                      <Typography variant="body2">{a.message}</Typography>
                      {a.target && <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{a.target}</Typography>}
                    </Paper>
                  ))}
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="secondary" gutterBottom>{t('history.newOnlyInScan', { scan: 2, count: alerts.only_in_2.length })}</Typography>
                <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                  {alerts.only_in_2.map((a, i) => (
                    <Paper key={i} variant="outlined" sx={{ p: 1, mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">[{a.type}] {a.level}</Typography>
                      <Typography variant="body2">{a.message}</Typography>
                      {a.target && <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{a.target}</Typography>}
                    </Paper>
                  ))}
                </Box>
              </Grid>
            </Grid>
          )}

          {tab === 7 && !!whois && Object.keys(whois).length > 0 && (
            <Box>
              {Boolean(whois.registrar && typeof whois.registrar === 'object' && 'changed' in whois.registrar) && (
                <Accordion defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>{t('results.registrar')}</AccordionSummary>
                  <AccordionDetails>
                    <Table size="small">
                      <TableBody>
                        <TableRow><TableCell>{t('history.scanOne')}</TableCell><TableCell>{String((whois.registrar as { value_1?: unknown }).value_1 ?? '-')}</TableCell></TableRow>
                        <TableRow><TableCell>{t('history.scanTwo')}</TableCell><TableCell>{String((whois.registrar as { value_2?: unknown }).value_2 ?? '-')}</TableCell></TableRow>
                        <TableRow><TableCell>{t('history.changed')}</TableCell><TableCell>{(whois.registrar as { changed?: boolean }).changed ? t('common.yes') : t('common.no')}</TableCell></TableRow>
                      </TableBody>
                    </Table>
                  </AccordionDetails>
                </Accordion>
              )}
              {Boolean(whois.creation_date && typeof whois.creation_date === 'object') && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>{t('history.creationDate')}</AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2">{t('history.scanOne')}: {String((whois.creation_date as { value_1?: unknown }).value_1 ?? '-')}</Typography>
                    <Typography variant="body2">{t('history.scanTwo')}: {String((whois.creation_date as { value_2?: unknown }).value_2 ?? '-')}</Typography>
                  </AccordionDetails>
                </Accordion>
              )}
              {Boolean(whois.expiration_date && typeof whois.expiration_date === 'object') && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>{t('history.expirationDate')}</AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2">{t('history.scanOne')}: {String((whois.expiration_date as { value_1?: unknown }).value_1 ?? '-')}</Typography>
                    <Typography variant="body2">{t('history.scanTwo')}: {String((whois.expiration_date as { value_2?: unknown }).value_2 ?? '-')}</Typography>
                  </AccordionDetails>
                </Accordion>
              )}
              {Boolean(whois.name_servers && typeof whois.name_servers === 'object' && 'only_in_1' in whois.name_servers) && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>{t('results.nameServers')}</AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="primary">{t('history.removedShort')}</Typography>
                        <ListBlock items={(whois.name_servers as { only_in_1: string[] }).only_in_1} />
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="secondary">{t('history.addedShort')}</Typography>
                        <ListBlock items={(whois.name_servers as unknown as { only_in_2: string[] }).only_in_2} />
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary">{t('history.unchanged')}</Typography>
                        <ListBlock items={(whois.name_servers as unknown as { in_both: string[] }).in_both} />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              )}
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  )
}

export default CompareResultDialog
