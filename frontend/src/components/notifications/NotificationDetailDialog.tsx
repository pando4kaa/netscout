import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Button,
  Tabs,
  Tab,
  Paper,
  Chip,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableRow,
  TableHead,
  TableContainer,
  CircularProgress,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import DownloadIcon from '@mui/icons-material/Download'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import { useState, useEffect } from 'react'
import { notificationsApi, type Notification, type NotificationReport } from '../../services/api'

interface NotificationDetailDialogProps {
  open: boolean
  onClose: () => void
  notification: Notification | null
  onReportLoaded?: () => void
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('uk-UA', { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return String(iso)
  }
}

function ListBlock({ items, max = 30 }: { items: string[]; max?: number }) {
  return (
    <Box sx={{ maxHeight: 150, overflow: 'auto' }}>
      {(items || []).slice(0, max).map((s, i) => (
        <Typography key={i} variant="caption" component="div" sx={{ fontFamily: 'monospace' }}>
          {s}
        </Typography>
      ))}
      {items && items.length > max && (
        <Typography variant="caption" color="text.secondary">
          +{items.length - max} more
        </Typography>
      )}
    </Box>
  )
}

const NotificationDetailDialog = ({
  open,
  onClose,
  notification,
  onReportLoaded,
}: NotificationDetailDialogProps) => {
  const [report, setReport] = useState<NotificationReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState(0)

  useEffect(() => {
    if (!open || !notification) {
      setReport(null)
      return
    }
    setLoading(true)
    setReport(null)
    notificationsApi
      .getReport(notification.id)
      .then((data) => {
        if (data && !('error' in data)) {
          setReport(data as NotificationReport)
          onReportLoaded?.()
        }
      })
      .finally(() => setLoading(false))
  }, [open, notification?.id, onReportLoaded])

  const handleExport = () => {
    if (notification) notificationsApi.exportJson(notification.id)
  }

  if (!notification) return null

  const comp = report?.comparison as {
    scan_1?: { domain?: string; date?: string; risk_score?: number }
    scan_2?: { domain?: string; date?: string; risk_score?: number }
    summary?: {
      risk_1?: number
      risk_2?: number
      risk_delta?: number
      subdomains_added?: number
      subdomains_removed?: number
      ips_added?: number
      ips_removed?: number
      alerts_1?: number
      alerts_2?: number
    }
    subdomains?: { only_in_1: string[]; only_in_2: string[]; in_both: string[] }
    ips?: { only_in_1: string[]; only_in_2: string[]; in_both: string[] }
    ssl?: {
      hosts_only_in_1: string[]
      hosts_only_in_2: string[]
      hosts_in_both: string[]
      expired_changes?: Array<{ host: string; was_expired_1: boolean; is_expired_2: boolean }>
    }
    ports?: {
      by_ip: Record<string, { only_in_1: string[]; only_in_2: string[]; in_both: string[] }>
      new_ports_count: number
      closed_ports_count: number
    }
    alerts?: {
      only_in_1: Array<{ type?: string; level?: string; message?: string; target?: string }>
      only_in_2: Array<{ type?: string; level?: string; message?: string; target?: string }>
    }
  } | undefined

  const summary = comp?.summary || {}

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="h6">{notification.domain}</Typography>
          <Chip label={notification.type} size="small" color="primary" />
          <Typography variant="body2" color="text.secondary">
            {formatDate(notification.created_at)}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            {notification.title}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {notification.message}
          </Typography>
        </Paper>

        {loading ? (
          <Box sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : report && comp ? (
          <Box>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              {comp.scan_1 && (
                <Grid item xs={6}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" color="primary">
                      Попередній скан
                    </Typography>
                    <Typography variant="body2">{formatDate(comp.scan_1.date)}</Typography>
                    <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Chip size="small" label={`Risk: ${comp.scan_1.risk_score ?? summary.risk_1}`} />
                    </Box>
                  </Paper>
                </Grid>
              )}
              {comp.scan_2 && (
                <Grid item xs={6}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" color="secondary">
                      Поточний скан
                    </Typography>
                    <Typography variant="body2">{formatDate(comp.scan_2.date)}</Typography>
                    <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Chip size="small" label={`Risk: ${comp.scan_2.risk_score ?? summary.risk_2}`} />
                    </Box>
                  </Paper>
                </Grid>
              )}
            </Grid>

            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Підсумок змін
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {summary.risk_delta !== undefined && (
                  <Chip
                    size="small"
                    icon={
                      summary.risk_delta > 0 ? (
                        <TrendingUpIcon />
                      ) : summary.risk_delta < 0 ? (
                        <TrendingDownIcon />
                      ) : undefined
                    }
                    color={
                      summary.risk_delta > 0 ? 'error' : summary.risk_delta < 0 ? 'success' : 'default'
                    }
                    label={`Risk: ${summary.risk_1} → ${summary.risk_2} (${summary.risk_delta >= 0 ? '+' : ''}${summary.risk_delta})`}
                  />
                )}
                <Chip
                  size="small"
                  label={`Піддомени: +${summary.subdomains_added ?? 0} нових, −${summary.subdomains_removed ?? 0} видалено`}
                />
                <Chip
                  size="small"
                  label={`IP: +${summary.ips_added ?? 0} нових, −${summary.ips_removed ?? 0} видалено`}
                />
                <Chip size="small" label={`Алерти: ${summary.alerts_1 ?? 0} → ${summary.alerts_2 ?? 0}`} />
              </Box>
            </Paper>

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
              <Tab label="Піддомени" />
              <Tab label="IP" />
              <Tab label="SSL" />
              <Tab label="Порти" />
              <Tab label="Алерти" />
            </Tabs>

            {tab === 0 && comp.subdomains && (
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    Видалено ({comp.subdomains.only_in_1.length})
                  </Typography>
                  <ListBlock items={comp.subdomains.only_in_1} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    Додано ({comp.subdomains.only_in_2.length})
                  </Typography>
                  <ListBlock items={comp.subdomains.only_in_2} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Без змін ({comp.subdomains.in_both.length})
                  </Typography>
                  <ListBlock items={comp.subdomains.in_both} />
                </Grid>
              </Grid>
            )}

            {tab === 1 && comp.ips && (
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    Видалено ({comp.ips.only_in_1.length})
                  </Typography>
                  <ListBlock items={comp.ips.only_in_1} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    Додано ({comp.ips.only_in_2.length})
                  </Typography>
                  <ListBlock items={comp.ips.only_in_2} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Без змін ({comp.ips.in_both.length})
                  </Typography>
                  <ListBlock items={comp.ips.in_both} />
                </Grid>
              </Grid>
            )}

            {tab === 2 && comp.ssl && (
              <Box>
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="primary" gutterBottom>
                      Тільки в попередньому ({comp.ssl.hosts_only_in_1.length})
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_only_in_1} />
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="secondary" gutterBottom>
                      Тільки в поточному ({comp.ssl.hosts_only_in_2.length})
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_only_in_2} />
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      В обох ({comp.ssl.hosts_in_both.length})
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_in_both} />
                  </Grid>
                </Grid>
                {comp.ssl.expired_changes && comp.ssl.expired_changes.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="body2">
                        Зміни терміну дії сертифікатів ({comp.ssl.expired_changes.length})
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Host</TableCell>
                              <TableCell>Попередній</TableCell>
                              <TableCell>Поточний</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {comp.ssl.expired_changes.map((c, i) => (
                              <TableRow key={i}>
                                <TableCell sx={{ fontFamily: 'monospace' }}>{c.host}</TableCell>
                                <TableCell>{c.was_expired_1 ? 'Прострочено' : 'Валідний'}</TableCell>
                                <TableCell>{c.is_expired_2 ? 'Прострочено' : 'Валідний'}</TableCell>
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

            {tab === 3 && comp.ports && (
              <Box>
                <Typography variant="body2" gutterBottom>
                  Нові порти: {comp.ports.new_ports_count} | Закрито: {comp.ports.closed_ports_count}
                </Typography>
                {comp.ports.by_ip && Object.keys(comp.ports.by_ip).length > 0 ? (
                  Object.entries(comp.ports.by_ip).map(([ip, diff]) => (
                    <Accordion key={ip}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {ip}
                        </Typography>
                        <Chip size="small" label={`−${diff.only_in_1.length}`} color="error" sx={{ ml: 1 }} />
                        <Chip size="small" label={`+${diff.only_in_2.length}`} color="success" sx={{ ml: 0.5 }} />
                      </AccordionSummary>
                      <AccordionDetails>
                        <Grid container spacing={2}>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="error">
                              Закрито
                            </Typography>
                            <ListBlock items={diff.only_in_1} />
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="success.main">
                              Нові
                            </Typography>
                            <ListBlock items={diff.only_in_2} />
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">
                              Без змін
                            </Typography>
                            <ListBlock items={diff.in_both} />
                          </Grid>
                        </Grid>
                      </AccordionDetails>
                    </Accordion>
                  ))
                ) : (
                  <Typography color="text.secondary">Немає змін портів</Typography>
                )}
              </Box>
            )}

            {tab === 4 && comp.alerts && (
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    Вирішено ({comp.alerts.only_in_1.length})
                  </Typography>
                  <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                    {comp.alerts.only_in_1.map((a, i) => (
                      <Paper key={i} variant="outlined" sx={{ p: 1, mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          [{a.type}] {a.level}
                        </Typography>
                        <Typography variant="body2">{a.message}</Typography>
                        {a.target && (
                          <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                            {a.target}
                          </Typography>
                        )}
                      </Paper>
                    ))}
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    Нові ({comp.alerts.only_in_2.length})
                  </Typography>
                  <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                    {comp.alerts.only_in_2.map((a, i) => (
                      <Paper key={i} variant="outlined" sx={{ p: 1, mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          [{a.type}] {a.level}
                        </Typography>
                        <Typography variant="body2">{a.message}</Typography>
                        {a.target && (
                          <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                            {a.target}
                          </Typography>
                        )}
                      </Paper>
                    ))}
                  </Box>
                </Grid>
              </Grid>
            )}
          </Box>
        ) : (
          !loading && (
            <Typography color="text.secondary">
              Не вдалося завантажити звіт порівняння. Можливо, дані сканів вже видалено.
            </Typography>
          )
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Закрити</Button>
        <Button variant="contained" startIcon={<DownloadIcon />} onClick={handleExport} disabled={!notification}>
          Експорт звіту (JSON)
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default NotificationDetailDialog
