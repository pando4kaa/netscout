import { AppBar, Toolbar, Typography, Box, Button, IconButton, Menu, MenuItem, Badge, Switch, ListItemText } from '@mui/material'
import { Link, useLocation } from 'react-router-dom'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import NotificationsIcon from '@mui/icons-material/Notifications'
import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { authApi, notificationsApi } from '../../services/api'

const Header = () => {
  const location = useLocation()
  const { user, isAuthenticated, logout, updateUser } = useAuth()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [unreadCount, setUnreadCount] = useState(0)

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

  return (
    <AppBar position="static" elevation={2}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
          NetScout
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
            Home
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
            Scan
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
            History
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
            Schedules
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
              Investigations
            </Button>
          )}
          {isAuthenticated ? (
            <>
              <IconButton
                component={Link}
                to="/notifications"
                color="inherit"
                size="large"
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
                  <ListItemText primary="Email-сповіщення про зміни" secondary="Надсилати на пошту" />
                  <Switch
                    checked={user?.email_notifications_enabled ?? false}
                    onChange={handleEmailNotificationsToggle}
                    size="small"
                    color="primary"
                  />
                </MenuItem>
                <MenuItem onClick={handleLogout}>Logout</MenuItem>
              </Menu>
            </>
          ) : (
            <>
              <Button component={Link} to="/login" color="inherit" sx={{ textTransform: 'none' }}>
                Sign in
              </Button>
              <Button component={Link} to="/register" color="inherit" variant="outlined" sx={{ textTransform: 'none', borderColor: 'rgba(255,255,255,0.5)' }}>
                Register
              </Button>
            </>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  )
}

export default Header
