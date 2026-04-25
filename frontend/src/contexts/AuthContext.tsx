import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { setAuthToken } from '../services/api'
import { isJwtExpired } from '../utils/jwt'

const TOKEN_KEY = 'netscout_token'
const USER_KEY = 'netscout_user'

export interface UserInfo {
  id: number
  email: string
  username: string
  email_notifications_enabled?: boolean
}

interface AuthContextType {
  user: UserInfo | null
  token: string | null
  isLoading: boolean
  login: (token: string, user: UserInfo) => void
  logout: () => void
  updateUser: (updates: Partial<UserInfo>) => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY)
    const storedUser = localStorage.getItem(USER_KEY)
    if (stored && storedUser) {
      try {
        if (isJwtExpired(stored)) {
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(USER_KEY)
          setAuthToken(null)
        } else {
          setToken(stored)
          setUser(JSON.parse(storedUser))
          setAuthToken(stored)
        }
      } catch {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        setAuthToken(null)
      }
    }
    setIsLoading(false)
  }, [])

  const login = useCallback((newToken: string, newUser: UserInfo) => {
    setToken(newToken)
    setUser(newUser)
    setAuthToken(newToken)
    localStorage.setItem(TOKEN_KEY, newToken)
    localStorage.setItem(USER_KEY, JSON.stringify(newUser))
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    setAuthToken(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }, [])

  const updateUser = useCallback((updates: Partial<UserInfo>) => {
    setUser((prev) => (prev ? { ...prev, ...updates } : null))
    const stored = localStorage.getItem(USER_KEY)
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        localStorage.setItem(USER_KEY, JSON.stringify({ ...parsed, ...updates }))
      } catch {
        // ignore
      }
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        updateUser,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
