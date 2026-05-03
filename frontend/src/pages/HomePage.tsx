import { Container, Typography, Box } from '@mui/material'
import { useTranslation } from 'react-i18next'
import DomainInput from '../components/scan/DomainInput'

const HomePage = () => {
  const { t } = useTranslation()

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 6 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ mb: 2 }}>
          {t('common.appTitle')}
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 4, fontSize: '1.1rem' }}>
          {t('home.subtitle')}
        </Typography>
        <Box sx={{ mt: 4 }}>
          <DomainInput />
        </Box>
      </Box>
    </Container>
  )
}

export default HomePage
