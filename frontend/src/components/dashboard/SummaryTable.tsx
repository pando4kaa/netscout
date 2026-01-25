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
import { ScanResults } from '../../types'

interface SummaryTableProps {
  scanResults: ScanResults
}

const SummaryTable = ({ scanResults }: SummaryTableProps) => {
  return (
    <TableContainer component={Paper}>
      <Typography variant="h6" sx={{ p: 2 }}>
        Scan Summary
      </Typography>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            <TableCell>Value</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
            <TableCell>Domain</TableCell>
            <TableCell>{scanResults.target_domain}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Subdomains Found</TableCell>
            <TableCell>{scanResults.subdomains?.length || 0}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>IP Addresses</TableCell>
            <TableCell>
              {scanResults.dns_info?.a_records?.join(', ') || 'N/A'}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default SummaryTable
