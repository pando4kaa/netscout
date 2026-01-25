import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
} from '@mui/material'

interface NodeDetailsProps {
  open: boolean
  onClose: () => void
  nodeData: {
    id: string
    label: string
    type: string
    [key: string]: any
  } | null
}

const NodeDetails = ({ open, onClose, nodeData }: NodeDetailsProps) => {
  if (!nodeData) return null

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Node Details</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography>
            <strong>ID:</strong> {nodeData.id}
          </Typography>
          <Typography>
            <strong>Label:</strong> {nodeData.label}
          </Typography>
          <Typography>
            <strong>Type:</strong> {nodeData.type}
          </Typography>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}

export default NodeDetails
