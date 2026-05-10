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
import { useTranslation } from 'react-i18next'
import { SslInfo } from '../../types'
import HelpTooltip from '../common/HelpTooltip'
import { useLocaleFormatters } from '../../i18n/format'

interface SSLInfoPanelProps {
  sslInfo: SslInfo | null | undefined
}

const SSLInfoPanel = ({ sslInfo }: SSLInfoPanelProps) => {
  const { t } = useTranslation()
  const { formatDateTime } = useLocaleFormatters()

  if (!sslInfo?.certificates?.length) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary">{t('results.noSslData')}</Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {t('results.ssl')}
            <Chip label={sslInfo.certificates.length} size="small" color="primary" />
            <HelpTooltip topic="ssl_certificates" />
          </Typography>
          <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t('results.host')}</TableCell>
                  <TableCell>{t('results.validFrom')}</TableCell>
                  <TableCell>{t('results.validTo')}</TableCell>
                  <TableCell>{t('results.status')}</TableCell>
                  <TableCell>{t('results.colSan')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sslInfo.certificates.map((cert, idx) => (
                  <TableRow key={idx}>
                    <TableCell sx={{ fontFamily: 'monospace' }}>{cert.host}</TableCell>
                    <TableCell>
                      {cert.not_before ? formatDateTime(cert.not_before, { dateStyle: 'medium' }) : '—'}
                    </TableCell>
                    <TableCell>
                      {cert.not_after ? formatDateTime(cert.not_after, { dateStyle: 'medium' }) : '—'}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={cert.is_expired ? t('results.expired') : t('results.valid')}
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
