import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
} from '@mui/material'
import { useTranslation } from 'react-i18next'
import { ScanResults } from '../../types'

interface SummaryTableProps {
  scanResults: ScanResults
}

const SummaryTable = ({ scanResults }: SummaryTableProps) => {
  const { t } = useTranslation()
  return (
    <TableContainer component={Paper}>
      <Typography variant="h6" sx={{ p: 2 }}>
        {t('results.scanSummary')}
      </Typography>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>{t('results.columnType')}</TableCell>
            <TableCell>{t('results.value')}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
            <TableCell>{t('common.domain')}</TableCell>
            <TableCell>{scanResults.target_domain}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>{t('results.subdomainsFound')}</TableCell>
            <TableCell>{scanResults.subdomains?.length || 0}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>{t('results.ipAddresses')}</TableCell>
            <TableCell>
              {scanResults.dns_info?.a_records?.join(', ') || t('common.notApplicable')}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default SummaryTable
