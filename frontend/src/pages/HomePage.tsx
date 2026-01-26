import { Container, Typography, Box } from '@mui/material'
import DomainInput from '../components/scan/DomainInput'

const HomePage = () => {
  return (
    <Container maxWidth="md">
      <Box sx={{ py: 6 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ mb: 2 }}>
          NetScout OSINT System
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 4, fontSize: '1.1rem' }}>
          Enter a domain name to start scanning for subdomains, IP addresses, and other information.
        </Typography>
        <Box sx={{ mt: 4 }}>
          <DomainInput />
        </Box>
      </Box>
    </Container>
  )
}

export default HomePage
