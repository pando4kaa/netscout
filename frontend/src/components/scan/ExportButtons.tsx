import { Button, ButtonGroup } from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import { jsPDF } from 'jspdf'
import { ScanResults } from '../../types'

interface ExportButtonsProps {
  scanResults: ScanResults
}

const ExportButtons = ({ scanResults }: ExportButtonsProps) => {
  const exportJson = () => {
    const blob = new Blob([JSON.stringify(scanResults, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `netscout_${scanResults.target_domain}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportCsv = () => {
    const rows: string[][] = [['type', 'value']]
    rows.push(['domain', scanResults.target_domain])
    for (const sub of scanResults.subdomains || []) {
      rows.push(['subdomain', sub])
    }
    const dns = scanResults.dns_info || {}
    for (const ip of dns.a_records || []) {
      rows.push(['ip', ip])
    }
    for (const ip of dns.aaaa_records || []) {
      rows.push(['ipv6', ip])
    }
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `netscout_${scanResults.target_domain}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportPdf = () => {
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const pageW = doc.internal.pageSize.getWidth()
    let y = 15
    const lineH = 7
    const margin = 15

    const addSection = (title: string, lines: string[]) => {
      if (y > 250) {
        doc.addPage()
        y = 15
      }
      doc.setFontSize(14)
      doc.setFont('helvetica', 'bold')
      doc.text(title, margin, y)
      y += lineH + 2
      doc.setFontSize(10)
      doc.setFont('helvetica', 'normal')
      for (const line of lines) {
        if (y > 280) {
          doc.addPage()
          y = 15
        }
        doc.text(line.substring(0, 90), margin, y)
        y += lineH
      }
      y += 5
    }

    doc.setFontSize(18)
    doc.setFont('helvetica', 'bold')
    doc.text(`NetScout Report: ${scanResults.target_domain}`, margin, y)
    y += 12
    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.text(`Scan date: ${scanResults.scan_date || new Date().toISOString().slice(0, 10)}`, margin, y)
    y += 15

    addSection('Subdomains', scanResults.subdomains || [])
    const dns = scanResults.dns_info || {}
    addSection('A Records (IPv4)', dns.a_records || [])
    addSection('AAAA Records (IPv6)', dns.aaaa_records || [])
    addSection('NS Records', dns.ns_records || [])
    addSection('MX Records', (dns.mx_records || []).map((m) => `${m.priority} ${m.host}`))
    if (scanResults.port_scan?.length) {
      const portLines = scanResults.port_scan.flatMap((ps) =>
        (ps.open_ports || []).map((op) => `${ps.ip}:${op.port} (${op.service || 'tcp'})`)
      )
      addSection('Open Ports', portLines)
    }
    if (scanResults.alerts?.length) {
      addSection('Alerts', scanResults.alerts.map((a) => `[${a.level}] ${a.message}`))
    }

    doc.save(`netscout_${scanResults.target_domain}.pdf`)
  }

  return (
    <ButtonGroup size="small" variant="outlined">
      <Button startIcon={<DownloadIcon />} onClick={exportJson}>
        JSON
      </Button>
      <Button startIcon={<DownloadIcon />} onClick={exportCsv}>
        CSV
      </Button>
      <Button startIcon={<DownloadIcon />} onClick={exportPdf}>
        PDF
      </Button>
    </ButtonGroup>
  )
}

export default ExportButtons
