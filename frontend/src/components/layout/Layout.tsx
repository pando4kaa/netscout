import { Box } from '@mui/material'
import Header from './Header'

interface LayoutProps {
  children: React.ReactNode
}

const Layout = ({ children }: LayoutProps) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />
      <Box
        component="main"
        sx={{
          flex: 1,
          width: '100%',
          maxWidth: '100%',
          boxSizing: 'border-box',
          px: { xs: 2, sm: 3, md: 4 },
          py: { xs: 2, sm: 3, md: 4 },
          bgcolor: 'background.default',
          minHeight: { xs: 'calc(100vh - 56px)', sm: 'calc(100vh - 64px)' },
        }}
      >
        {children}
      </Box>
    </Box>
  )
}

export default Layout
