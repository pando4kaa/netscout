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
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  Divider,
  useTheme,
  useMediaQuery,
} from '@mui/material'
import { Link, useLocation } from 'react-router-dom'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import NotificationsIcon from '@mui/icons-material/Notifications'
import MenuIcon from '@mui/icons-material/Menu'
import HomeOutlinedIcon from '@mui/icons-material/HomeOutlined'
import TravelExploreOutlinedIcon from '@mui/icons-material/TravelExploreOutlined'
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined'
import ScheduleOutlinedIcon from '@mui/icons-material/ScheduleOutlined'
import ManageSearchOutlinedIcon from '@mui/icons-material/ManageSearchOutlined'
import NotificationsNoneOutlinedIcon from '@mui/icons-material/NotificationsNoneOutlined'
import LoginOutlinedIcon from '@mui/icons-material/LoginOutlined'
import PersonAddOutlinedIcon from '@mui/icons-material/PersonAddOutlined'
import { useTranslation } from 'react-i18next'
import { useState, useEffect, useMemo, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { authApi, notificationsApi } from '../../services/api'
import { AppLanguage, LANGUAGE_LABELS, SUPPORTED_LANGUAGES } from '../../i18n'

const NAV_BREAKPOINT: 'lg' | 'md' = 'lg'

const Header = () => {
  const theme = useTheme()
  const isCompactNav = useMediaQuery(theme.breakpoints.down(NAV_BREAKPOINT), { noSsr: true })
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const { user, isAuthenticated, logout, updateUser } = useAuth()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const currentLanguage = (i18n.language.split('-')[0] as AppLanguage) || 'uk'

  useEffect(() => {
    if (!isAuthenticated) return
    notificationsApi.getUnreadCount().then((d) => setUnreadCount(d.count)).catch(() => {})
  }, [isAuthenticated, location.pathname])

  useEffect(() => {
    if (!isCompactNav) setMobileOpen(false)
  }, [isCompactNav])

  const closeMobileDrawer = useCallback(() => setMobileOpen(false), [])

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget)
  const handleClose = () => setAnchorEl(null)
  const handleLogout = () => {
    handleClose()
    logout()
    closeMobileDrawer()
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

  const mainNavItems = useMemo(
    () =>
      [
        { text: t('navigation.home'), path: '/', match: (p: string) => p === '/', icon: HomeOutlinedIcon },
        { text: t('navigation.scan'), path: '/scan', match: (p: string) => p === '/scan', icon: TravelExploreOutlinedIcon },
        { text: t('navigation.history'), path: '/history', match: (p: string) => p === '/history', icon: HistoryOutlinedIcon },
        { text: t('navigation.schedules'), path: '/schedules', match: (p: string) => p === '/schedules', icon: ScheduleOutlinedIcon },
        ...(isAuthenticated
          ? [
              {
                text: t('navigation.investigations'),
                path: '/investigations',
                match: (p: string) => p.startsWith('/investigations'),
                icon: ManageSearchOutlinedIcon,
              },
            ]
          : []),
      ] as const,
    [isAuthenticated, t]
  )

  const accountMenu = (
    <>
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
    </>
  )

  const languageToggle = (
    <ToggleButtonGroup
      value={currentLanguage}
      exclusive
      size="small"
      onChange={handleLanguageChange}
      aria-label={t('navigation.language')}
      sx={{
        '& .MuiToggleButton-root': {
          color: 'inherit',
          borderColor: 'rgba(148,163,184,0.45)',
          px: 1,
          py: 0.25,
          '&.Mui-selected': {
            color: '#ecfeff',
            bgcolor: 'rgba(13,148,136,0.38)',
            borderColor: 'rgba(94,234,212,0.5)',
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
  )

  const drawer = (
    <Box sx={{ width: 280, pt: 1 }} role="navigation" aria-label={t('navigation.mainNavigation')}>
      <List dense>
        {mainNavItems.map((item) => {
          const Icon = item.icon
          const selected = item.match(location.pathname)
          return (
            <ListItemButton
              key={item.path}
              component={Link}
              to={item.path}
              selected={selected}
              onClick={closeMobileDrawer}
            >
              <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                <Icon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary={item.text} primaryTypographyProps={{ fontWeight: selected ? 600 : 400 }} />
            </ListItemButton>
          )
        })}
        {isAuthenticated && (
          <ListItemButton
            component={Link}
            to="/notifications"
            selected={location.pathname === '/notifications'}
            onClick={closeMobileDrawer}
          >
            <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
              <Badge badgeContent={unreadCount} color="error">
                <NotificationsNoneOutlinedIcon fontSize="small" />
              </Badge>
            </ListItemIcon>
            <ListItemText primary={t('navigation.notifications')} />
          </ListItemButton>
        )}
      </List>
      <Divider sx={{ my: 1 }} />
      {!isAuthenticated ? (
        <List dense>
          <ListItemButton component={Link} to="/login" onClick={closeMobileDrawer}>
            <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
              <LoginOutlinedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary={t('navigation.signIn')} />
          </ListItemButton>
          <ListItemButton component={Link} to="/register" onClick={closeMobileDrawer}>
            <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
              <PersonAddOutlinedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary={t('navigation.register')} />
          </ListItemButton>
        </List>
      ) : null}
      <Box sx={{ px: 2, py: 2 }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
          {t('navigation.language')}
        </Typography>
        <ToggleButtonGroup
          value={currentLanguage}
          exclusive
          fullWidth
          size="small"
          onChange={handleLanguageChange}
          aria-label={t('navigation.language')}
        >
          {SUPPORTED_LANGUAGES.map((language) => (
            <ToggleButton key={language} value={language} aria-label={LANGUAGE_LABELS[language]}>
              {LANGUAGE_LABELS[language]}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>
    </Box>
  )

  return (
    <>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          top: 0,
          zIndex: (muiTheme) => muiTheme.zIndex.appBar,
          background: 'linear-gradient(118deg, #0a101c 0%, #111b2e 40%, #0d1526 100%)',
          color: 'rgba(241, 245, 249, 0.94)',
          borderBottom: '1px solid rgba(45, 212, 191, 0.22)',
          boxShadow: '0 8px 28px rgba(8, 12, 22, 0.45)',
        }}
      >
        <Toolbar
          disableGutters
          sx={{
            px: { xs: 1, sm: 2 },
            gap: { xs: 0.5, sm: 1 },
            minHeight: { xs: 56, sm: 64 },
          }}
        >
          {isCompactNav && (
            <IconButton
              color="inherit"
              edge="start"
              aria-label={t('navigation.openMenu')}
              onClick={() => setMobileOpen(true)}
              size="large"
            >
              <MenuIcon />
            </IconButton>
          )}
          <Typography
            variant="h6"
            component={Link}
            to="/"
            color="inherit"
            sx={{
              fontWeight: 600,
              textDecoration: 'none',
              flexGrow: isCompactNav ? 1 : 0,
              minWidth: 0,
              mr: isCompactNav ? 0 : 2,
              typography: { xs: 'subtitle1', sm: 'h6' },
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {t('common.appName')}
          </Typography>

          {!isCompactNav && (
            <Box sx={{ display: 'flex', flexGrow: 1, flexWrap: 'wrap', gap: 0.5, alignItems: 'center' }}>
              {mainNavItems.map((item) => (
                <Button
                  key={item.path}
                  component={Link}
                  to={item.path}
                  color="inherit"
                  sx={{
                    textTransform: 'none',
                    fontWeight: item.match(location.pathname) ? 600 : 400,
                    borderBottom: item.match(location.pathname)
                      ? `2px solid ${theme.palette.primary.light}`
                      : '2px solid transparent',
                    borderRadius: 0,
                    px: { md: 1, lg: 1.5 },
                    py: 0.5,
                    color: 'inherit',
                    '&:hover': { bgcolor: 'rgba(94, 234, 212, 0.08)' },
                  }}
                >
                  {item.text}
                </Button>
              ))}
            </Box>
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.5, sm: 1 }, ml: isCompactNav ? 0 : 'auto' }}>
            {!isCompactNav && isAuthenticated && (
              <>
                <IconButton
                  component={Link}
                  to="/notifications"
                  color="inherit"
                  size="large"
                  aria-label={t('navigation.notifications')}
                  sx={{
                    ...(location.pathname === '/notifications' && {
                      bgcolor: 'rgba(94, 234, 212, 0.12)',
                      borderRadius: 1,
                    }),
                  }}
                >
                  <Badge badgeContent={unreadCount} color="error">
                    <NotificationsIcon />
                  </Badge>
                </IconButton>
                <IconButton color="inherit" onClick={handleMenu} size="large" aria-haspopup="true">
                  <AccountCircleIcon />
                </IconButton>
                <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose}>
                  {accountMenu}
                </Menu>
              </>
            )}
            {!isCompactNav && !isAuthenticated && (
              <>
                <Button component={Link} to="/login" color="inherit" sx={{ textTransform: 'none', display: { xs: 'none', sm: 'inline-flex' } }}>
                  {t('navigation.signIn')}
                </Button>
                <Button
                  component={Link}
                  to="/register"
                  color="inherit"
                  variant="outlined"
                  sx={{
                    textTransform: 'none',
                    borderColor: 'rgba(226, 232, 240, 0.45)',
                    color: 'rgba(241, 245, 249, 0.95)',
                    display: { xs: 'none', sm: 'inline-flex' },
                    '&:hover': { borderColor: theme.palette.primary.light, bgcolor: 'rgba(94, 234, 212, 0.08)' },
                  }}
                >
                  {t('navigation.register')}
                </Button>
                <IconButton component={Link} to="/login" color="inherit" size="large" sx={{ display: { xs: 'inline-flex', sm: 'none' } }} aria-label={t('navigation.signIn')}>
                  <LoginOutlinedIcon />
                </IconButton>
              </>
            )}
            {!isCompactNav && <Box sx={{ ml: 0.5 }}>{languageToggle}</Box>}
            {isCompactNav && isAuthenticated && (
              <>
                <IconButton
                  component={Link}
                  to="/notifications"
                  color="inherit"
                  size="large"
                  aria-label={t('navigation.notifications')}
                  sx={{
                    ...(location.pathname === '/notifications' && {
                      bgcolor: 'rgba(94, 234, 212, 0.12)',
                      borderRadius: 1,
                    }),
                  }}
                >
                  <Badge badgeContent={unreadCount} color="error">
                    <NotificationsIcon />
                  </Badge>
                </IconButton>
                <IconButton color="inherit" onClick={handleMenu} size="large" aria-haspopup="true">
                  <AccountCircleIcon />
                </IconButton>
                <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose}>
                  {accountMenu}
                </Menu>
              </>
            )}
            {isCompactNav && !isAuthenticated && (
              <IconButton
                component={Link}
                to="/login"
                color="inherit"
                size="large"
                aria-label={t('navigation.signIn')}
              >
                <LoginOutlinedIcon />
              </IconButton>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      {isCompactNav && (
        <Drawer
          anchor="left"
          open={mobileOpen}
          onClose={closeMobileDrawer}
          ModalProps={{ keepMounted: true }}
          PaperProps={{ sx: { pt: 1 } }}
        >
          {drawer}
        </Drawer>
      )}
    </>
  )
}

export default Header
