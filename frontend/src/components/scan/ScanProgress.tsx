import { LinearProgress, Box, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { translateScanProgressMessage } from '../../i18n/scanProgress'

interface ScanProgressProps {
  progress: number
  message?: string
}

const ScanProgress = ({ progress, message }: ScanProgressProps) => {
  const { t } = useTranslation()
  const line = message
    ? translateScanProgressMessage(message, t)
    : t('scan.progress.inProgress')

  return (
    <Box sx={{ width: '100%', p: 2 }}>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        {line}
      </Typography>
      <LinearProgress variant="determinate" value={progress} sx={{ mt: 1 }} />
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'right' }}>
        {progress}%
      </Typography>
    </Box>
  )
}

export default ScanProgress
