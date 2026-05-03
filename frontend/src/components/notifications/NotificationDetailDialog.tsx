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
import { useTranslation } from 'react-i18next'
import { jsPDF } from 'jspdf'
import { notificationsApi, type Notification, type NotificationReport } from '../../services/api'
import { useLocaleFormatters } from '../../i18n/format'

interface NotificationDetailDialogProps {
  open: boolean
  onClose: () => void
  notification: Notification | null
  onReportLoaded?: () => void
}

function ListBlock({ items, max = 30 }: { items: string[]; max?: number }) {
  const { t } = useTranslation()
  return (
    <Box sx={{ maxHeight: 150, overflow: 'auto' }}>
      {(items || []).slice(0, max).map((s, i) => (
        <Typography key={i} variant="caption" component="div" sx={{ fontFamily: 'monospace' }}>
          {s}
        </Typography>
      ))}
      {items && items.length > max && (
        <Typography variant="caption" color="text.secondary">
          {t('results.moreItems', { count: items.length - max })}
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
  const { t } = useTranslation()
  const { formatDateTime } = useLocaleFormatters()
  const [report, setReport] = useState<NotificationReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState(0)
  const formatDate = (iso: string | null | undefined) => formatDateTime(iso)

  type ComparisonPayload = {
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
  }

  const comp = report?.comparison as ComparisonPayload | undefined
  const summary = comp?.summary || {}

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
    lines.push(t('notifications.changeReportHeader', { domain: notification.domain }))
    lines.push('═'.repeat(60))
    lines.push('')
    lines.push(t('notifications.eventTypeLine', { type: notification.type }))
    lines.push(t('notifications.dateLine', { date: formatDate(notification.created_at) }))
    lines.push(t('notifications.titleLine', { title: notification.title }))
    lines.push(t('notifications.messageLine', { message: notification.message }))
    lines.push('')

    if (comp.scan_1 || comp.scan_2) {
      lines.push('─'.repeat(60))
      lines.push(t('notifications.scanComparison').toUpperCase())
      lines.push('─'.repeat(60))
      if (comp.scan_1) {
        lines.push(`${t('notifications.previousScan')}: ${formatDate(comp.scan_1.date)} | ${t('common.risk')}: ${comp.scan_1.risk_score ?? summary.risk_1}`)
      }
      if (comp.scan_2) {
        lines.push(`${t('notifications.currentScan')}:  ${formatDate(comp.scan_2.date)} | ${t('common.risk')}: ${comp.scan_2.risk_score ?? summary.risk_2}`)
      }
      lines.push('')
    }

    lines.push('─'.repeat(60))
    lines.push(t('notifications.summaryOfChanges').toUpperCase())
    lines.push('─'.repeat(60))
    if (summary.risk_delta !== undefined) {
      lines.push(`${t('common.risk')}: ${summary.risk_1} → ${summary.risk_2} (${summary.risk_delta >= 0 ? '+' : ''}${summary.risk_delta})`)
    }
    lines.push(t('notifications.subdomainDelta', { added: summary.subdomains_added ?? 0, removed: summary.subdomains_removed ?? 0 }))
    lines.push(t('history.ipsDelta', { added: summary.ips_added ?? 0, removed: summary.ips_removed ?? 0 }))
    lines.push(`${t('common.alerts')}: ${summary.alerts_1 ?? 0} → ${summary.alerts_2 ?? 0}`)
    lines.push('')

    if (comp.subdomains) {
      lines.push('─'.repeat(60))
      lines.push(t('common.subdomains').toUpperCase())
      lines.push('─'.repeat(60))
      lines.push(`${t('history.removed', { count: comp.subdomains.only_in_1.length })}:`)
      comp.subdomains.only_in_1.forEach((s) => lines.push(`  • ${s}`))
      lines.push(`${t('history.added', { count: comp.subdomains.only_in_2.length })}:`)
      comp.subdomains.only_in_2.forEach((s) => lines.push(`  • ${s}`))
      lines.push(`${t('history.unchangedWithCount', { count: comp.subdomains.in_both.length })}:`)
      comp.subdomains.in_both.slice(0, 20).forEach((s) => lines.push(`  • ${s}`))
      if (comp.subdomains.in_both.length > 20) {
        lines.push(`  ${t('results.moreItems', { count: comp.subdomains.in_both.length - 20 })}`)
      }
      lines.push('')
    }

    if (comp.ips) {
      lines.push('─'.repeat(60))
      lines.push(t('results.ipAddresses').toUpperCase())
      lines.push('─'.repeat(60))
      lines.push(`${t('history.removed', { count: comp.ips.only_in_1.length })}:`)
      comp.ips.only_in_1.forEach((ip) => lines.push(`  • ${ip}`))
      lines.push(`${t('history.added', { count: comp.ips.only_in_2.length })}:`)
      comp.ips.only_in_2.forEach((ip) => lines.push(`  • ${ip}`))
      lines.push('')
    }

    if (comp.ssl) {
      lines.push('─'.repeat(60))
      lines.push(t('results.sslCertificates').toUpperCase())
      lines.push('─'.repeat(60))
      lines.push(`${t('notifications.onlyInPrevious', { count: comp.ssl.hosts_only_in_1.length })}:`)
      comp.ssl.hosts_only_in_1.forEach((h) => lines.push(`  • ${h}`))
      lines.push(`${t('notifications.onlyInCurrent', { count: comp.ssl.hosts_only_in_2.length })}:`)
      comp.ssl.hosts_only_in_2.forEach((h) => lines.push(`  • ${h}`))
      if (comp.ssl.expired_changes?.length) {
        lines.push(`${t('notifications.validityChanges')}:`)
        comp.ssl.expired_changes.forEach((c) =>
          lines.push(`  • ${c.host}: ${c.was_expired_1 ? t('results.expired') : t('results.valid')} → ${c.is_expired_2 ? t('results.expired') : t('results.valid')}`)
        )
      }
      lines.push('')
    }

    if (comp.ports && comp.ports.by_ip && Object.keys(comp.ports.by_ip).length > 0) {
      lines.push('─'.repeat(60))
      lines.push(t('scan.tabs.ports').toUpperCase())
      lines.push('─'.repeat(60))
      lines.push(t('notifications.newClosedPorts', { newPorts: comp.ports.new_ports_count ?? 0, closedPorts: comp.ports.closed_ports_count ?? 0 }))
      Object.entries(comp.ports.by_ip).forEach(([ip, diff]) => {
        lines.push(`  ${ip}: −${diff.only_in_1?.length ?? 0} ${t('notifications.closedShort')}, +${diff.only_in_2?.length ?? 0} ${t('notifications.newShort')}`)
      })
      lines.push('')
    }

    if (comp.alerts) {
      lines.push('─'.repeat(60))
      lines.push(t('common.alerts').toUpperCase())
      lines.push('─'.repeat(60))
      lines.push(`${t('notifications.resolved', { count: comp.alerts.only_in_1.length })}:`)
      comp.alerts.only_in_1.forEach((a) => lines.push(`  • [${a.type}] ${a.message}${a.target ? ` (${a.target})` : ''}`))
      lines.push(`${t('history.added', { count: comp.alerts.only_in_2.length })}:`)
      comp.alerts.only_in_2.forEach((a) => lines.push(`  • [${a.type}] ${a.message}${a.target ? ` (${a.target})` : ''}`))
    }

    lines.push('')
    lines.push('═'.repeat(60))
    lines.push(t('notifications.reportFooter', { date: formatDateTime(new Date()) }))
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
      ctx.fillText(t('notifications.pdfReportTitle'), marginX, pageHeightPx - 24)
      const pageLabel = t('notifications.pageLabel', { page: pageNo })
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
      if (riskDelta > 0) narrative.push(t('notifications.riskIncreased', { delta: riskDelta }))
      if (riskDelta < 0) narrative.push(t('notifications.riskDecreased', { delta: Math.abs(riskDelta) }))
      if (riskDelta === 0) narrative.push(t('notifications.riskUnchanged'))

      if ((summary.subdomains_added ?? 0) > 0 || (summary.subdomains_removed ?? 0) > 0) {
        narrative.push(
          t('notifications.subdomainNarrative', {
            added: summary.subdomains_added ?? 0,
            removed: summary.subdomains_removed ?? 0,
          })
        )
      }
      if ((summary.ips_added ?? 0) > 0 || (summary.ips_removed ?? 0) > 0) {
        narrative.push(t('notifications.ipNarrative', { added: summary.ips_added ?? 0, removed: summary.ips_removed ?? 0 }))
      }
      if ((summary.alerts_2 ?? 0) !== (summary.alerts_1 ?? 0)) {
        narrative.push(t('notifications.alertCountChanged', { from: summary.alerts_1 ?? 0, to: summary.alerts_2 ?? 0 }))
      }
      if ((comp.ssl?.expired_changes?.length ?? 0) > 0) {
        narrative.push(t('notifications.sslStatusChanges', { count: comp.ssl?.expired_changes?.length ?? 0 }))
      }
      if ((comp.ports?.new_ports_count ?? 0) > 0 || (comp.ports?.closed_ports_count ?? 0) > 0) {
        narrative.push(
          t('notifications.portNarrative', {
            newPorts: comp.ports?.new_ports_count ?? 0,
            closedPorts: comp.ports?.closed_ports_count ?? 0,
          })
        )
      }

      return narrative
    }

    drawParagraph(t('notifications.changeReportFor', { domain: notification.domain }), { size: 42, weight: 700, gap: 6 })
    drawParagraph(`${notification.title}`, { size: 26, weight: 600, color: '#374151', gap: 10 })
    drawParagraph(`${t('common.date')}: ${formatDate(notification.created_at)}  •  ${t('notifications.eventType')}: ${notification.type}`, {
      size: 20,
      color: '#6b7280',
      gap: 28,
    })

    drawSection(t('notifications.whatChanged'))
    const narrative = buildNarrative()
    if (narrative.length === 0) {
      drawParagraph(t('notifications.noSignificantChanges'), { size: 20, color: '#4b5563' })
    } else {
      narrative.forEach((line) => drawParagraph(`• ${line}`, { size: 21, indent: 4, gap: 6 }))
      cursorY += 14
    }

    drawSection(t('notifications.keyMetrics'))
    drawParagraph(`${t('common.risk')}: ${summary.risk_1 ?? 0} -> ${summary.risk_2 ?? 0} (${summary.risk_delta ?? 0})`, {
      size: 22,
      weight: 600,
      color: '#1d4ed8',
      gap: 8,
    })
    drawParagraph(t('notifications.subdomainDeltaCompact', { added: summary.subdomains_added ?? 0, removed: summary.subdomains_removed ?? 0 }), { size: 21, gap: 6 })
    drawParagraph(t('notifications.ipDeltaCompact', { added: summary.ips_added ?? 0, removed: summary.ips_removed ?? 0 }), { size: 21, gap: 6 })
    drawParagraph(`${t('common.alerts')}: ${summary.alerts_1 ?? 0} -> ${summary.alerts_2 ?? 0}`, { size: 21, gap: 20 })

    const drawListSection = (title: string, lines: string[]) => {
      if (lines.length === 0) return
      drawSection(title)
      lines.forEach((line) => drawParagraph(line, { size: 20, gap: 6 }))
      cursorY += 14
    }

    drawListSection(t('common.subdomains'), [
      `${t('history.removedShort')}: ${comp.subdomains?.only_in_1.length ?? 0}`,
      ...(comp.subdomains?.only_in_1 ?? []).slice(0, 10).map((v) => `• ${v}`),
      `${t('history.addedShort')}: ${comp.subdomains?.only_in_2.length ?? 0}`,
      ...(comp.subdomains?.only_in_2 ?? []).slice(0, 10).map((v) => `• ${v}`),
    ])

    drawListSection(t('results.ipAddresses'), [
      `${t('history.removedShort')}: ${comp.ips?.only_in_1.length ?? 0}`,
      ...(comp.ips?.only_in_1 ?? []).slice(0, 10).map((v) => `• ${v}`),
      `${t('history.addedShort')}: ${comp.ips?.only_in_2.length ?? 0}`,
      ...(comp.ips?.only_in_2 ?? []).slice(0, 10).map((v) => `• ${v}`),
    ])

    drawListSection('SSL', [
      `${t('notifications.onlyInPreviousShort')}: ${comp.ssl?.hosts_only_in_1.length ?? 0}`,
      ...(comp.ssl?.hosts_only_in_1 ?? []).slice(0, 8).map((v) => `• ${v}`),
      `${t('notifications.onlyInCurrentShort')}: ${comp.ssl?.hosts_only_in_2.length ?? 0}`,
      ...(comp.ssl?.hosts_only_in_2 ?? []).slice(0, 8).map((v) => `• ${v}`),
      ...((comp.ssl?.expired_changes ?? []).slice(0, 8).map(
        (c) => `• ${c.host}: ${c.was_expired_1 ? t('results.expired') : t('results.valid')} -> ${c.is_expired_2 ? t('results.expired') : t('results.valid')}`
      )),
    ])

    drawListSection(t('scan.tabs.ports'), [
      `${t('notifications.newPorts')}: ${comp.ports?.new_ports_count ?? 0}`,
      `${t('notifications.closedPorts')}: ${comp.ports?.closed_ports_count ?? 0}`,
      ...Object.entries(comp.ports?.by_ip ?? {})
        .slice(0, 10)
        .map(([ip, diff]) => `• ${ip}: -${diff.only_in_1.length}, +${diff.only_in_2.length}`),
    ])

    drawListSection(t('common.alerts'), [
      `${t('notifications.resolvedShort')}: ${comp.alerts?.only_in_1.length ?? 0}`,
      ...(comp.alerts?.only_in_1 ?? []).slice(0, 8).map((a) => `• [${a.type ?? '-'}] ${a.message ?? '-'}`),
      `${t('notifications.newShort')}: ${comp.alerts?.only_in_2.length ?? 0}`,
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
                      {t('notifications.previousScan')}
                    </Typography>
                    <Typography variant="body2">{formatDate(comp.scan_1.date)}</Typography>
                    <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Chip size="small" label={`${t('common.risk')}: ${comp.scan_1.risk_score ?? summary.risk_1}`} />
                    </Box>
                  </Paper>
                </Grid>
              )}
              {comp.scan_2 && (
                <Grid item xs={6}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" color="secondary">
                      {t('notifications.currentScan')}
                    </Typography>
                    <Typography variant="body2">{formatDate(comp.scan_2.date)}</Typography>
                    <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Chip size="small" label={`${t('common.risk')}: ${comp.scan_2.risk_score ?? summary.risk_2}`} />
                    </Box>
                  </Paper>
                </Grid>
              )}
            </Grid>

            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                {t('notifications.summaryOfChanges')}
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
                    label={`${t('common.risk')}: ${summary.risk_1} → ${summary.risk_2} (${summary.risk_delta >= 0 ? '+' : ''}${summary.risk_delta})`}
                  />
                )}
                <Chip
                  size="small"
                  label={t('notifications.subdomainDelta', { added: summary.subdomains_added ?? 0, removed: summary.subdomains_removed ?? 0 })}
                />
                <Chip
                  size="small"
                  label={t('history.ipsDelta', { added: summary.ips_added ?? 0, removed: summary.ips_removed ?? 0 })}
                />
                <Chip size="small" label={`${t('common.alerts')}: ${summary.alerts_1 ?? 0} → ${summary.alerts_2 ?? 0}`} />
              </Box>
            </Paper>

            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
              <Tab label={t('common.subdomains')} />
              <Tab label={t('investigations.types.ip')} />
              <Tab label={t('notifications.tabSsl')} />
              <Tab label={t('scan.tabs.ports')} />
              <Tab label={t('common.alerts')} />
            </Tabs>

            {tab === 0 && comp.subdomains && (
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    {t('history.removed', { count: comp.subdomains.only_in_1.length })}
                  </Typography>
                  <ListBlock items={comp.subdomains.only_in_1} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    {t('history.added', { count: comp.subdomains.only_in_2.length })}
                  </Typography>
                  <ListBlock items={comp.subdomains.only_in_2} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {t('history.unchangedWithCount', { count: comp.subdomains.in_both.length })}
                  </Typography>
                  <ListBlock items={comp.subdomains.in_both} />
                </Grid>
              </Grid>
            )}

            {tab === 1 && comp.ips && (
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    {t('history.removed', { count: comp.ips.only_in_1.length })}
                  </Typography>
                  <ListBlock items={comp.ips.only_in_1} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="secondary" gutterBottom>
                    {t('history.added', { count: comp.ips.only_in_2.length })}
                  </Typography>
                  <ListBlock items={comp.ips.only_in_2} />
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {t('history.unchangedWithCount', { count: comp.ips.in_both.length })}
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
                      {t('notifications.onlyInPrevious', { count: comp.ssl.hosts_only_in_1.length })}
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_only_in_1} />
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="secondary" gutterBottom>
                      {t('notifications.onlyInCurrent', { count: comp.ssl.hosts_only_in_2.length })}
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_only_in_2} />
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {t('history.inBoth', { count: comp.ssl.hosts_in_both.length })}
                    </Typography>
                    <ListBlock items={comp.ssl.hosts_in_both} />
                  </Grid>
                </Grid>
                {comp.ssl.expired_changes && comp.ssl.expired_changes.length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="body2">
                        {t('notifications.certificateValidityChanges', { count: comp.ssl.expired_changes.length })}
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>{t('results.host')}</TableCell>
                              <TableCell>{t('notifications.previous')}</TableCell>
                              <TableCell>{t('notifications.current')}</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {comp.ssl.expired_changes.map((c, i) => (
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

            {tab === 3 && comp.ports && (
              <Box>
                <Typography variant="body2" gutterBottom>
                  {t('notifications.newClosedPorts', {
                    newPorts: comp.ports.new_ports_count,
                    closedPorts: comp.ports.closed_ports_count,
                  })}
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
                              {t('notifications.closedShort')}
                            </Typography>
                            <ListBlock items={diff.only_in_1} />
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="success.main">
                              {t('notifications.newShort')}
                            </Typography>
                            <ListBlock items={diff.only_in_2} />
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">
                              {t('history.unchanged')}
                            </Typography>
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

            {tab === 4 && comp.alerts && (
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="primary" gutterBottom>
                    {t('notifications.resolved', { count: comp.alerts.only_in_1.length })}
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
                    {t('history.added', { count: comp.alerts.only_in_2.length })}
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
              {t('notifications.failedToLoadReport')}
            </Typography>
          )
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('common.close')}</Button>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          endIcon={<KeyboardArrowDownIcon />}
          onClick={(e) => setExportAnchor(e.currentTarget)}
          disabled={!notification || !report}
        >
          {t('common.export')}
        </Button>
        <Menu
          anchorEl={exportAnchor}
          open={Boolean(exportAnchor)}
          onClose={() => setExportAnchor(null)}
          anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
          transformOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <MenuItem onClick={handleExportJson}>{t('notifications.exportJsonPrograms')}</MenuItem>
          <MenuItem onClick={handleExportTxt}>{t('notifications.exportTextReport')}</MenuItem>
          <MenuItem onClick={handleExportPdf}>{t('notifications.exportPdf')}</MenuItem>
        </Menu>
      </DialogActions>
    </Dialog>
  )
}

export default NotificationDetailDialog
