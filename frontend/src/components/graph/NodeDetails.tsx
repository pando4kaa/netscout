import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
} from '@mui/material'
import { useTranslation } from 'react-i18next'

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
  const { t } = useTranslation()
  if (!nodeData) return null

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t('results.nodeDetails')}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography>
            <strong>{t('results.nodeIdLabel')}:</strong> {nodeData.id}
          </Typography>
          <Typography>
            <strong>{t('results.label')}:</strong> {nodeData.label}
          </Typography>
          <Typography>
            <strong>{t('results.type')}:</strong> {nodeData.type}
          </Typography>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('common.close')}</Button>
      </DialogActions>
    </Dialog>
  )
}

export default NodeDetails
