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
import { PortScanResult } from '../../types'

interface PortScanPanelProps {
  portScan: PortScanResult[] | null | undefined
}

const PortScanPanel = ({ portScan }: PortScanPanelProps) => {
  if (!portScan?.length) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary">No port scan data available</Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {portScan.map((ps, idx) => (
        <Card key={idx}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {ps.ip}
              <Chip label={`${ps.open_ports?.length ?? 0} open`} size="small" color="primary" />
            </Typography>
            {ps.open_ports && ps.open_ports.length > 0 ? (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
                {ps.open_ports.map((op, i) => (
                  <Chip
                    key={i}
                    label={`${op.port} (${op.service || 'tcp'})`}
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Box>
            ) : (
              <Typography color="text.secondary">No open ports found</Typography>
            )}
          </CardContent>
        </Card>
      ))}
    </Box>
  )
}

export default PortScanPanel
