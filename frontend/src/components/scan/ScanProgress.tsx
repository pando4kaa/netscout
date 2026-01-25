import { LinearProgress, Box, Typography } from '@mui/material'

interface ScanProgressProps {
  progress: number
  message?: string
}

const ScanProgress = ({ progress, message }: ScanProgressProps) => {
  return (
    <Box sx={{ width: '100%', p: 2 }}>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        {message || 'Scanning in progress...'}
      </Typography>
      <LinearProgress variant="determinate" value={progress} sx={{ mt: 1 }} />
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'right' }}>
        {progress}%
      </Typography>
    </Box>
  )
}

export default ScanProgress
