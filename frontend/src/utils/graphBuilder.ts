import { ScanResults, GraphElements } from '../types'

const NODE_COLORS = {
  domain: '#1976d2',
  subdomain: '#2e7d32',
  ip: '#ed6c02',
}

export const buildGraphElements = (scanData: ScanResults): GraphElements => {
  const nodes: any[] = []
  const edges: any[] = []

  if (!scanData) {
    return { nodes, edges }
  }

  // Add main domain node
  nodes.push({
    data: {
      id: scanData.target_domain,
      label: scanData.target_domain,
      type: 'domain',
      color: NODE_COLORS.domain,
    },
  })

  // Add subdomain nodes
  scanData.subdomains?.forEach((subdomain) => {
    nodes.push({
      data: {
        id: subdomain,
        label: subdomain,
        type: 'subdomain',
        color: NODE_COLORS.subdomain,
      },
    })
    edges.push({
      data: {
        source: scanData.target_domain,
        target: subdomain,
      },
    })
  })

  // Add IP address nodes
  scanData.dns_info?.a_records?.forEach((ip) => {
    const ipNodeId = `ip_${ip}`
    if (!nodes.find((n) => n.data.id === ipNodeId)) {
      nodes.push({
        data: {
          id: ipNodeId,
          label: ip,
          type: 'ip',
          color: NODE_COLORS.ip,
        },
      })
    }

    // Connect domain to IP
    edges.push({
      data: {
        source: scanData.target_domain,
        target: ipNodeId,
      },
    })

    // Connect subdomains to their IPs (if we have that info)
    // This would require additional data structure
  })

  return { nodes, edges }
}
