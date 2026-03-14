import { ScanResults, GraphElements } from '../types'

export const MAX_SUBDOMAINS_IN_GRAPH = 50

export const NODE_TYPES = {
  domain: 'domain',
  subdomain: 'subdomain',
  ip: 'ip',
  mx: 'mx',
  ns: 'ns',
  certificate: 'certificate',
  port: 'port',
  technology: 'technology',
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
  const subdomainsToShow = scanData.subdomains?.slice(0, MAX_SUBDOMAINS_IN_GRAPH) || []
  
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

  // Add port nodes (from port_scan) - after IPs and subdomains
  if (scanData.port_scan) {
    scanData.port_scan.forEach((ps) => {
      ps.open_ports?.forEach((op) => {
        const portNodeId = `port_${ps.ip}_${op.port}`
        if (!addedNodes.has(portNodeId)) {
          nodes.push({
            data: {
              id: portNodeId,
              label: `${op.port} (${op.service || 'tcp'})`,
              type: NODE_TYPES.port,
              ip: ps.ip,
              port: op.port,
            },
          })
          addedNodes.add(portNodeId)
          const ipNodeId = `ip_${ps.ip}`
          if (addedNodes.has(ipNodeId)) {
            edges.push({
              data: {
                id: `edge_${ipNodeId}_${portNodeId}`,
                source: ipNodeId,
                target: portNodeId,
                edgeType: 'port',
              },
            })
          }
        }
      })
    })
  }

  // Add certificate nodes (from ssl_info)
  if (scanData.ssl_info?.certificates) {
    scanData.ssl_info.certificates.slice(0, 10).forEach((cert) => {
      const certNodeId = `cert_${cert.host}`
      if (!addedNodes.has(certNodeId)) {
        nodes.push({
          data: {
            id: certNodeId,
            label: cert.host,
            type: NODE_TYPES.certificate,
            is_expired: cert.is_expired,
          },
        })
        addedNodes.add(certNodeId)
        const subdomainId = `subdomain_${cert.host}`
        if (addedNodes.has(subdomainId)) {
          edges.push({
            data: {
              id: `edge_${subdomainId}_${certNodeId}`,
              source: subdomainId,
              target: certNodeId,
              edgeType: 'certificate',
            },
          })
        } else {
          edges.push({
            data: {
              id: `edge_${domainId}_${certNodeId}`,
              source: domainId,
              target: certNodeId,
              edgeType: 'certificate',
            },
          })
        }
      }
    })
  }

  return { nodes, edges }
}
