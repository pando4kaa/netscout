import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material'
import { SslInfo } from '../../types'

interface SSLInfoPanelProps {
  sslInfo: SslInfo | null | undefined
}

const SSLInfoPanel = ({ sslInfo }: SSLInfoPanelProps) => {
  if (!sslInfo?.certificates?.length) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary">No SSL certificate data available</Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            SSL Certificates
            <Chip label={sslInfo.certificates.length} size="small" color="primary" />
          </Typography>
          <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Host</TableCell>
                  <TableCell>Valid From</TableCell>
                  <TableCell>Valid To</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>SAN</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sslInfo.certificates.map((cert, idx) => (
                  <TableRow key={idx}>
                    <TableCell sx={{ fontFamily: 'monospace' }}>{cert.host}</TableCell>
                    <TableCell>
                      {cert.not_before
                        ? new Date(cert.not_before).toLocaleDateString('uk-UA')
                        : '—'}
                    </TableCell>
                    <TableCell>
                      {cert.not_after
                        ? new Date(cert.not_after).toLocaleDateString('uk-UA')
                        : '—'}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={cert.is_expired ? 'Expired' : 'Valid'}
                        color={cert.is_expired ? 'error' : 'success'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, maxWidth: 300 }}>
                        {cert.san?.slice(0, 3).map((s, i) => (
                          <Chip key={i} label={s} size="small" variant="outlined" />
                        ))}
                        {(cert.san?.length ?? 0) > 3 && (
                          <Chip label={`+${cert.san!.length - 3}`} size="small" />
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  )
}

export default SSLInfoPanel
