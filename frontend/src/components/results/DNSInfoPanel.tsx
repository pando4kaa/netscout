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
  Divider,
} from '@mui/material'
import { DNSInfo } from '../../types'

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
      {/* A Records (IPv4) */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            A Records (IPv4)
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

      {/* TXT Records */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            TXT Records
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

      {/* CNAME Records */}
      {dnsInfo.cname_records && dnsInfo.cname_records.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              CNAME Records
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
