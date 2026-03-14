import { useState, useEffect } from 'react'
import {
  Container,
  Box,
  Typography,
  Alert,
  Tabs,
  Tab,
  Paper,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'
import DashboardIcon from '@mui/icons-material/Dashboard'
import DnsIcon from '@mui/icons-material/Dns'
import InfoIcon from '@mui/icons-material/Info'
import ListIcon from '@mui/icons-material/List'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import SecurityIcon from '@mui/icons-material/Security'
import NetworkCheckIcon from '@mui/icons-material/NetworkCheck'
import BuildIcon from '@mui/icons-material/Build'
import MapIcon from '@mui/icons-material/Map'
import ApiIcon from '@mui/icons-material/Api'

import OverviewPanel from '../components/results/OverviewPanel'
import GeoMap from '../components/results/GeoMap'
import ExternalApisPanel from '../components/results/ExternalApisPanel'
import SSLInfoPanel from '../components/results/SSLInfoPanel'
import PortScanPanel from '../components/results/PortScanPanel'
import TechStackPanel from '../components/results/TechStackPanel'
import ExportButtons from '../components/scan/ExportButtons'
import DNSInfoPanel from '../components/results/DNSInfoPanel'
import WhoisInfoPanel from '../components/results/WhoisInfoPanel'
import SubdomainsList from '../components/results/SubdomainsList'
import GraphView from '../components/graph/GraphView'
import GraphControls from '../components/graph/GraphControls'
import { useScanStore } from '../store/useScanStore'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`scan-tabpanel-${index}`}
      aria-labelledby={`scan-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

const ScanPage = () => {
  const [tabValue, setTabValue] = useState(0)
  const [cyInstance, setCyInstance] = useState<any>(null)
  const { currentScan } = useScanStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (!currentScan) {
      navigate('/')
    }
  }, [currentScan, navigate])

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  if (!currentScan) {
    return (
      <Container maxWidth="xl">
        <Box sx={{ py: 4 }}>
          <Alert severity="info">
            No scan results available. Please start a scan from the home page.
          </Alert>
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              {currentScan.target_domain}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Scan completed • {currentScan.subdomains?.length || 0} subdomains found
              {currentScan.scan_date && (
                <> • {new Date(currentScan.scan_date).toLocaleString('uk-UA', { dateStyle: 'medium', timeStyle: 'short' })}</>
              )}
            </Typography>
          </Box>
          <ExportButtons scanResults={currentScan} />
        </Box>

        {/* Tabs */}
        <Paper sx={{ mb: 2 }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              borderBottom: 1,
              borderColor: 'divider',
              '& .MuiTab-root': {
                minHeight: 64,
                textTransform: 'none',
              },
            }}
          >
            <Tab
              icon={<DashboardIcon />}
              label="Overview"
              iconPosition="start"
            />
            <Tab
              icon={<DnsIcon />}
              label="DNS Records"
              iconPosition="start"
            />
            <Tab
              icon={<InfoIcon />}
              label="WHOIS"
              iconPosition="start"
            />
            <Tab
              icon={<ListIcon />}
              label={`Subdomains (${currentScan.subdomains?.length || 0})`}
              iconPosition="start"
            />
            <Tab
              icon={<SecurityIcon />}
              label={`SSL (${currentScan.ssl_info?.certificates?.length || 0})`}
              iconPosition="start"
            />
            <Tab
              icon={<NetworkCheckIcon />}
              label="Ports"
              iconPosition="start"
            />
            <Tab
              icon={<BuildIcon />}
              label={`Tech (${Object.keys(currentScan.tech_stack || {}).length})`}
              iconPosition="start"
            />
            <Tab
              icon={<MapIcon />}
              label={`Map (${Object.keys(currentScan.geoip_info || {}).length})`}
              iconPosition="start"
            />
            <Tab
              icon={<ApiIcon />}
              label={`APIs (${Object.keys(currentScan.external_apis || {}).length})`}
              iconPosition="start"
            />
            <Tab
              icon={<AccountTreeIcon />}
              label="Graph"
              iconPosition="start"
            />
          </Tabs>
        </Paper>

        {/* Tab Panels */}
        <TabPanel value={tabValue} index={0}>
          <OverviewPanel scanResults={currentScan} />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <DNSInfoPanel dnsInfo={currentScan.dns_info || {}} />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <WhoisInfoPanel whoisInfo={currentScan.whois_info || {}} />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <SubdomainsList
            subdomains={currentScan.subdomains}
            targetDomain={currentScan.target_domain}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <SSLInfoPanel sslInfo={currentScan.ssl_info} />
        </TabPanel>

        <TabPanel value={tabValue} index={5}>
          <PortScanPanel portScan={currentScan.port_scan} />
        </TabPanel>

        <TabPanel value={tabValue} index={6}>
          <TechStackPanel techStack={currentScan.tech_stack} />
        </TabPanel>

        <TabPanel value={tabValue} index={7}>
          <GeoMap scanResults={currentScan} />
        </TabPanel>

        <TabPanel value={tabValue} index={8}>
          <ExternalApisPanel data={currentScan.external_apis} />
        </TabPanel>

        <TabPanel value={tabValue} index={9}>
          <Box>
            <GraphControls cy={cyInstance} />
            {(currentScan.subdomains?.length ?? 0) > 50 && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                Showing first 50 of {currentScan.subdomains?.length} subdomains in graph
              </Typography>
            )}
            <Box sx={{ mt: 2 }}>
              <GraphView data={currentScan} setCyInstance={setCyInstance} />
            </Box>
          </Box>
        </TabPanel>
      </Box>
    </Container>
  )
}

export default ScanPage
