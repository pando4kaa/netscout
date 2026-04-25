export interface EmailSecurityInfo {
  spf_present?: boolean
  spf_record?: string
  dmarc_present?: boolean
  dmarc_record?: string
  dmarc_policy?: string
  dkim_hints?: string[]
}

export interface DNSInfo {
  domain?: string
  a_records?: string[]
  aaaa_records?: string[]
  mx_records?: Array<{
    priority: number
    host: string
  }>
  txt_records?: string[]
  ns_records?: string[]
  cname_records?: string[]
  soa_records?: string[]
  ptr_records?: Record<string, string>
  zone_transfer_attempted?: boolean
  zone_transfer_available?: boolean
  zone_transfer_error?: string
  email_security?: EmailSecurityInfo
  error?: string
}

export interface WhoisInfo {
  domain?: string
  registrar?: string | null
  creation_date?: string | null
  expiration_date?: string | null
  name_servers?: string[]
  emails?: string[]
  status?: string | null
  error?: string
}

export interface CertificateInfo {
  host: string
  subject_cn?: string
  issuer?: string
  san?: string[]
  is_expired?: boolean
  error?: string
}

export interface SslInfo {
  certificates?: CertificateInfo[]
  error?: string
}

export interface OpenPort {
  port: number
  protocol?: string
  service?: string
  banner?: string
}

export interface PortScanResult {
  ip: string
  open_ports: OpenPort[]
  error?: string
}

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export interface Alert {
  type: string
  level: RiskLevel
  message: string
  target?: string
  details?: Record<string, unknown>
}

export interface ScanResults {
  target_domain: string
  scan_date?: string
  scan_id?: string
  dns_info?: DNSInfo
  whois_info?: WhoisInfo
  subdomains: string[]
  ssl_info?: SslInfo
  port_scan?: PortScanResult[]
  tech_stack?: Record<string, unknown>
  geoip_info?: Record<string, { country?: string; city?: string; latitude?: number; longitude?: number }>
  external_apis?: Record<string, unknown>
  alerts?: Alert[]
  summary?: {
    total_subdomains?: number
    total_ip_addresses?: number
    total_dns_records?: number
    total_alerts?: number
    risk_score?: number
  }
  correlation?: {
    subdomain_count?: number
    unique_ips?: number
    ip_to_subdomains?: Record<string, string[]>
    ptr_records?: Record<string, string>
  }
}

export interface GraphNode {
  data: {
    id: string
    label: string
    type: 'domain' | 'subdomain' | 'ip' | 'mx' | 'ns' | 'certificate' | 'port' | 'technology' | 'asn'
    color?: string
    [key: string]: unknown
  }
}

export interface GraphEdge {
  data: {
    source: string
    target: string
    [key: string]: any
  }
}

export interface GraphElements {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface Investigation {
  id: string
  name: string
  created_at?: string
  updated_at?: string
}

export interface InvestigationDetail extends Investigation {
  graph: {
    nodes: GraphNode[]
    edges: GraphEdge[]
  }
}

export const ENRICHERS_BY_ENTITY: Record<string, string[]> = {
  domain: ['dns', 'whois', 'subdomains', 'ssl', 'tech', 'root_domain'],
  subdomain: ['dns', 'whois', 'subdomains', 'ssl', 'tech', 'root_domain'],
  ip: ['port', 'geoip', 'reverse_dns', 'ip_to_asn'],
}

/** Display names for investigation context menu and bulk enricher menu */
export const ENRICHER_LABELS: Record<string, string> = {
  dns: 'DNS Resolution',
  whois: 'WHOIS Lookup',
  subdomains: 'Subdomain Discovery',
  ssl: 'SSL Certificate',
  tech: 'Technology Detection',
  root_domain: 'Root Domain',
  port: 'Port Scan',
  geoip: 'GeoIP',
  reverse_dns: 'Reverse DNS',
  ip_to_asn: 'IP to ASN',
}

export const INVESTIGATION_EXTERNAL_APIS_BY_ENTITY: Record<string, Array<{ id: string; label: string }>> = {
  domain: [
    { id: 'virustotal', label: 'VirusTotal' },
    { id: 'alienvault_otx', label: 'AlienVault OTX' },
    { id: 'urlscan', label: 'URLScan' },
    { id: 'threatcrowd', label: 'ThreatCrowd' },
  ],
  subdomain: [
    { id: 'virustotal', label: 'VirusTotal' },
    { id: 'alienvault_otx', label: 'AlienVault OTX' },
    { id: 'urlscan', label: 'URLScan' },
    { id: 'threatcrowd', label: 'ThreatCrowd' },
  ],
  ip: [
    { id: 'bgpview', label: 'BGPView' },
    { id: 'abuseipdb', label: 'AbuseIPDB' },
  ],
}

export const ENRICHER_OPSEC: Record<string, 'passive' | 'semi-passive' | 'active'> = {
  dns: 'semi-passive',
  whois: 'semi-passive',
  subdomains: 'passive',
  ssl: 'active',
  tech: 'active',
  root_domain: 'passive',
  port: 'active',
  geoip: 'passive',
  reverse_dns: 'passive',
  ip_to_asn: 'passive',
  'external_apis:virustotal': 'passive',
  'external_apis:alienvault_otx': 'passive',
  'external_apis:urlscan': 'passive',
  'external_apis:threatcrowd': 'passive',
  'external_apis:bgpview': 'passive',
  'external_apis:abuseipdb': 'passive',
}
