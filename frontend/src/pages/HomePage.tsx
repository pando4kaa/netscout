import { Container, Typography, Box } from '@mui/material'
import { useTranslation } from 'react-i18next'
import DomainInput from '../components/scan/DomainInput'

const HomePage = () => {
  const { t } = useTranslation()

  return (
    <Container maxWidth="md" sx={{ px: { xs: 2, sm: 3 } }}>
      <Box sx={{ py: { xs: 3, sm: 4, md: 6 } }}>
        <Typography
          variant="h3"
          component="h1"
          gutterBottom
          sx={{ mb: 2, typography: { xs: 'h4', sm: 'h3' } }}
        >
          {t('common.appTitle')}
        </Typography>
        <Typography
          variant="body1"
          color="text.secondary"
          paragraph
          sx={{ mb: { xs: 3, md: 4 }, fontSize: { xs: '1rem', sm: '1.1rem' } }}
        >
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
