import { useState } from 'react'
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Alert,
  Paper,
  Link,
} from '@mui/material'
import { Link as RouterLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { authApi } from '../services/api'

const LoginPage = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const sessionExpired = Boolean((location.state as { sessionExpired?: boolean } | null)?.sessionExpired)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const data = await authApi.login(email, password)
      login(data.access_token, data.user)
      navigate('/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="xs">
      <Box sx={{ py: 6 }}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" component="h1" gutterBottom align="center">
            Sign in
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 2 }}>
            Sign in to save scans and schedule recurring scans
          </Typography>
          {sessionExpired && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Your session has expired. Please sign in again.
            </Alert>
          )}
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <form onSubmit={handleSubmit}>
            <TextField
              margin="normal"
              required
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
            <TextField
              margin="normal"
              required
              fullWidth
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>
          <Typography variant="body2" color="text.secondary" align="center">
            Don&apos;t have an account?{' '}
            <Link component={RouterLink} to="/register">
              Register
            </Link>
          </Typography>
        </Paper>
      </Box>
    </Container>
  )
}

export default LoginPage
