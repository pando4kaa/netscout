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

function formatDate(iso: string | undefined): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function ListBlock({ items, max = 30 }: { items: string[]; max?: number }) {
  return (
    <Box sx={{ maxHeight: 150, overflow: 'auto' }}>
      {items.slice(0, max).map((s, i) => (
        <Typography key={i} variant="caption" component="div" sx={{ fontFamily: 'monospace' }}>{s}</Typography>
      ))}
      {items.length > max && (
        <Typography variant="caption" color="text.secondary">+{items.length - max} more</Typography>
      )}
    </Box>
  )
}

const CompareResultDialog = ({ open, onClose, result, error, loading }: CompareResultDialogProps) => {
  const [tab, setTab] = useState(0)

  if (loading) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
        <DialogTitle>Scan comparison</DialogTitle>
        <DialogContent>
          <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
            <Typography color="text.secondary">Loading...</Typography>
          </Box>
        </DialogContent>
      </Dialog>
    )
  }

  if (error) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle>Scan comparison</DialogTitle>
        <DialogContent>
          <Typography color="error">{error}</Typography>
        </DialogContent>
      </Dialog>
    )
  }

  if (!result) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle>Scan comparison</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary">Select two different scans and click Compare.</Typography>
        </DialogContent>
      </Dialog>
    )
  }

  const { scan_1, scan_2, summary, subdomains, ips, dns, whois, ssl, ports, tech_stack, alerts } = result

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Scan comparison: {scan_1.domain}</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="primary">Scan 1</Typography>
                <Typography variant="body2">{formatDate(scan_1.date)}</Typography>
                <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip size="small" label={`Risk: ${scan_1.risk_score ?? summary.risk_1}`} />
                  <Chip size="small" label={`Subdomains: ${scan_1.subdomains_count ?? subdomains.count_1}`} />
                  <Chip size="small" label={`Alerts: ${scan_1.alerts_count ?? summary.alerts_1}`} />
                </Box>
              </Paper>
            </Grid>
            <Grid item xs={6}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" color="secondary">Scan 2</Typography>
                <Typography variant="body2">{formatDate(scan_2.date)}</Typography>
                <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip size="small" label={`Risk: ${scan_2.risk_score ?? summary.risk_2}`} />
                  <Chip size="small" label={`Subdomains: ${scan_2.subdomains_count ?? subdomains.count_2}`} />
                  <Chip size="small" label={`Alerts: ${scan_2.alerts_count ?? summary.alerts_2}`} />
                </Box>
              </Paper>
            </Grid>
          </Grid>

          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>Summary of changes</Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip
                size="small"
                icon={summary.risk_delta !== undefined && summary.risk_delta > 0 ? <TrendingUpIcon /> : summary.risk_delta !== undefined && summary.risk_delta < 0 ? <TrendingDownIcon /> : undefined}
                color={summary.risk_delta !== undefined && summary.risk_delta > 0 ? 'error' : summary.risk_delta !== undefined && summary.risk_delta < 0 ? 'success' : 'default'}
                label={`Risk: ${summary.risk_1} → ${summary.risk_2}${summary.risk_delta !== undefined ? ` (${summary.risk_delta >= 0 ? '+' : ''}${summary.risk_delta})` : ''}`}
              />
              <Chip size="small" label={`Subdomains: +${summary.subdomains_added ?? 0} new, −${summary.subdomains_removed ?? 0} removed`} />
              <Chip size="small" label={`IPs: +${summary.ips_added ?? 0} new, −${summary.ips_removed ?? 0} removed`} />
              <Chip size="small" label={`Alerts: ${summary.alerts_1} → ${summary.alerts_2}`} />
            </Box>
          </Paper>

          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tab label="Subdomains" />
            <Tab label="IPs" />
            <Tab label="DNS" />
            <Tab label="SSL" />
            <Tab label="Ports" />
            <Tab label="Tech" />
            <Tab label="Alerts" />
            <Tab label="WHOIS" />
          </Tabs>

          {tab === 0 && (
            <Grid container spacing={2}>
              <Grid item xs={4}>
                <Typography variant="body2" color="primary" gutterBottom>Only in Scan 1 ({subdomains.only_in_1.length})</Typography>
                <ListBlock items={subdomains.only_in_1} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="secondary" gutterBottom>Only in Scan 2 ({subdomains.only_in_2.length})</Typography>
                <ListBlock items={subdomains.only_in_2} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary" gutterBottom>In both ({subdomains.in_both.length})</Typography>
                <ListBlock items={subdomains.in_both} />
              </Grid>
            </Grid>
          )}

          {tab === 1 && (
            <Grid container spacing={2}>
              <Grid item xs={4}>
                <Typography variant="body2" color="primary" gutterBottom>Only in Scan 1 ({ips.only_in_1.length})</Typography>
                <ListBlock items={ips.only_in_1} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="secondary" gutterBottom>Only in Scan 2 ({ips.only_in_2.length})</Typography>
                <ListBlock items={ips.only_in_2} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary" gutterBottom>In both ({ips.in_both.length})</Typography>
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
                          <Typography variant="caption" color="primary">Only in Scan 1</Typography>
                          <ListBlock items={diff.only_in_1} />
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="secondary">Only in Scan 2</Typography>
                          <ListBlock items={diff.only_in_2} />
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">In both</Typography>
                          <ListBlock items={diff.in_both} />
                        </Grid>
                      </Grid>
                    </AccordionDetails>
                  </Accordion>
                ))
              ) : (
                <Typography color="text.secondary">No DNS changes</Typography>
              )}
            </Box>
          )}

          {tab === 3 && ssl && (
            <Box>
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="primary" gutterBottom>Hosts only in Scan 1 ({ssl.hosts_only_in_1.length})</Typography>
                  <ListBlock items={ssl.hosts_only_in_1} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="secondary" gutterBottom>Hosts only in Scan 2 ({ssl.hosts_only_in_2.length})</Typography>
                  <ListBlock items={ssl.hosts_only_in_2} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>Hosts in both ({ssl.hosts_in_both.length})</Typography>
                  <ListBlock items={ssl.hosts_in_both} />
                </Grid>
              </Grid>
              {ssl.expired_changes && ssl.expired_changes.length > 0 && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="body2">Certificate expiry changes ({ssl.expired_changes.length})</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Host</TableCell>
                            <TableCell>Scan 1</TableCell>
                            <TableCell>Scan 2</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {ssl.expired_changes.map((c, i) => (
                            <TableRow key={i}>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{c.host}</TableCell>
                              <TableCell>{c.was_expired_1 ? 'Expired' : 'Valid'}</TableCell>
                              <TableCell>{c.is_expired_2 ? 'Expired' : 'Valid'}</TableCell>
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
                New ports: {ports.new_ports_count} | Closed ports: {ports.closed_ports_count} | IPs with changes: {ports.ips_with_changes}
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
                          <Typography variant="caption" color="error">Closed (Scan 1 only)</Typography>
                          <ListBlock items={diff.only_in_1} />
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="success.main">New (Scan 2 only)</Typography>
                          <ListBlock items={diff.only_in_2} />
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">Unchanged</Typography>
                          <ListBlock items={diff.in_both} />
                        </Grid>
                      </Grid>
                    </AccordionDetails>
                  </Accordion>
                ))
              ) : (
                <Typography color="text.secondary">No port changes</Typography>
              )}
            </Box>
          )}

          {tab === 5 && tech_stack && (
            <Grid container spacing={2}>
              <Grid item xs={4}>
                <Typography variant="body2" color="primary" gutterBottom>Removed ({tech_stack.only_in_1.length})</Typography>
                <ListBlock items={tech_stack.only_in_1} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="secondary" gutterBottom>Added ({tech_stack.only_in_2.length})</Typography>
                <ListBlock items={tech_stack.only_in_2} />
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="text.secondary" gutterBottom>Unchanged ({tech_stack.in_both.length})</Typography>
                <ListBlock items={tech_stack.in_both} />
              </Grid>
              {tech_stack.value_changes && tech_stack.value_changes.length > 0 && (
                <Grid item xs={12}>
                  <Typography variant="body2" gutterBottom sx={{ mt: 2 }}>Value changes</Typography>
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Technology</TableCell>
                          <TableCell>Scan 1</TableCell>
                          <TableCell>Scan 2</TableCell>
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
                <Typography variant="body2" color="primary" gutterBottom>Resolved (only in Scan 1) ({alerts.only_in_1.length})</Typography>
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
                <Typography variant="body2" color="secondary" gutterBottom>New (only in Scan 2) ({alerts.only_in_2.length})</Typography>
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

          {tab === 7 && whois && Object.keys(whois).length > 0 && (
            <Box>
              {whois.registrar && typeof whois.registrar === 'object' && 'changed' in whois.registrar && (
                <Accordion defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>Registrar</AccordionSummary>
                  <AccordionDetails>
                    <Table size="small">
                      <TableBody>
                        <TableRow><TableCell>Scan 1</TableCell><TableCell>{String((whois.registrar as { value_1?: unknown }).value_1 ?? '-')}</TableCell></TableRow>
                        <TableRow><TableCell>Scan 2</TableCell><TableCell>{String((whois.registrar as { value_2?: unknown }).value_2 ?? '-')}</TableCell></TableRow>
                        <TableRow><TableCell>Changed</TableCell><TableCell>{(whois.registrar as { changed?: boolean }).changed ? 'Yes' : 'No'}</TableCell></TableRow>
                      </TableBody>
                    </Table>
                  </AccordionDetails>
                </Accordion>
              )}
              {whois.creation_date && typeof whois.creation_date === 'object' && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>Creation date</AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2">Scan 1: {String((whois.creation_date as { value_1?: unknown }).value_1 ?? '-')}</Typography>
                    <Typography variant="body2">Scan 2: {String((whois.creation_date as { value_2?: unknown }).value_2 ?? '-')}</Typography>
                  </AccordionDetails>
                </Accordion>
              )}
              {whois.expiration_date && typeof whois.expiration_date === 'object' && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>Expiration date</AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2">Scan 1: {String((whois.expiration_date as { value_1?: unknown }).value_1 ?? '-')}</Typography>
                    <Typography variant="body2">Scan 2: {String((whois.expiration_date as { value_2?: unknown }).value_2 ?? '-')}</Typography>
                  </AccordionDetails>
                </Accordion>
              )}
              {whois.name_servers && typeof whois.name_servers === 'object' && 'only_in_1' in whois.name_servers && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>Name servers</AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="primary">Removed</Typography>
                        <ListBlock items={(whois.name_servers as { only_in_1: string[] }).only_in_1} />
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="secondary">Added</Typography>
                        <ListBlock items={(whois.name_servers as { only_in_2: string[] }).only_in_2} />
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary">Unchanged</Typography>
                        <ListBlock items={(whois.name_servers as { in_both: string[] }).in_both} />
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
