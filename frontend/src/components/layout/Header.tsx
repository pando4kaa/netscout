import { AppBar, Toolbar, Typography, Box } from '@mui/material'
import { Link } from 'react-router-dom'

const Header = () => {
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          NetScout OSINT System
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Link to="/" style={{ color: 'white', textDecoration: 'none' }}>
            Home
          </Link>
          <Link to="/scan" style={{ color: 'white', textDecoration: 'none' }}>
            Scan
          </Link>
          <Link to="/history" style={{ color: 'white', textDecoration: 'none' }}>
            History
          </Link>
        </Box>
      </Toolbar>
    </AppBar>
  )
}

export default Header
