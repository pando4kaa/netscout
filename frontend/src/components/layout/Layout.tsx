import { Box, Typography } from '@mui/material'
import { useTranslation } from 'react-i18next'
import Header from './Header'

interface LayoutProps {
  children: React.ReactNode
}

const Layout = ({ children }: LayoutProps) => {
  const { t } = useTranslation()

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: '#f5f5f5' }}>
      <Header />
      <Box 
        component="main" 
        sx={{ 
          flex: 1,
          p: 4,
          bgcolor: 'background.default',
          minHeight: 'calc(100vh - 64px)',
        }}
      >
        {children}
      </Box>
      <Box component="footer" sx={{ px: 4, py: 1.5, bgcolor: 'background.paper', borderTop: '1px solid', borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary">
          {t('common.footerNotice')}
        </Typography>
      </Box>
    </Box>
  )
}

export default Layout
