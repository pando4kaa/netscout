import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { setSessionExpiredHandler } from '../../services/api'

/**
 * Registers axios 401 handler: clear session and redirect to login (except on auth pages).
 */
export default function SessionExpiryBridge() {
  const navigate = useNavigate()
  const { logout } = useAuth()

  useEffect(() => {
    const handler = () => {
      logout()
      const path = window.location.pathname
      if (path !== '/login' && path !== '/register') {
        navigate('/login', { replace: true, state: { sessionExpired: true } })
      }
    }
    setSessionExpiredHandler(handler)
    return () => setSessionExpiredHandler(null)
  }, [logout, navigate])

  return null
}
