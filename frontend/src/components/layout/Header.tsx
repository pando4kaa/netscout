import { AppBar, Toolbar, Typography, Box, Button } from '@mui/material'
import { Link, useLocation } from 'react-router-dom'

const Header = () => {
  const location = useLocation()

  return (
    <AppBar position="static" elevation={2}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
          NetScout
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
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
        </Box>
      </Toolbar>
    </AppBar>
  )
}

export default Header
