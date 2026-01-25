import { Box, Drawer, List, ListItem, ListItemButton, ListItemText, Toolbar } from '@mui/material'
import { Link, useLocation } from 'react-router-dom'

const drawerWidth = 240

const Sidebar = () => {
  const location = useLocation()

  const menuItems = [
    { text: 'Home', path: '/' },
    { text: 'Scan', path: '/scan' },
    { text: 'History', path: '/history' },
  ]

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
        },
      }}
    >
      <Toolbar />
      <Box sx={{ overflow: 'auto' }}>
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                component={Link}
                to={item.path}
                selected={location.pathname === item.path}
              >
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
    </Drawer>
  )
}

export default Sidebar
