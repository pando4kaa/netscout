import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
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
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
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
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
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
  },
})

function App() {
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
