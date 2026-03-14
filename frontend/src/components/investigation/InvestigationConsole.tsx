import { useRef, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  IconButton,
  useTheme,
} from '@mui/material'
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep'

export type ConsoleLogLevel = 'INFO' | 'GRPH' | 'CMPL' | 'ERR'

export interface ConsoleLogEntry {
  id: string
  timestamp: string
  level: ConsoleLogLevel
  message: string
}

interface InvestigationConsoleProps {
  logs: ConsoleLogEntry[]
  onClear?: () => void
  maxHeight?: number
}

const levelColors: Record<ConsoleLogLevel, string> = {
  INFO: '#2196f3',
  GRPH: '#9c27b0',
  CMPL: '#4caf50',
  ERR: '#f44336',
}

const formatTime = () => {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

const InvestigationConsole = ({
  logs,
  onClear,
  maxHeight = 180,
}: InvestigationConsoleProps) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const theme = useTheme()
  const isDark = theme.palette.mode === 'dark'

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [logs])

  return (
    <Paper
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        overflow: 'hidden',
        bgcolor: isDark ? '#1e1e1e' : '#263238',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 1.5,
          py: 0.75,
          bgcolor: isDark ? '#2d2d2d' : '#37474f',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
          &gt;_ Console
        </Typography>
        <IconButton size="small" onClick={onClear} sx={{ color: 'text.secondary' }} title="Clear">
          <DeleteSweepIcon fontSize="small" />
        </IconButton>
      </Box>
      <Box
        ref={scrollRef}
        component="pre"
        sx={{
          m: 0,
          p: 1.5,
          fontFamily: 'monospace',
          fontSize: 12,
          lineHeight: 1.6,
          maxHeight,
          overflow: 'auto',
          color: isDark ? '#b0bec5' : '#90a4ae',
        }}
      >
        {logs.length === 0 ? (
          <Typography component="span" variant="caption" color="text.secondary">
            Run an enricher to see logs...
          </Typography>
        ) : (
          logs.map((entry) => (
            <Box
              key={entry.id}
              component="span"
              sx={{
                display: 'block',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              <Box
                component="span"
                sx={{
                  color: 'text.secondary',
                  mr: 1,
                }}
              >
                [{entry.timestamp}]
              </Box>
              <Box
                component="span"
                sx={{
                  color: levelColors[entry.level],
                  fontWeight: 600,
                  mr: 1,
                }}
              >
                {entry.level}
              </Box>
              <Box component="span">{entry.message}</Box>
            </Box>
          ))
        )}
      </Box>
    </Paper>
  )
}

export { formatTime }
export default InvestigationConsole
