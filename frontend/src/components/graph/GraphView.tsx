import { useEffect, useRef, useCallback, useState } from 'react'
import cytoscape, { Core, NodeSingular } from 'cytoscape'
import { Box, Paper, Typography, Chip, Menu, MenuItem } from '@mui/material'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong'
import { buildGraphElements } from '../../utils/graphBuilder'
import { ScanResults } from '../../types'

const MINIMAP_SIZE = { w: 140, h: 100 }

function MinimapOverlay({ cy, container }: { cy: Core; container: HTMLDivElement }) {
  const extent = cy.extent()
  const pan = cy.pan()
  const zoom = cy.zoom()
  const rect = container.getBoundingClientRect()
  const viewW = rect.width / zoom
  const viewH = rect.height / zoom
  const viewX = pan.x - viewW / 2
  const viewY = pan.y - viewH / 2
  const extW = extent.x2 - extent.x1 || 1
  const extH = extent.y2 - extent.y1 || 1
  const scaleX = MINIMAP_SIZE.w / extW
  const scaleY = MINIMAP_SIZE.h / extH
  const scale = Math.min(scaleX, scaleY)
  const offX = (MINIMAP_SIZE.w - extW * scale) / 2 - (extent.x1 * scale)
  const offY = (MINIMAP_SIZE.h - extH * scale) / 2 - (extent.y1 * scale)
  const vp = {
    x: offX + viewX * scale,
    y: offY + viewY * scale,
    w: viewW * scale,
    h: viewH * scale,
  }
  return (
    <Paper
      elevation={2}
      sx={{
        position: 'absolute',
        bottom: 16,
        right: 16,
        zIndex: 10,
        width: MINIMAP_SIZE.w,
        height: MINIMAP_SIZE.h,
        bgcolor: 'rgba(255,255,255,0.95)',
        overflow: 'hidden',
        borderRadius: 1,
        border: '1px solid #e0e0e0',
      }}
    >
      <Box
        sx={{
          width: '100%',
          height: '100%',
          bgcolor: '#f5f5f5',
          position: 'relative',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            left: vp.x,
            top: vp.y,
            width: Math.max(vp.w, 4),
            height: Math.max(vp.h, 4),
            border: '2px solid',
            borderColor: 'primary.main',
            bgcolor: 'rgba(25, 118, 210, 0.15)',
            borderRadius: 0.5,
          }}
        />
      </Box>
    </Paper>
  )
}

interface GraphViewProps {
  data: ScanResults | null
  setCyInstance?: (cy: Core | null) => void
}

