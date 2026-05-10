import { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { useTranslation } from 'react-i18next'
import { AuthProvider } from './contexts/AuthContext'
import SessionExpiryBridge from './components/auth/SessionExpiryBridge'
import Layout from './components/layout/Layout'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import HomePage from './pages/HomePage'
import ScanPage from './pages/ScanPage'
import HistoryPage from './pages/HistoryPage'
import SchedulesPage from './pages/SchedulesPage'
import InvestigationsPage from './pages/InvestigationsPage'
import NotificationsPage from './pages/NotificationsPage'
import InvestigationDetailPage from './pages/InvestigationDetailPage'
import InvestigationSharedPage from './pages/InvestigationSharedPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#0d9488',
      light: '#5eead4',
      dark: '#0f766e',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#ea580c',
      light: '#fb923c',
      dark: '#c2410c',
    },
    background: {
      default: '#f0f4f8',
      paper: '#ffffff',
    },
    divider: 'rgba(15, 23, 42, 0.08)',
  },
  typography: {
    fontFamily: '"Raleway", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontFamily: '"Unbounded", "Roboto", "Helvetica", "Arial", sans-serif',
      fontWeight: 700,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontFamily: '"Unbounded", "Roboto", "Helvetica", "Arial", sans-serif',
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontFamily: '"Unbounded", "Roboto", "Helvetica", "Arial", sans-serif',
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    h4: {
      fontFamily: '"Unbounded", "Roboto", "Helvetica", "Arial", sans-serif',
      fontWeight: 600,
    },
    h5: {
      fontFamily: '"Unbounded", "Roboto", "Helvetica", "Arial", sans-serif',
      fontWeight: 500,
    },
    h6: {
      fontFamily: '"Unbounded", "Roboto", "Helvetica", "Arial", sans-serif',
      fontWeight: 500,
    },
    button: {
      fontFamily: '"Raleway", "Roboto", "Helvetica", "Arial", sans-serif',
      fontWeight: 500,
      textTransform: 'none',
    },
    body1: {
      fontFamily: '"Raleway", "Roboto", "Helvetica", "Arial", sans-serif',
    },
    body2: {
      fontFamily: '"Raleway", "Roboto", "Helvetica", "Arial", sans-serif',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(15,23,42,0.06), 0 4px 14px rgba(15,23,42,0.06)',
          border: '1px solid rgba(15, 23, 42, 0.06)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 24px',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
})

function App() {
  const { t, i18n } = useTranslation()

  useEffect(() => {
    document.title = t('common.appTitle')
  }, [i18n.language, t])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <AuthProvider>
          <SessionExpiryBridge />
          <Layout>
            <ErrorBoundary>
              <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/scan" element={<ScanPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/schedules" element={<SchedulesPage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route path="/investigations" element={<InvestigationsPage />} />
              <Route path="/investigations/shared/:token" element={<InvestigationSharedPage />} />
              <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              </Routes>
            </ErrorBoundary>
          </Layout>
        </AuthProvider>
      </Router>
    </ThemeProvider>
  )
}

export default App
