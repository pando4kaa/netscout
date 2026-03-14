import { AppBar, Toolbar, Typography, Box, Button, IconButton, Menu, MenuItem } from '@mui/material'
import { Link, useLocation } from 'react-router-dom'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import { useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'

const Header = () => {
  const location = useLocation()
  const { user, isAuthenticated, logout } = useAuth()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget)
  const handleClose = () => setAnchorEl(null)
  const handleLogout = () => {
    handleClose()
    logout()
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
              <IconButton color="inherit" onClick={handleMenu} size="large" sx={{ ml: 1 }}>
                <AccountCircleIcon />
              </IconButton>
              <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose}>
                <MenuItem disabled>{user?.username}</MenuItem>
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
