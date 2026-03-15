import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material'
import { DNSInfo } from '../../types'
import HelpTooltip from '../common/HelpTooltip'

interface DNSInfoPanelProps {
  dnsInfo: DNSInfo
}

const DNSInfoPanel = ({ dnsInfo }: DNSInfoPanelProps) => {
  if (dnsInfo.error) {
    return (
      <Card>
        <CardContent>
          <Typography color="error">DNS Error: {dnsInfo.error}</Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="h6">DNS Records</Typography>
        <HelpTooltip topic="dns" />
      </Box>
      {/* A Records (IPv4) */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            A Records (IPv4)
            <HelpTooltip topic="dns_a_record" />
            <Chip label={dnsInfo.a_records?.length || 0} size="small" color="primary" />
          </Typography>
          {dnsInfo.a_records && dnsInfo.a_records.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {dnsInfo.a_records.map((ip, index) => (
                <Chip key={index} label={ip} variant="outlined" />
              ))}
            </Box>
          ) : (
            <Typography color="text.secondary">No A records found</Typography>
          )}
        </CardContent>
      </Card>

      {/* AAAA Records (IPv6) */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            AAAA Records (IPv6)
            <HelpTooltip topic="dns_aaaa_record" />
            <Chip label={dnsInfo.aaaa_records?.length || 0} size="small" color="secondary" />
          </Typography>
          {dnsInfo.aaaa_records && dnsInfo.aaaa_records.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {dnsInfo.aaaa_records.map((ip, index) => (
                <Chip key={index} label={ip} variant="outlined" sx={{ maxWidth: 300 }} />
              ))}
            </Box>
          ) : (
            <Typography color="text.secondary">No AAAA records found</Typography>
          )}
        </CardContent>
      </Card>

      {/* MX Records */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            MX Records (Mail Servers)
            <HelpTooltip topic="dns_mx_record" />
            <Chip label={dnsInfo.mx_records?.length || 0} size="small" color="info" />
          </Typography>
          {dnsInfo.mx_records && dnsInfo.mx_records.length > 0 ? (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Priority</TableCell>
                    <TableCell>Mail Server</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {dnsInfo.mx_records.map((mx, index) => (
                    <TableRow key={index}>
                      <TableCell>{mx.priority}</TableCell>
                      <TableCell>{mx.host}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography color="text.secondary">No MX records found</Typography>
          )}
        </CardContent>
      </Card>

      {/* NS Records */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            NS Records (Name Servers)
            <HelpTooltip topic="dns_ns_record" />
            <Chip label={dnsInfo.ns_records?.length || 0} size="small" color="success" />
          </Typography>
          {dnsInfo.ns_records && dnsInfo.ns_records.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {dnsInfo.ns_records.map((ns, index) => (
                <Chip key={index} label={ns} variant="outlined" color="success" />
              ))}
            </Box>
          ) : (
            <Typography color="text.secondary">No NS records found</Typography>
          )}
        </CardContent>
      </Card>

      {/* Email Security (SPF, DMARC, DKIM) */}
      {dnsInfo.email_security && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              Email Security (SPF / DMARC / DKIM)
              <HelpTooltip topic="dns_email_security" />
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  label={dnsInfo.email_security.spf_present ? 'SPF' : 'No SPF'}
                  size="small"
                  color={dnsInfo.email_security.spf_present ? 'success' : 'warning'}
                />
                <Chip
                  label={dnsInfo.email_security.dmarc_present ? `DMARC (${dnsInfo.email_security.dmarc_policy || '?'})` : 'No DMARC'}
                  size="small"
                  color={dnsInfo.email_security.dmarc_present ? 'success' : 'error'}
                />
                {dnsInfo.email_security.dkim_hints && dnsInfo.email_security.dkim_hints.length > 0 && (
                  <Chip label="DKIM hints" size="small" color="info" />
                )}
              </Box>
              {dnsInfo.email_security.spf_record && (
                <Typography variant="caption" sx={{ fontFamily: 'monospace', wordBreak: 'break-all', display: 'block' }}>
                  SPF: {dnsInfo.email_security.spf_record}
                </Typography>
              )}
              {dnsInfo.email_security.dmarc_record && (
                <Typography variant="caption" sx={{ fontFamily: 'monospace', wordBreak: 'break-all', display: 'block' }}>
                  DMARC: {dnsInfo.email_security.dmarc_record}
                </Typography>
              )}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* TXT Records */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            TXT Records
            <HelpTooltip topic="dns_txt_record" />
            <Chip label={dnsInfo.txt_records?.length || 0} size="small" color="warning" />
          </Typography>
          {dnsInfo.txt_records && dnsInfo.txt_records.length > 0 ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {dnsInfo.txt_records.map((txt, index) => (
                <Paper key={index} variant="outlined" sx={{ p: 1.5 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontFamily: 'monospace',
                      wordBreak: 'break-all',
                      fontSize: '0.85rem',
                    }}
                  >
                    {txt}
                  </Typography>
                </Paper>
              ))}
            </Box>
          ) : (
            <Typography color="text.secondary">No TXT records found</Typography>
          )}
        </CardContent>
      </Card>

      {/* SOA Records */}
      {dnsInfo.soa_records && dnsInfo.soa_records.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              SOA Records
              <HelpTooltip topic="dns_soa_record" />
              <Chip label={dnsInfo.soa_records.length} size="small" />
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {dnsInfo.soa_records.map((soa, index) => (
                <Typography key={index} variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  {soa}
                </Typography>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* PTR Records (Reverse DNS) */}
      {dnsInfo.ptr_records && Object.keys(dnsInfo.ptr_records).length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              PTR Records (Reverse DNS)
              <HelpTooltip topic="dns_ptr_record" />
              <Chip label={Object.keys(dnsInfo.ptr_records).length} size="small" />
            </Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>IP</TableCell>
                    <TableCell>Hostname</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(dnsInfo.ptr_records).map(([ip, hostname]) => (
                    <TableRow key={ip}>
                      <TableCell>{ip}</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace' }}>{hostname}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Zone Transfer (AXFR) */}
      {dnsInfo.zone_transfer_attempted && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              Zone Transfer (AXFR)
              <HelpTooltip topic="dns_zone_transfer" />
              <Chip
                label={dnsInfo.zone_transfer_available ? 'Available' : 'Not available'}
                size="small"
                color={dnsInfo.zone_transfer_available ? 'error' : 'default'}
              />
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Attempted: {dnsInfo.zone_transfer_attempted ? 'Yes' : 'No'}
              {dnsInfo.zone_transfer_error && ` • Error: ${dnsInfo.zone_transfer_error}`}
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* CNAME Records */}
      {dnsInfo.cname_records && dnsInfo.cname_records.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              CNAME Records
              <HelpTooltip topic="dns_cname_record" />
              <Chip label={dnsInfo.cname_records.length} size="small" />
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {dnsInfo.cname_records.map((cname, index) => (
                <Chip key={index} label={cname} variant="outlined" />
              ))}
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}

export default DNSInfoPanel
