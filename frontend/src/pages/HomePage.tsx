import { Container, Typography, Box } from '@mui/material'
import DomainInput from '../components/scan/DomainInput'

const HomePage = () => {
  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          NetScout OSINT System
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
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
