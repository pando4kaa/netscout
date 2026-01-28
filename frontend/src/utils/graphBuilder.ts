import { ScanResults, GraphElements } from '../types'

export const NODE_TYPES = {
  domain: 'domain',
  subdomain: 'subdomain',
  ip: 'ip',
  mx: 'mx',
  ns: 'ns',
} as const

export const buildGraphElements = (scanData: ScanResults): GraphElements => {
  const nodes: any[] = []
  const edges: any[] = []
  const addedNodes = new Set<string>()

  if (!scanData) {
    return { nodes, edges }
  }

  // Add main domain node
  const domainId = `domain_${scanData.target_domain}`
  nodes.push({
    data: {
      id: domainId,
      label: scanData.target_domain,
      type: NODE_TYPES.domain,
    },
  })
  addedNodes.add(domainId)

  // Add IP address nodes (connect to main domain)
  if (scanData.dns_info && !scanData.dns_info.error && scanData.dns_info.a_records) {
    scanData.dns_info.a_records.forEach((ip) => {
      const ipNodeId = `ip_${ip}`
      if (!addedNodes.has(ipNodeId)) {
        nodes.push({
          data: {
            id: ipNodeId,
            label: ip,
            type: NODE_TYPES.ip,
          },
        })
        addedNodes.add(ipNodeId)
      }

      edges.push({
        data: {
          id: `edge_${domainId}_${ipNodeId}`,
          source: domainId,
          target: ipNodeId,
          edgeType: 'ip',
        },
      })
    })
  }

  // Add MX record nodes
  if (scanData.dns_info && !scanData.dns_info.error && scanData.dns_info.mx_records) {
    scanData.dns_info.mx_records.forEach((mx) => {
      const mxNodeId = `mx_${mx.host}`
      if (!addedNodes.has(mxNodeId)) {
        nodes.push({
          data: {
            id: mxNodeId,
            label: mx.host.replace(/\.$/, ''), // Remove trailing dot
            type: NODE_TYPES.mx,
            priority: mx.priority,
          },
        })
        addedNodes.add(mxNodeId)
      }

      edges.push({
        data: {
          id: `edge_${domainId}_${mxNodeId}`,
          source: domainId,
          target: mxNodeId,
          edgeType: 'mx',
        },
      })
    })
  }

  // Add NS record nodes
  if (scanData.dns_info && !scanData.dns_info.error && scanData.dns_info.ns_records) {
    scanData.dns_info.ns_records.forEach((ns) => {
      const nsNodeId = `ns_${ns}`
      if (!addedNodes.has(nsNodeId)) {
        nodes.push({
          data: {
            id: nsNodeId,
            label: ns.replace(/\.$/, ''), // Remove trailing dot
            type: NODE_TYPES.ns,
          },
        })
        addedNodes.add(nsNodeId)
      }

      edges.push({
        data: {
          id: `edge_${domainId}_${nsNodeId}`,
          source: domainId,
          target: nsNodeId,
          edgeType: 'ns',
        },
      })
    })
  }

  // Add subdomain nodes (limit to avoid overcrowding)
  const maxSubdomains = 50 // Limit for performance and readability
  const subdomainsToShow = scanData.subdomains?.slice(0, maxSubdomains) || []
  
  subdomainsToShow.forEach((subdomain) => {
    const subdomainId = `subdomain_${subdomain}`
    if (!addedNodes.has(subdomainId)) {
      // Shorten label if too long
      let label = subdomain
      if (label.length > 30) {
        const parts = label.split('.')
        if (parts.length > 2) {
          label = parts[0] + '...' + parts.slice(-2).join('.')
        }
      }

      nodes.push({
        data: {
          id: subdomainId,
          label: label,
          fullLabel: subdomain,
          type: NODE_TYPES.subdomain,
        },
      })
      addedNodes.add(subdomainId)

      edges.push({
        data: {
          id: `edge_${domainId}_${subdomainId}`,
          source: domainId,
          target: subdomainId,
          edgeType: 'subdomain',
        },
      })
    }
  })

  return { nodes, edges }
}
