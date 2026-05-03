import { useState, useMemo, useRef } from 'react'
import type { Core as CytoscapeCore } from 'cytoscape'
import {
  Container,
  Box,
  Typography,
  Alert,
  Tabs,
  Tab,
  Paper,
  Button,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import HomeOutlinedIcon from '@mui/icons-material/HomeOutlined'
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
import { useLocaleFormatters } from '../i18n/format'

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
      {value === index && <Box sx={{ py: { xs: 2, sm: 3 }, px: { xs: 0.5, sm: 0 } }}>{children}</Box>}
    </div>
  )
}

const ScanPage = () => {
  const { t } = useTranslation()
  const { formatDateTime } = useLocaleFormatters()
  const [tabValue, setTabValue] = useState(0)
  const [cyInstance, setCyInstance] = useState<CytoscapeCore | null>(null)
  const graphWrapperRef = useRef<HTMLDivElement>(null)
  const { currentScan } = useScanStore()
  const navigate = useNavigate()

  const safeScan = useMemo(() => {
    if (!currentScan) return null
    return {
      ...currentScan,
      target_domain: currentScan.target_domain || 'unknown',
      subdomains: Array.isArray(currentScan.subdomains) ? currentScan.subdomains : [],
    }
  }, [currentScan])

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  if (!currentScan || !safeScan) {
    return (
      <Container maxWidth="sm">
        <Box
          sx={{
            py: { xs: 4, sm: 8 },
            px: { xs: 1, sm: 2 },
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            gap: 2,
          }}
        >
          <Typography variant="h4" component="h1" sx={{ fontWeight: 600, typography: { xs: 'h5', sm: 'h4' } }}>
            {t('scan.noResultsTitle')}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 480 }}>
            {t('scan.noResultsBody')}
          </Typography>
          <Alert severity="info" sx={{ width: '100%', textAlign: 'left' }}>
            {t('scan.noResultsAlert')}
          </Alert>
          <Button
            variant="contained"
            size="large"
            startIcon={<HomeOutlinedIcon />}
            onClick={() => navigate('/')}
            sx={{ mt: 1 }}
          >
            {t('scan.homeCta')}
          </Button>
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl" disableGutters sx={{ px: { xs: 0, sm: 2, md: 3 } }}>
      <Box sx={{ py: { xs: 2, md: 3 } }}>
        {/* Header */}
        <Box
          sx={{
            mb: { xs: 2, md: 3 },
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: { xs: 'stretch', sm: 'flex-start' },
            gap: 2,
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography
              variant="h4"
              component="h1"
              gutterBottom
              sx={{ wordBreak: 'break-word', typography: { xs: 'h5', sm: 'h4' } }}
            >
              {currentScan.target_domain}
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ fontSize: { xs: '0.9rem', sm: '1rem' } }}>
              {t('scan.completedSummary', { count: safeScan.subdomains?.length || 0 })}
              {safeScan.scan_date && (
                <> {t('scan.completedDate', { date: formatDateTime(safeScan.scan_date) })}</>
              )}
            </Typography>
          </Box>
          <Box sx={{ alignSelf: { xs: 'stretch', sm: 'flex-start' } }}>
            <ExportButtons scanResults={safeScan} />
          </Box>
        </Box>

        {/* Tabs */}
        <Paper sx={{ mb: 2, overflow: 'hidden' }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
            sx={{
              borderBottom: 1,
              borderColor: 'divider',
              '& .MuiTab-root': {
                minHeight: { xs: 48, sm: 56, md: 64 },
                textTransform: 'none',
                px: { xs: 1, sm: 1.5 },
                fontSize: { xs: '0.8rem', sm: '0.875rem' },
              },
              '& .MuiTab-iconWrapper': { mr: { xs: 0.5, sm: 1 } },
            }}
          >
            <Tab
              icon={<DashboardIcon />}
              label={t('scan.tabs.overview')}
              iconPosition="start"
            />
            <Tab
              icon={<DnsIcon />}
              label={t('scan.tabs.dns')}
              iconPosition="start"
            />
            <Tab
              icon={<InfoIcon />}
              label={t('scan.tabs.whois')}
              iconPosition="start"
            />
            <Tab
              icon={<ListIcon />}
              label={t('scan.tabs.subdomains', { count: safeScan.subdomains?.length || 0 })}
              iconPosition="start"
            />
            <Tab
              icon={<SecurityIcon />}
              label={t('scan.tabs.ssl', { count: safeScan.ssl_info?.certificates?.length || 0 })}
              iconPosition="start"
            />
            <Tab
              icon={<NetworkCheckIcon />}
              label={t('scan.tabs.ports')}
              iconPosition="start"
            />
            <Tab
              icon={<BuildIcon />}
              label={t('scan.tabs.tech', { count: Object.keys(safeScan.tech_stack || {}).length })}
              iconPosition="start"
            />
            <Tab
              icon={<MapIcon />}
              label={t('scan.tabs.map', { count: Object.keys(safeScan.geoip_info || {}).length })}
              iconPosition="start"
            />
            <Tab
              icon={<ApiIcon />}
              label={t('scan.tabs.apis', { count: Object.keys(safeScan.external_apis || {}).length })}
              iconPosition="start"
            />
            <Tab
              icon={<AccountTreeIcon />}
              label={t('scan.tabs.graph')}
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
              <Typography variant="h6">{t('common.graph')}</Typography>
              <HelpTooltip topic="graph_view" />
            </Box>
            <GraphControls cy={cyInstance} graphWrapperRef={graphWrapperRef} />
            {(safeScan.subdomains?.length ?? 0) > 50 && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                {t('scan.graphLimit', { count: safeScan.subdomains?.length })}
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
