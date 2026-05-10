import { Component, ErrorInfo, ReactNode } from 'react'
import { Box, Typography, Button, Paper } from '@mui/material'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import { useTranslation } from 'react-i18next'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

function DefaultErrorFallback({ error, onReset }: { error: Error; onReset: () => void }) {
  const { t } = useTranslation()

  return (
    <Box sx={{ p: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
      <Paper sx={{ p: 4, maxWidth: 500, textAlign: 'center' }}>
        <ErrorOutlineIcon sx={{ fontSize: 48, color: 'error.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {t('errors.unexpected')}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }} component="pre">
          {error.message}
        </Typography>
        <Button variant="contained" onClick={onReset}>
          {t('errors.tryAgain')}
        </Button>
      </Paper>
    </Box>
  )
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback
      }
      return <DefaultErrorFallback error={this.state.error} onReset={this.handleReset} />
    }
    return this.props.children
  }
}
