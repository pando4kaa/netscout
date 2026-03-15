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
  Menu,
  MenuItem,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import DownloadIcon from '@mui/icons-material/Download'
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import { useState, useEffect } from 'react'
import { jsPDF } from 'jspdf'
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
    return new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
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

  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null)

  const handleExportJson = () => {
    if (notification) notificationsApi.exportJson(notification.id)
    setExportAnchor(null)
  }

  const buildHumanReadableReport = (): string => {
    if (!notification || !report || !comp) return ''
    const lines: string[] = []
    lines.push('═'.repeat(60))
    lines.push(`CHANGE REPORT: ${notification.domain}`)
    lines.push('═'.repeat(60))
    lines.push('')
    lines.push(`Event type: ${notification.type}`)
    lines.push(`Date: ${formatDate(notification.created_at)}`)
    lines.push(`Title: ${notification.title}`)
    lines.push(`Message: ${notification.message}`)
    lines.push('')

    if (comp.scan_1 || comp.scan_2) {
      lines.push('─'.repeat(60))
      lines.push('SCAN COMPARISON')
      lines.push('─'.repeat(60))
      if (comp.scan_1) {
        lines.push(`Previous scan: ${formatDate(comp.scan_1.date)} | Risk: ${comp.scan_1.risk_score ?? summary.risk_1}`)
      }
      if (comp.scan_2) {
        lines.push(`Current scan:  ${formatDate(comp.scan_2.date)} | Risk: ${comp.scan_2.risk_score ?? summary.risk_2}`)
      }
      lines.push('')
    }

    lines.push('─'.repeat(60))
    lines.push('SUMMARY OF CHANGES')
    lines.push('─'.repeat(60))
    if (summary.risk_delta !== undefined) {
      lines.push(`Risk: ${summary.risk_1} → ${summary.risk_2} (${summary.risk_delta >= 0 ? '+' : ''}${summary.risk_delta})`)
    }
    lines.push(`Subdomains: +${summary.subdomains_added ?? 0} new, −${summary.subdomains_removed ?? 0} removed`)
    lines.push(`IP: +${summary.ips_added ?? 0} new, −${summary.ips_removed ?? 0} removed`)
    lines.push(`Alerts: ${summary.alerts_1 ?? 0} → ${summary.alerts_2 ?? 0}`)
    lines.push('')

    if (comp.subdomains) {
      lines.push('─'.repeat(60))
      lines.push('SUBDOMAINS')
      lines.push('─'.repeat(60))
      lines.push(`Removed (${comp.subdomains.only_in_1.length}):`)
      comp.subdomains.only_in_1.forEach((s) => lines.push(`  • ${s}`))
      lines.push(`Added (${comp.subdomains.only_in_2.length}):`)
      comp.subdomains.only_in_2.forEach((s) => lines.push(`  • ${s}`))
      lines.push(`Unchanged (${comp.subdomains.in_both.length}):`)
      comp.subdomains.in_both.slice(0, 20).forEach((s) => lines.push(`  • ${s}`))
      if (comp.subdomains.in_both.length > 20) {
        lines.push(`  ... and ${comp.subdomains.in_both.length - 20} more`)
      }
      lines.push('')
    }

    if (comp.ips) {
      lines.push('─'.repeat(60))
      lines.push('IP ADDRESSES')
      lines.push('─'.repeat(60))
      lines.push(`Removed (${comp.ips.only_in_1.length}):`)
      comp.ips.only_in_1.forEach((ip) => lines.push(`  • ${ip}`))
      lines.push(`Added (${comp.ips.only_in_2.length}):`)
      comp.ips.only_in_2.forEach((ip) => lines.push(`  • ${ip}`))
      lines.push('')
    }

    if (comp.ssl) {
      lines.push('─'.repeat(60))
      lines.push('SSL CERTIFICATES')
      lines.push('─'.repeat(60))
      lines.push(`Only in previous (${comp.ssl.hosts_only_in_1.length}):`)
      comp.ssl.hosts_only_in_1.forEach((h) => lines.push(`  • ${h}`))
      lines.push(`Only in current (${comp.ssl.hosts_only_in_2.length}):`)
      comp.ssl.hosts_only_in_2.forEach((h) => lines.push(`  • ${h}`))
      if (comp.ssl.expired_changes?.length) {
        lines.push('Validity changes:')
        comp.ssl.expired_changes.forEach((c) =>
          lines.push(`  • ${c.host}: ${c.was_expired_1 ? 'Expired' : 'Valid'} → ${c.is_expired_2 ? 'Expired' : 'Valid'}`)
        )
      }
      lines.push('')
    }

    if (comp.ports && comp.ports.by_ip && Object.keys(comp.ports.by_ip).length > 0) {
      lines.push('─'.repeat(60))
      lines.push('PORTS')
      lines.push('─'.repeat(60))
      lines.push(`New ports: ${comp.ports.new_ports_count ?? 0} | Closed: ${comp.ports.closed_ports_count ?? 0}`)
      Object.entries(comp.ports.by_ip).forEach(([ip, diff]) => {
        lines.push(`  ${ip}: −${diff.only_in_1?.length ?? 0} closed, +${diff.only_in_2?.length ?? 0} new`)
      })
      lines.push('')
    }

    if (comp.alerts) {
      lines.push('─'.repeat(60))
      lines.push('ALERTS')
      lines.push('─'.repeat(60))
      lines.push(`Resolved (${comp.alerts.only_in_1.length}):`)
      comp.alerts.only_in_1.forEach((a) => lines.push(`  • [${a.type}] ${a.message}${a.target ? ` (${a.target})` : ''}`))
      lines.push(`New (${comp.alerts.only_in_2.length}):`)
      comp.alerts.only_in_2.forEach((a) => lines.push(`  • [${a.type}] ${a.message}${a.target ? ` (${a.target})` : ''}`))
    }

    lines.push('')
    lines.push('═'.repeat(60))
    lines.push(`Report generated by NetScout • ${new Date().toLocaleString('en-US')}`)
    return lines.join('\n')
  }

  const handleExportTxt = () => {
    const text = buildHumanReadableReport()
    if (!text) return
    const BOM = '\uFEFF'
    const blob = new Blob([BOM + text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${notification?.domain}_${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
    setExportAnchor(null)
  }

  const buildPdfReport = async () => {
    if (!notification || !report || !comp) return
    await document.fonts.ready

    const pageWidthPx = 1240
    const pageHeightPx = 1754
    const marginX = 76
    const marginTop = 84
    const marginBottom = 72
    const contentWidth = pageWidthPx - marginX * 2
    const contentBottom = pageHeightPx - marginBottom

    const createCanvas = () => {
      const canvas = document.createElement('canvas')
      canvas.width = pageWidthPx
      canvas.height = pageHeightPx
      const ctx = canvas.getContext('2d')
      if (!ctx) return null
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, pageWidthPx, pageHeightPx)
      return { canvas, ctx }
    }

    const state = createCanvas()
    if (!state) return
    let { canvas, ctx } = state
    let cursorY = marginTop
    let pageNo = 1
    const pages: string[] = []

    const setFont = (size: number, weight: 400 | 600 | 700 = 400) => {
      ctx.font = `${weight} ${size}px "Montserrat", "Segoe UI", Arial, sans-serif`
      ctx.fillStyle = '#1f2937'
    }

    const wrapText = (text: string, maxWidth: number) => {
      if (!text.trim()) return ['']
      const words = text.split(/\s+/)
      const wrapped: string[] = []
      let line = ''

      for (const word of words) {
        const candidate = line ? `${line} ${word}` : word
        if (ctx.measureText(candidate).width <= maxWidth) {
          line = candidate
          continue
        }
        if (line) wrapped.push(line)
        line = word

        while (ctx.measureText(line).width > maxWidth && line.length > 1) {
          let splitAt = line.length - 1
          while (splitAt > 1 && ctx.measureText(line.slice(0, splitAt)).width > maxWidth) splitAt -= 1
          wrapped.push(line.slice(0, splitAt))
          line = line.slice(splitAt)
        }
      }
      if (line) wrapped.push(line)
      return wrapped
    }

    const drawFooter = () => {
      ctx.strokeStyle = '#e5e7eb'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(marginX, pageHeightPx - 50)
      ctx.lineTo(pageWidthPx - marginX, pageHeightPx - 50)
      ctx.stroke()
      setFont(14, 400)
      ctx.fillStyle = '#6b7280'
      ctx.fillText(`NetScout Report`, marginX, pageHeightPx - 24)
      const pageLabel = `Page ${pageNo}`
      const labelWidth = ctx.measureText(pageLabel).width
      ctx.fillText(pageLabel, pageWidthPx - marginX - labelWidth, pageHeightPx - 24)
    }

    const pushPage = () => {
      drawFooter()
      pages.push(canvas.toDataURL('image/png'))
      const next = createCanvas()
      if (!next) return false
      canvas = next.canvas
      ctx = next.ctx
      cursorY = marginTop
      pageNo += 1
      return true
    }

    const ensureSpace = (requiredHeight: number) => {
      if (cursorY + requiredHeight <= contentBottom) return true
      return pushPage()
    }

    const drawParagraph = (text: string, opts?: { size?: number; weight?: 400 | 600 | 700; color?: string; indent?: number; gap?: number }) => {
      const size = opts?.size ?? 25
      const weight = opts?.weight ?? 400
      const indent = opts?.indent ?? 0
      const gap = opts?.gap ?? 14
      setFont(size, weight)
      if (opts?.color) ctx.fillStyle = opts.color
      const lines = wrapText(text, contentWidth - indent)
      if (!ensureSpace(lines.length * (size + 14) + gap)) return
      for (const line of lines) {
        ctx.fillText(line, marginX + indent, cursorY)
        cursorY += size + 14
      }
      cursorY += gap
    }

    const drawSection = (title: string) => {
      if (!ensureSpace(90)) return
      cursorY += 4
      setFont(30, 700)
      ctx.fillStyle = '#111827'
      ctx.fillText(title, marginX, cursorY)
      cursorY += 20
      ctx.fillStyle = '#2563eb'
      ctx.fillRect(marginX, cursorY, 120, 5)
      cursorY += 32
    }

    const buildNarrative = () => {
      const narrative: string[] = []
      const riskDelta = summary.risk_delta ?? 0
      if (riskDelta > 0) narrative.push(`Risk score increased by ${riskDelta}. Attack surface has widened.`)
      if (riskDelta < 0) narrative.push(`Risk score decreased by ${Math.abs(riskDelta)}. Overall security improved.`)
      if (riskDelta === 0) narrative.push('Risk score unchanged compared to the previous scan.')

      if ((summary.subdomains_added ?? 0) > 0 || (summary.subdomains_removed ?? 0) > 0) {
        narrative.push(
          `Subdomains: ${summary.subdomains_added ?? 0} added, ${summary.subdomains_removed ?? 0} removed.`
        )
      }
      if ((summary.ips_added ?? 0) > 0 || (summary.ips_removed ?? 0) > 0) {
        narrative.push(`IP addresses: ${summary.ips_added ?? 0} added, ${summary.ips_removed ?? 0} removed.`)
      }
      if ((summary.alerts_2 ?? 0) !== (summary.alerts_1 ?? 0)) {
        narrative.push(`Alert count changed: ${summary.alerts_1 ?? 0} -> ${summary.alerts_2 ?? 0}.`)
      }
      if ((comp.ssl?.expired_changes?.length ?? 0) > 0) {
        narrative.push(`Found ${comp.ssl?.expired_changes?.length ?? 0} SSL certificate status changes.`)
      }
      if ((comp.ports?.new_ports_count ?? 0) > 0 || (comp.ports?.closed_ports_count ?? 0) > 0) {
        narrative.push(
          `Ports: ${comp.ports?.new_ports_count ?? 0} newly opened, ${comp.ports?.closed_ports_count ?? 0} closed.`
        )
      }

      return narrative
    }

    drawParagraph(`Change Report: ${notification.domain}`, { size: 42, weight: 700, gap: 6 })
    drawParagraph(`${notification.title}`, { size: 26, weight: 600, color: '#374151', gap: 10 })
    drawParagraph(`Date: ${formatDate(notification.created_at)}  •  Event type: ${notification.type}`, {
      size: 20,
      color: '#6b7280',
      gap: 28,
    })

    drawSection('What Changed')
    const narrative = buildNarrative()
    if (narrative.length === 0) {
      drawParagraph('No significant changes detected between scans.', { size: 20, color: '#4b5563' })
    } else {
      narrative.forEach((line) => drawParagraph(`• ${line}`, { size: 21, indent: 4, gap: 6 }))
      cursorY += 14
    }

    drawSection('Key Metrics')
    drawParagraph(`Risk: ${summary.risk_1 ?? 0} -> ${summary.risk_2 ?? 0} (${summary.risk_delta ?? 0})`, {
      size: 22,
      weight: 600,
      color: '#1d4ed8',
      gap: 8,
    })
    drawParagraph(`Subdomains: +${summary.subdomains_added ?? 0}, -${summary.subdomains_removed ?? 0}`, { size: 21, gap: 6 })
    drawParagraph(`IP: +${summary.ips_added ?? 0}, -${summary.ips_removed ?? 0}`, { size: 21, gap: 6 })
    drawParagraph(`Alerts: ${summary.alerts_1 ?? 0} -> ${summary.alerts_2 ?? 0}`, { size: 21, gap: 20 })

    const drawListSection = (title: string, lines: string[]) => {
      if (lines.length === 0) return
      drawSection(title)
      lines.forEach((line) => drawParagraph(line, { size: 20, gap: 6 }))
      cursorY += 14
    }

    drawListSection('Subdomains', [
      `Removed: ${comp.subdomains?.only_in_1.length ?? 0}`,
      ...(comp.subdomains?.only_in_1 ?? []).slice(0, 10).map((v) => `• ${v}`),
      `Added: ${comp.subdomains?.only_in_2.length ?? 0}`,
      ...(comp.subdomains?.only_in_2 ?? []).slice(0, 10).map((v) => `• ${v}`),
    ])

    drawListSection('IP Addresses', [
      `Removed: ${comp.ips?.only_in_1.length ?? 0}`,
      ...(comp.ips?.only_in_1 ?? []).slice(0, 10).map((v) => `• ${v}`),
      `Added: ${comp.ips?.only_in_2.length ?? 0}`,
      ...(comp.ips?.only_in_2 ?? []).slice(0, 10).map((v) => `• ${v}`),
    ])

    drawListSection('SSL', [
      `Only in previous: ${comp.ssl?.hosts_only_in_1.length ?? 0}`,
      ...(comp.ssl?.hosts_only_in_1 ?? []).slice(0, 8).map((v) => `• ${v}`),
      `Only in current: ${comp.ssl?.hosts_only_in_2.length ?? 0}`,
      ...(comp.ssl?.hosts_only_in_2 ?? []).slice(0, 8).map((v) => `• ${v}`),
      ...((comp.ssl?.expired_changes ?? []).slice(0, 8).map(
        (c) => `• ${c.host}: ${c.was_expired_1 ? 'expired' : 'valid'} -> ${c.is_expired_2 ? 'expired' : 'valid'}`
      )),
    ])

    drawListSection('Ports', [
      `New ports: ${comp.ports?.new_ports_count ?? 0}`,
      `Closed ports: ${comp.ports?.closed_ports_count ?? 0}`,
      ...Object.entries(comp.ports?.by_ip ?? {})
        .slice(0, 10)
        .map(([ip, diff]) => `• ${ip}: -${diff.only_in_1.length}, +${diff.only_in_2.length}`),
    ])

    drawListSection('Alerts', [
      `Resolved: ${comp.alerts?.only_in_1.length ?? 0}`,
      ...(comp.alerts?.only_in_1 ?? []).slice(0, 8).map((a) => `• [${a.type ?? '-'}] ${a.message ?? '-'}`),
      `New: ${comp.alerts?.only_in_2.length ?? 0}`,
      ...(comp.alerts?.only_in_2 ?? []).slice(0, 8).map((a) => `• [${a.type ?? '-'}] ${a.message ?? '-'}`),
    ])

    drawFooter()
    pages.push(canvas.toDataURL('image/png'))

    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    pages.forEach((img, idx) => {
      if (idx > 0) doc.addPage('a4', 'portrait')
      doc.addImage(img, 'PNG', 0, 0, 210, 297)
    })
    doc.save(`report_${notification.domain}_${new Date().toISOString().slice(0, 10)}.pdf`)
  }

  const handleExportPdf = () => {
    void buildPdfReport()
    setExportAnchor(null)
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
                      Previous scan
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
                      Current scan
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
                Summary of changes
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
                  label={`Subdomains: +${summary.subdomains_added ?? 0} new, −${summary.subdomains_removed ?? 0} removed`}
                />
                <Chip
                  size="small"
                  label={`IP: +${summary.ips_added ?? 0} new, −${summary.ips_removed ?? 0} removed`}
                />
                <Chip size="small" label={`Alerts: ${summary.alerts_1 ?? 0} → ${summary.alerts_2 ?? 0}`} />
              </Box>
            </Paper>

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
              <Tab label="Subdomains" />
              <Tab label="IP" />
              <Tab label="SSL" />
              <Tab label="Ports" />
              <Tab label="Alerts" />
            </Tabs>

            {tab === 0 && comp.subdomains && (
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    Removed ({comp.subdomains.only_in_1.length})
                  </Typography>
                  <ListBlock items={comp.subdomains.only_in_1} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    Added ({comp.subdomains.only_in_2.length})
                  </Typography>
                  <ListBlock items={comp.subdomains.only_in_2} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Unchanged ({comp.subdomains.in_both.length})
                  </Typography>
                  <ListBlock items={comp.subdomains.in_both} />
                </Grid>
              </Grid>
            )}

            {tab === 1 && comp.ips && (
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    Removed ({comp.ips.only_in_1.length})
                  </Typography>
                  <ListBlock items={comp.ips.only_in_1} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    Added ({comp.ips.only_in_2.length})
                  </Typography>
                  <ListBlock items={comp.ips.only_in_2} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Unchanged ({comp.ips.in_both.length})
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
                      Only in previous ({comp.ssl.hosts_only_in_1.length})
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_only_in_1} />
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="secondary" gutterBottom>
                      Only in current ({comp.ssl.hosts_only_in_2.length})
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_only_in_2} />
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      In both ({comp.ssl.hosts_in_both.length})
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_in_both} />
                  </Grid>
                </Grid>
                {comp.ssl.expired_changes && comp.ssl.expired_changes.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="body2">
                        Certificate validity changes ({comp.ssl.expired_changes.length})
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Host</TableCell>
                              <TableCell>Previous</TableCell>
                              <TableCell>Current</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {comp.ssl.expired_changes.map((c, i) => (
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

            {tab === 3 && comp.ports && (
              <Box>
                <Typography variant="body2" gutterBottom>
                  New ports: {comp.ports.new_ports_count} | Closed: {comp.ports.closed_ports_count}
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
                              Closed
                            </Typography>
                            <ListBlock items={diff.only_in_1} />
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="success.main">
                              New
                            </Typography>
                            <ListBlock items={diff.only_in_2} />
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">
                              Unchanged
                            </Typography>
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

            {tab === 4 && comp.alerts && (
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    Resolved ({comp.alerts.only_in_1.length})
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
                    New ({comp.alerts.only_in_2.length})
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
              Failed to load comparison report. Scan data may have been deleted.
            </Typography>
          )
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          endIcon={<KeyboardArrowDownIcon />}
          onClick={(e) => setExportAnchor(e.currentTarget)}
          disabled={!notification || !report}
        >
          Export report
        </Button>
        <Menu
          anchorEl={exportAnchor}
          open={Boolean(exportAnchor)}
          onClose={() => setExportAnchor(null)}
          anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
          transformOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <MenuItem onClick={handleExportJson}>JSON (for programs)</MenuItem>
          <MenuItem onClick={handleExportTxt}>Text report (TXT)</MenuItem>
          <MenuItem onClick={handleExportPdf}>PDF</MenuItem>
        </Menu>
      </DialogActions>
    </Dialog>
  )
}

export default NotificationDetailDialog
