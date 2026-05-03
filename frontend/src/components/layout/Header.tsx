import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Badge,
  Switch,
  ListItemText,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material'
import { Link, useLocation } from 'react-router-dom'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import NotificationsIcon from '@mui/icons-material/Notifications'
import { useTranslation } from 'react-i18next'
import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { authApi, notificationsApi } from '../../services/api'
import { AppLanguage, LANGUAGE_LABELS, SUPPORTED_LANGUAGES } from '../../i18n'

const Header = () => {
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const { user, isAuthenticated, logout, updateUser } = useAuth()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [unreadCount, setUnreadCount] = useState(0)
  const currentLanguage = (i18n.language.split('-')[0] as AppLanguage) || 'uk'

  useEffect(() => {
    if (!isAuthenticated) return
    notificationsApi.getUnreadCount().then((d) => setUnreadCount(d.count)).catch(() => {})
  }, [isAuthenticated, location.pathname])

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget)
  const handleClose = () => setAnchorEl(null)
  const handleLogout = () => {
    handleClose()
    logout()
  }

  const handleEmailNotificationsToggle = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const enabled = e.target.checked
    try {
      await authApi.updateEmailNotifications(enabled)
      updateUser({ email_notifications_enabled: enabled })
    } catch {
      // revert on error
    }
  }

  const handleLanguageChange = (_: React.MouseEvent<HTMLElement>, nextLanguage: AppLanguage | null) => {
    if (nextLanguage) {
      void i18n.changeLanguage(nextLanguage)
    }
  }

  return (
    <AppBar position="static" elevation={2}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
          {t('common.appName')}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Button
            component={Link}
            to="/"
            color="inherit"
            sx={{
              textTransform: 'none',
              fontWeight: location.pathname === '/' ? 600 : 400,
              borderBottom: location.pathname === '/' ? '2px solid white' : 'none',
              borderRadius: 0,
            }}
          >
            {t('navigation.home')}
          </Button>
          <Button
            component={Link}
            to="/scan"
            color="inherit"
            sx={{
              textTransform: 'none',
              fontWeight: location.pathname === '/scan' ? 600 : 400,
              borderBottom: location.pathname === '/scan' ? '2px solid white' : 'none',
              borderRadius: 0,
            }}
          >
            {t('navigation.scan')}
          </Button>
          <Button
            component={Link}
            to="/history"
            color="inherit"
            sx={{
              textTransform: 'none',
              fontWeight: location.pathname === '/history' ? 600 : 400,
              borderBottom: location.pathname === '/history' ? '2px solid white' : 'none',
              borderRadius: 0,
            }}
          >
            {t('navigation.history')}
          </Button>
          <Button
            component={Link}
            to="/schedules"
            color="inherit"
            sx={{
              textTransform: 'none',
              fontWeight: location.pathname === '/schedules' ? 600 : 400,
              borderBottom: location.pathname === '/schedules' ? '2px solid white' : 'none',
              borderRadius: 0,
            }}
          >
            {t('navigation.schedules')}
          </Button>
          {isAuthenticated && (
            <Button
              component={Link}
              to="/investigations"
              color="inherit"
              sx={{
                textTransform: 'none',
                fontWeight: location.pathname.startsWith('/investigations') ? 600 : 400,
                borderBottom: location.pathname.startsWith('/investigations') ? '2px solid white' : 'none',
                borderRadius: 0,
              }}
            >
              {t('navigation.investigations')}
            </Button>
          )}
          {isAuthenticated ? (
            <>
              <IconButton
                component={Link}
                to="/notifications"
                color="inherit"
                size="large"
                aria-label={t('navigation.notifications')}
                sx={{
                  ml: 1,
                  ...(location.pathname === '/notifications' && {
                    bgcolor: 'rgba(255,255,255,0.1)',
                    borderRadius: 1,
                  }),
                }}
              >
                <Badge badgeContent={unreadCount} color="error">
                  <NotificationsIcon />
                </Badge>
              </IconButton>
              <IconButton color="inherit" onClick={handleMenu} size="large">
                <AccountCircleIcon />
              </IconButton>
              <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose}>
                <MenuItem disabled>{user?.username}</MenuItem>
                <MenuItem disableRipple>
                  <ListItemText
                    primary={t('navigation.emailNotifications')}
                    secondary={t('navigation.emailNotificationsHint')}
                  />
                  <Switch
                    checked={user?.email_notifications_enabled ?? false}
                    onChange={handleEmailNotificationsToggle}
                    size="small"
                    color="primary"
                  />
                </MenuItem>
                <MenuItem onClick={handleLogout}>{t('navigation.logout')}</MenuItem>
              </Menu>
            </>
          ) : (
            <>
              <Button component={Link} to="/login" color="inherit" sx={{ textTransform: 'none' }}>
                {t('navigation.signIn')}
              </Button>
              <Button component={Link} to="/register" color="inherit" variant="outlined" sx={{ textTransform: 'none', borderColor: 'rgba(255,255,255,0.5)' }}>
                {t('navigation.register')}
              </Button>
            </>
          )}
          <ToggleButtonGroup
            value={currentLanguage}
            exclusive
            size="small"
            onChange={handleLanguageChange}
            aria-label={t('navigation.language')}
            sx={{
              ml: 1,
              '& .MuiToggleButton-root': {
                color: 'inherit',
                borderColor: 'rgba(255,255,255,0.4)',
                px: 1,
                py: 0.25,
                '&.Mui-selected': {
                  color: 'primary.contrastText',
                  bgcolor: 'rgba(255,255,255,0.2)',
                },
              },
            }}
          >
            {SUPPORTED_LANGUAGES.map((language) => (
              <ToggleButton key={language} value={language} aria-label={LANGUAGE_LABELS[language]}>
                {LANGUAGE_LABELS[language]}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>
      </Toolbar>
    </AppBar>
  )
}

export default Header