const GraphView = ({ data, setCyInstance }: GraphViewProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [contextMenu, setContextMenu] = useState<{ node: NodeSingular; x: number; y: number } | null>(null)
  const [, setMinimapUpdate] = useState(0)

  const showTooltip = useCallback((node: NodeSingular, event: any) => {
    if (!tooltipRef.current) return
    
    const tooltip = tooltipRef.current
    const nodeData = node.data()
    
    const displayLabel = nodeData.fullLabel || nodeData.label
    tooltip.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 4px; word-break: break-all;">${displayLabel}</div>
      <div style="font-size: 12px; color: #666;">Type: ${nodeData.type}</div>
      ${nodeData.count ? `<div style="font-size: 12px; color: #666;">Count: ${nodeData.count}</div>` : ''}
    `
    
    tooltip.style.display = 'block'
    tooltip.style.left = `${event.renderedPosition.x + 15}px`
    tooltip.style.top = `${event.renderedPosition.y + 15}px`
  }, [])

  const hideTooltip = useCallback(() => {
    if (tooltipRef.current) {
      tooltipRef.current.style.display = 'none'
    }
  }, [])

  useEffect(() => {
    if (!containerRef.current || !data) {
      if (setCyInstance) setCyInstance(null)
      return
    }

    const elements = buildGraphElements(data)

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.3,
      style: [
        // Base node style
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 8,
            'font-size': 11,
            'font-family': 'Raleway, sans-serif',
            'font-weight': 500,
            'color': '#333',
            'text-outline-color': '#fff',
            'text-outline-width': 2,
            'text-max-width': '120px',
            'text-wrap': 'ellipsis',
            'min-zoomed-font-size': 8,
            'transition-property': 'width, height, background-color, border-width, opacity',
            'transition-duration': 200,
            'border-width': 3,
            'border-opacity': 0.8,
          },
        },
        // Domain node (main)
        {
          selector: 'node[type="domain"]',
          style: {
            'width': 70,
            'height': 70,
            'background-color': '#1565c0',
            'background-opacity': 1,
            'border-color': '#0d47a1',
            'font-size': 14,
            'font-weight': 700,
            'color': '#0d47a1',
            'text-margin-y': 12,
            'z-index': 100,
            'shape': 'ellipse',
            // Gradient effect using overlay
            'background-fill': 'radial-gradient',
            'background-gradient-stop-colors': '#42a5f5 #1565c0 #0d47a1',
            'background-gradient-stop-positions': '0% 50% 100%',
          },
        },
        // Subdomain nodes
        {
          selector: 'node[type="subdomain"]',
          style: {
            'width': 44,
            'height': 44,
            'background-fill': 'radial-gradient',
            'background-gradient-stop-colors': '#66bb6a #388e3c #1b5e20',
            'background-gradient-stop-positions': '0% 50% 100%',
            'border-color': '#2e7d32',
            'color': '#1b5e20',
            'shape': 'ellipse',
            'font-size': 10,
            'text-max-width': '90px',
          },
        },
        // IP address nodes
        {
          selector: 'node[type="ip"]',
          style: {
            'width': 50,
            'height': 50,
            'background-fill': 'radial-gradient',
            'background-gradient-stop-colors': '#ffb74d #f57c00 #e65100',
            'background-gradient-stop-positions': '0% 50% 100%',
            'border-color': '#ef6c00',
            'color': '#e65100',
            'shape': 'round-rectangle',
            'corner-radius': '8px',
          },
        },
        // MX record nodes
        {
          selector: 'node[type="mx"]',
          style: {
            'width': 45,
            'height': 45,
            'background-fill': 'radial-gradient',
            'background-gradient-stop-colors': '#ba68c8 #7b1fa2 #4a148c',
            'background-gradient-stop-positions': '0% 50% 100%',
            'border-color': '#8e24aa',
            'color': '#4a148c',
            'shape': 'diamond',
          },
        },
        // NS record nodes
        {
          selector: 'node[type="ns"]',
          style: {
            'width': 45,
            'height': 45,
            'background-fill': 'radial-gradient',
            'background-gradient-stop-colors': '#4dd0e1 #00acc1 #006064',
            'background-gradient-stop-positions': '0% 50% 100%',
            'border-color': '#00838f',
            'color': '#006064',
            'shape': 'round-hexagon',
          },
        },
        // Certificate nodes
        {
          selector: 'node[type="certificate"]',
          style: {
            'width': 36,
            'height': 36,
            'background-color': '#78909c',
            'border-color': '#546e7a',
            'color': '#37474f',
            'shape': 'round-octagon',
            'font-size': 9,
          },
        },
        // Risk indicator: expired certificate (red border)
        {
          selector: 'node.risk-expired',
          style: {
            'border-color': '#d32f2f',
            'border-width': 4,
          },
        },
        // Risk indicator: warning (yellow border) - for future use
        {
          selector: 'node.risk-warning',
          style: {
            'border-color': '#ed6c02',
            'border-width': 4,
          },
        },
        // Port nodes
        {
          selector: 'node[type="port"]',
          style: {
            'width': 32,
            'height': 32,
            'background-color': '#90a4ae',
            'border-color': '#607d8b',
            'color': '#455a64',
            'shape': 'round-rectangle',
            'font-size': 9,
          },
        },
        // Hide subdomain labels when zoomed out (class added via zoom listener)
        {
          selector: 'node[type="subdomain"].labels-hidden',
          style: {
            'label': '',
          },
        },
        // Base edge style
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#bdbdbd',
            'target-arrow-color': '#9e9e9e',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.8,
            'curve-style': 'bezier',
            'opacity': 0.7,
            'transition-property': 'line-color, width, opacity',
            'transition-duration': 200,
          },
        },
        // Edge to subdomain
        {
          selector: 'edge[edgeType="subdomain"]',
          style: {
            'line-color': '#81c784',
            'target-arrow-color': '#66bb6a',
            'line-style': 'solid',
            'opacity': 0.6,
          },
        },
        // Edge to IP
        {
          selector: 'edge[edgeType="ip"]',
          style: {
            'line-color': '#ffb74d',
            'target-arrow-color': '#ffa726',
            'line-style': 'solid',
          },
        },
        // Edge to MX
        {
          selector: 'edge[edgeType="mx"]',
          style: {
            'line-color': '#ce93d8',
            'target-arrow-color': '#ba68c8',
            'line-style': 'dashed',
          },
        },
        // Edge to NS
        {
          selector: 'edge[edgeType="ns"]',
          style: {
            'line-color': '#80deea',
            'target-arrow-color': '#4dd0e1',
            'line-style': 'dashed',
          },
        },
        // Edge to certificate
        {
          selector: 'edge[edgeType="certificate"]',
          style: {
            'line-color': '#90a4ae',
            'target-arrow-color': '#78909c',
            'line-style': 'dotted',
            'opacity': 0.5,
          },
        },
        // Edge to port
        {
          selector: 'edge[edgeType="port"]',
          style: {
            'line-color': '#b0bec5',
            'target-arrow-color': '#90a4ae',
            'line-style': 'dotted',
            'opacity': 0.5,
          },
        },
        // Hover state for nodes
        {
          selector: 'node:active',
          style: {
            'overlay-opacity': 0.2,
            'overlay-color': '#000',
          },
        },
        // Selected node
        {
          selector: 'node:selected',
          style: {
            'border-width': 5,
            'border-color': '#d32f2f',
            'overlay-opacity': 0.1,
            'overlay-color': '#d32f2f',
          },
        },
        // Highlighted nodes (neighbors of hovered)
        {
          selector: 'node.highlighted',
          style: {
            'border-width': 4,
            'opacity': 1,
            'z-index': 50,
          },
        },
        // Faded nodes
        {
          selector: 'node.faded',
          style: {
            'opacity': 0.2,
          },
        },
        // Highlighted edges
        {
          selector: 'edge.highlighted',
          style: {
            'width': 4,
            'opacity': 1,
            'z-index': 50,
          },
        },
        // Faded edges
        {
          selector: 'edge.faded',
          style: {
            'opacity': 0.1,
          },
        },
      ],
      layout: {
        name: 'concentric',
        concentric: function(node: any) {
          const type = node.data('type')
          if (type === 'domain') return 100
          if (type === 'ip') return 75
          if (type === 'ns') return 60
          if (type === 'mx') return 60
          if (type === 'certificate' || type === 'port') return 20
          return 35 // subdomains
        },
        levelWidth: function() { return 3 },
        minNodeSpacing: 70,
        spacingFactor: 2,
        animate: true,
        animationDuration: 500,
      },
    })

    // Collect path from node back to root (domain) - full chain
    const getPathToRoot = (node: NodeSingular) => {
      let path = node.union()
      let current = node.predecessors()
      const seen = new Set<string>([node.id()])
      while (current.length > 0) {
        current.forEach((n: any) => {
          if (!seen.has(n.id())) {
            seen.add(n.id())
            path = path.union(n)
          }
        })
        current = current.predecessors().filter((n: any) => !seen.has(n.id()))
      }
      const pathEdges = path.connectedEdges().filter((e: any) =>
        path.contains(e.source()) && path.contains(e.target())
      )
      return path.union(pathEdges)
    }

    // Hover effects - highlight full chain from node to main domain
    cy.on('mouseover', 'node', (event) => {
      const node = event.target
      showTooltip(node, event)
      
      const pathToRoot = getPathToRoot(node)
      cy.elements().addClass('faded')
      pathToRoot.removeClass('faded').addClass('highlighted')
      
      // Scale up hovered node
      const type = node.data('type')
      const hoverSizes: Record<string, number> = {
        domain: 80,
        ip: 60,
        mx: 52,
        ns: 52,
        subdomain: 52,
        certificate: 42,
        port: 38,
      }
      const s = hoverSizes[type] || 50
      node.style({ width: s, height: s })
    })

    cy.on('mouseout', 'node', (event) => {
      const node = event.target
      hideTooltip()
      
      // Reset all elements
      cy.elements().removeClass('faded highlighted')
      
      // Reset node size
      const type = node.data('type')
      let size = 44
      if (type === 'domain') size = 70
      else if (type === 'ip') size = 50
      else if (type === 'mx' || type === 'ns') size = 45
      else if (type === 'certificate') size = 36
      else if (type === 'port') size = 32
      
      node.style({
        'width': size,
        'height': size,
      })
    })

    // Double click to focus
    cy.on('dblclick', 'node', (event) => {
      const node = event.target
      cy.animate({
        fit: {
          eles: node.neighborhood().add(node),
          padding: 50,
        },
        duration: 500,
      })
    })

    // Toggle subdomain labels based on zoom level to reduce clutter
    const updateLabelVisibility = () => {
      const zoom = cy.zoom()
      cy.nodes('[type="subdomain"]').forEach((n: any) => {
        if (zoom < 0.7) {
          n.addClass('labels-hidden')
        } else {
          n.removeClass('labels-hidden')
        }
      })
    }
    updateLabelVisibility()
    cy.on('zoom', () => {
      updateLabelVisibility()
      setMinimapUpdate((n) => n + 1)
    })
    cy.on('pan', () => setMinimapUpdate((n) => n + 1))

    // Context menu: find node at position
    const getNodeAtPosition = (clientX: number, clientY: number): NodeSingular | null => {
      const container = cy.container()
      if (!container) return null
      const rect = container.getBoundingClientRect()
      const x = clientX - rect.left
      const y = clientY - rect.top
      let found: NodeSingular | null = null
      cy.nodes().forEach((node: any) => {
        if (!node.visible()) return
        const bb = node.renderedBoundingBox()
        if (x >= bb.x1 && x <= bb.x2 && y >= bb.y1 && y <= bb.y2) {
          found = node
        }
      })
      return found
    }

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault()
      const node = getNodeAtPosition(e.clientX, e.clientY)
      if (node) {
        setContextMenu({ node, x: e.clientX, y: e.clientY })
      }
    }
    containerRef.current?.addEventListener('contextmenu', handleContextMenu)

    cyRef.current = cy
    if (setCyInstance) setCyInstance(cy)
    setMinimapUpdate((n) => n + 1)

    return () => {
      containerRef.current?.removeEventListener('contextmenu', handleContextMenu)
      cy.destroy()
      if (setCyInstance) setCyInstance(null)
    }
  }, [data, setCyInstance, showTooltip, hideTooltip])

  if (!data) {
    return (
      <Paper
        sx={{
          width: '100%',
          height: '600px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: '#fafafa',
        }}
      >
        <Typography color="text.secondary">No data available</Typography>
      </Paper>
    )
  }

  const getNodeUrl = (node: NodeSingular) => {
    const d = node.data()
    const label = d.fullLabel || d.label || ''
    if (d.type === 'ip') return `https://${label}`
    if (label && !label.startsWith('http')) return `https://${label}`
    return label
  }

  const handleContextMenuCopy = () => {
    if (contextMenu) {
      const label = contextMenu.node.data('fullLabel') || contextMenu.node.data('label') || ''
      navigator.clipboard.writeText(label)
    }
    setContextMenu(null)
  }

  const handleContextMenuOpen = () => {
    if (contextMenu) {
      const url = getNodeUrl(contextMenu.node)
      if (url) window.open(url, '_blank')
    }
    setContextMenu(null)
  }

  const handleContextMenuFocus = () => {
    if (contextMenu && cyRef.current) {
      cyRef.current.animate({
        fit: { eles: contextMenu.node.neighborhood().add(contextMenu.node), padding: 80 },
        duration: 400,
      })
    }
    setContextMenu(null)
  }

  return (
    <Box sx={{ position: 'relative' }}>
      {/* Context menu */}
      <Menu
        open={contextMenu !== null}
        onClose={() => setContextMenu(null)}
        anchorReference="anchorPosition"
        anchorPosition={contextMenu ? { top: contextMenu.y, left: contextMenu.x } : undefined}
      >
        <MenuItem onClick={handleContextMenuCopy}>
          <ContentCopyIcon fontSize="small" sx={{ mr: 1 }} />
          Copy
        </MenuItem>
        <MenuItem onClick={handleContextMenuOpen}>
          <OpenInNewIcon fontSize="small" sx={{ mr: 1 }} />
          Open in new tab
        </MenuItem>
        <MenuItem onClick={handleContextMenuFocus}>
          <CenterFocusStrongIcon fontSize="small" sx={{ mr: 1 }} />
          Focus
        </MenuItem>
      </Menu>

      {/* Legend */}
      <Paper
        sx={{
          position: 'absolute',
          top: 16,
          left: 16,
          zIndex: 10,
          p: 1.5,
          bgcolor: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          flexDirection: 'column',
          gap: 0.5,
        }}
      >
        <Typography variant="caption" sx={{ fontWeight: 600, mb: 0.5 }}>Legend</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 16, height: 16, borderRadius: '50%', background: 'linear-gradient(135deg, #42a5f5 0%, #1565c0 100%)' }} />
          <Typography variant="caption">Domain</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 14, height: 14, borderRadius: '50%', background: 'linear-gradient(135deg, #66bb6a 0%, #388e3c 100%)' }} />
          <Typography variant="caption">Subdomain</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 14, height: 14, borderRadius: 1, background: 'linear-gradient(135deg, #ffb74d 0%, #f57c00 100%)' }} />
          <Typography variant="caption">IP Address</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 14, height: 14, transform: 'rotate(45deg)', background: 'linear-gradient(135deg, #ba68c8 0%, #7b1fa2 100%)' }} />
          <Typography variant="caption">Mail Server</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 14, height: 14, borderRadius: '3px', background: 'linear-gradient(135deg, #4dd0e1 0%, #00acc1 100%)' }} />
          <Typography variant="caption">Name Server</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 12, height: 12, borderRadius: 1, bgcolor: '#78909c' }} />
          <Typography variant="caption">Certificate</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 12, height: 12, borderRadius: 0.5, bgcolor: '#90a4ae' }} />
          <Typography variant="caption">Port</Typography>
        </Box>
      </Paper>

      {/* Tooltip */}
      <Box
        ref={tooltipRef}
        sx={{
          position: 'absolute',
          display: 'none',
          backgroundColor: 'rgba(255, 255, 255, 0.98)',
          border: '1px solid #e0e0e0',
          borderRadius: 1,
          padding: '8px 12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          zIndex: 1000,
          pointerEvents: 'none',
          maxWidth: 250,
        }}
      />

      {/* Minimap */}
      {cyRef.current && containerRef.current && (
        <MinimapOverlay cy={cyRef.current} container={containerRef.current} />
      )}

      {/* Graph Container */}
      <Paper
        ref={containerRef}
        elevation={0}
        sx={{
          width: '100%',
          height: '600px',
          bgcolor: '#fafafa',
          backgroundImage: `
            radial-gradient(circle, #e0e0e0 1px, transparent 1px)
          `,
          backgroundSize: '20px 20px',
          borderRadius: 2,
          border: '1px solid #e0e0e0',
        }}
      />

      {/* Tips */}
      <Box sx={{ mt: 1, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Chip label="Scroll to zoom" size="small" variant="outlined" />
        <Chip label="Drag to pan" size="small" variant="outlined" />
        <Chip label="Double-click to focus" size="small" variant="outlined" />
        <Chip label="Hover for details" size="small" variant="outlined" />
        <Chip label="Zoom in to see labels" size="small" variant="outlined" />
      </Box>
    </Box>
  )
}

export default GraphView
