import { useState, useEffect, useMemo, useRef } from 'react'
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
import HelpTooltip from '../components/common/HelpTooltip'
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
  const graphWrapperRef = useRef<HTMLDivElement>(null)
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

  const safeScan = useMemo(
    () => ({
      ...currentScan,
      target_domain: currentScan.target_domain || 'unknown',
      subdomains: Array.isArray(currentScan.subdomains) ? currentScan.subdomains : [],
    }),
    [currentScan]
  )

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
              Scan completed • {safeScan.subdomains?.length || 0} subdomains found
              {safeScan.scan_date && (
                <> • {new Date(safeScan.scan_date).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })}</>
              )}
            </Typography>
          </Box>
          <ExportButtons scanResults={safeScan} />
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
              label={`Subdomains (${safeScan.subdomains?.length || 0})`}
              iconPosition="start"
            />
            <Tab
              icon={<SecurityIcon />}
              label={`SSL (${safeScan.ssl_info?.certificates?.length || 0})`}
              iconPosition="start"
            />
            <Tab
              icon={<NetworkCheckIcon />}
              label="Ports"
              iconPosition="start"
            />
            <Tab
              icon={<BuildIcon />}
              label={`Tech (${Object.keys(safeScan.tech_stack || {}).length})`}
              iconPosition="start"
            />
            <Tab
              icon={<MapIcon />}
              label={`Map (${Object.keys(safeScan.geoip_info || {}).length})`}
              iconPosition="start"
            />
            <Tab
              icon={<ApiIcon />}
              label={`APIs (${Object.keys(safeScan.external_apis || {}).length})`}
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
          <OverviewPanel scanResults={safeScan} />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <DNSInfoPanel dnsInfo={safeScan.dns_info || {}} />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <WhoisInfoPanel whoisInfo={safeScan.whois_info || {}} />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <SubdomainsList
            subdomains={safeScan.subdomains}
            targetDomain={safeScan.target_domain}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <SSLInfoPanel sslInfo={safeScan.ssl_info} />
        </TabPanel>

        <TabPanel value={tabValue} index={5}>
          <PortScanPanel portScan={safeScan.port_scan} />
        </TabPanel>

        <TabPanel value={tabValue} index={6}>
          <TechStackPanel techStack={safeScan.tech_stack} />
        </TabPanel>

        <TabPanel value={tabValue} index={7}>
          <GeoMap scanResults={safeScan} />
        </TabPanel>

        <TabPanel value={tabValue} index={8}>
          <ExternalApisPanel data={safeScan.external_apis} />
        </TabPanel>

        <TabPanel value={tabValue} index={9}>
          <Box ref={graphWrapperRef}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Typography variant="h6">Graph</Typography>
              <HelpTooltip topic="graph_view" />
            </Box>
            <GraphControls cy={cyInstance} graphWrapperRef={graphWrapperRef} />
            {(safeScan.subdomains?.length ?? 0) > 50 && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                Showing first 50 of {safeScan.subdomains?.length} subdomains in graph
              </Typography>
            )}
            <Box sx={{ mt: 2 }}>
              <GraphView data={safeScan} setCyInstance={setCyInstance} />
            </Box>
          </Box>
        </TabPanel>
      </Box>
    </Container>
  )
}

export default ScanPage
