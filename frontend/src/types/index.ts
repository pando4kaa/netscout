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

export interface ScanResults {
  target_domain: string
  scan_date?: string
  dns_info: DNSInfo
  whois_info: WhoisInfo
  subdomains: string[]
  summary: {
    total_subdomains: number
    total_ip_addresses: number
  }
}

export interface GraphNode {
  data: {
    id: string
    label: string
    type: 'domain' | 'subdomain' | 'ip'
    color?: string
    [key: string]: any
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
