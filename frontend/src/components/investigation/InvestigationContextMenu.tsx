import { useState } from 'react'
import { Menu, MenuItem, ListItemIcon, ListItemText, CircularProgress, Chip } from '@mui/material'
import DnsIcon from '@mui/icons-material/Dns'
import PublicIcon from '@mui/icons-material/Public'
import StorageIcon from '@mui/icons-material/Storage'
import SecurityIcon from '@mui/icons-material/Security'
import RouterIcon from '@mui/icons-material/Router'
import CodeIcon from '@mui/icons-material/Code'
import PlaceIcon from '@mui/icons-material/Place'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import WarningIcon from '@mui/icons-material/Warning'
import ApiIcon from '@mui/icons-material/Api'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import {
  ENRICHERS_BY_ENTITY,
  ENRICHER_LABELS,
  ENRICHER_OPSEC,
  INVESTIGATION_EXTERNAL_APIS_BY_ENTITY,
} from '../../types'

const ENRICHER_ICONS: Record<string, React.ReactNode> = {
  dns: <DnsIcon fontSize="small" />,
  whois: <PublicIcon fontSize="small" />,
  subdomains: <StorageIcon fontSize="small" />,
  ssl: <SecurityIcon fontSize="small" />,
  tech: <CodeIcon fontSize="small" />,
  root_domain: <AccountTreeIcon fontSize="small" />,
  port: <RouterIcon fontSize="small" />,
  geoip: <PlaceIcon fontSize="small" />,
  reverse_dns: <SwapHorizIcon fontSize="small" />,
  ip_to_asn: <AccountTreeIcon fontSize="small" />,
  'external_apis:virustotal': <ApiIcon fontSize="small" />,
  'external_apis:alienvault_otx': <ApiIcon fontSize="small" />,
  'external_apis:urlscan': <ApiIcon fontSize="small" />,
  'external_apis:threatcrowd': <ApiIcon fontSize="small" />,
  'external_apis:bgpview': <ApiIcon fontSize="small" />,
  'external_apis:abuseipdb': <ApiIcon fontSize="small" />,
}

interface InvestigationContextMenuProps {
  anchorPosition: { x: number; y: number } | null
  nodeType: string
  nodeValue: string
  nodeId: string
  onClose: () => void
  onRunEnricher: (enricherName: string) => void
  loading?: boolean
}

const InvestigationContextMenu = ({
  anchorPosition,
  nodeType,
  nodeValue,
  onClose,
  onRunEnricher,
  loading = false,
}: InvestigationContextMenuProps) => {
  const [externalApisOpen, setExternalApisOpen] = useState(false)
  const [submenuAnchor, setSubmenuAnchor] = useState<HTMLElement | null>(null)
  const enrichers = ENRICHERS_BY_ENTITY[nodeType] || []
  const externalApis = INVESTIGATION_EXTERNAL_APIS_BY_ENTITY[nodeType] || []

  const handleExternalApisClick = (e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation()
    setSubmenuAnchor(e.currentTarget)
    setExternalApisOpen(true)
  }

  const handleExternalApiSelect = (apiId: string) => {
    onRunEnricher(`external_apis:${apiId}`)
    setExternalApisOpen(false)
    setSubmenuAnchor(null)
    onClose()
  }

  return (
    <>
      <Menu
        open={anchorPosition !== null}
        onClose={() => {
          setExternalApisOpen(false)
          setSubmenuAnchor(null)
          onClose()
        }}
        anchorReference="anchorPosition"
        anchorPosition={
          anchorPosition
            ? { top: anchorPosition.y, left: anchorPosition.x }
            : undefined
        }
        MenuListProps={{ sx: { minWidth: 220 } }}
        slotProps={{
          paper: { 'data-no-context-menu': true } as object,
          backdrop: { 'data-no-context-menu': true } as object,
        }}
      >
        {loading ? (
          <MenuItem disabled>
            <ListItemIcon>
              <CircularProgress size={20} />
            </ListItemIcon>
            <ListItemText primary="Running..." />
          </MenuItem>
        ) : (
          <>
            {enrichers.map((name) => {
              const opsec = ENRICHER_OPSEC[name]
              const isActive = opsec === 'active'
              return (
                <MenuItem
                  key={name}
                  onClick={() => {
                    onRunEnricher(name)
                    onClose()
                  }}
                >
                  <ListItemIcon>{ENRICHER_ICONS[name] || <DnsIcon fontSize="small" />}</ListItemIcon>
                  <ListItemText
                    primary={ENRICHER_LABELS[name] || name}
                    secondary={isActive ? 'Direct contact with target' : undefined}
                  />
                  {isActive && (
                    <Chip
                      icon={<WarningIcon sx={{ fontSize: 14 }} />}
                      label="Active"
                      size="small"
                      color="warning"
                      sx={{ ml: 0.5 }}
                    />
                  )}
                </MenuItem>
              )
            })}
            {externalApis.length > 0 && (
              <MenuItem onClick={handleExternalApisClick}>
                <ListItemIcon><ApiIcon fontSize="small" /></ListItemIcon>
                <ListItemText primary="External APIs" />
                <ChevronRightIcon fontSize="small" sx={{ ml: 0.5 }} />
              </MenuItem>
            )}
          </>
        )}
      </Menu>
      <Menu
        open={externalApisOpen}
        onClose={() => {
          setExternalApisOpen(false)
          setSubmenuAnchor(null)
        }}
        anchorEl={submenuAnchor}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        MenuListProps={{ sx: { minWidth: 180 } }}
        slotProps={{
          paper: { 'data-no-context-menu': true } as object,
          backdrop: { 'data-no-context-menu': true } as object,
        }}
      >
        {externalApis.map((api) => (
          <MenuItem
            key={api.id}
            onClick={() => handleExternalApiSelect(api.id)}
          >
            <ListItemText primary={api.label} />
          </MenuItem>
        ))}
      </Menu>
    </>
  )
}

export default InvestigationContextMenu
