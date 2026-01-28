import { useEffect, useRef, useCallback } from 'react'
import cytoscape, { Core, NodeSingular } from 'cytoscape'
import { Box, Paper, Typography, Chip } from '@mui/material'
import { buildGraphElements, NODE_TYPES } from '../../utils/graphBuilder'
import { ScanResults } from '../../types'

interface GraphViewProps {
  data: ScanResults | null
  setCyInstance?: (cy: Core | null) => void
}

const GraphView = ({ data, setCyInstance }: GraphViewProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)

  const showTooltip = useCallback((node: NodeSingular, event: any) => {
    if (!tooltipRef.current) return
    
    const tooltip = tooltipRef.current
    const nodeData = node.data()
    
    tooltip.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 4px;">${nodeData.label}</div>
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
            'width': 40,
            'height': 40,
            'background-fill': 'radial-gradient',
            'background-gradient-stop-colors': '#66bb6a #388e3c #1b5e20',
            'background-gradient-stop-positions': '0% 50% 100%',
            'border-color': '#2e7d32',
            'color': '#1b5e20',
            'shape': 'ellipse',
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
          if (type === 'ip') return 70
          if (type === 'ns') return 50
          if (type === 'mx') return 50
          return 30 // subdomains
        },
        levelWidth: function() { return 2 },
        minNodeSpacing: 60,
        spacingFactor: 1.5,
        animate: true,
        animationDuration: 500,
      },
    })

    // Hover effects
    cy.on('mouseover', 'node', (event) => {
      const node = event.target
      showTooltip(node, event)
      
      // Highlight connected nodes and edges
      const neighborhood = node.neighborhood().add(node)
      cy.elements().addClass('faded')
      neighborhood.removeClass('faded').addClass('highlighted')
      
      // Scale up hovered node
      node.style({
        'width': node.data('type') === 'domain' ? 80 : node.data('type') === 'ip' ? 60 : 50,
        'height': node.data('type') === 'domain' ? 80 : node.data('type') === 'ip' ? 60 : 50,
      })
    })

    cy.on('mouseout', 'node', (event) => {
      const node = event.target
      hideTooltip()
      
      // Reset all elements
      cy.elements().removeClass('faded highlighted')
      
      // Reset node size
      const type = node.data('type')
      let size = 40
      if (type === 'domain') size = 70
      else if (type === 'ip') size = 50
      else if (type === 'mx' || type === 'ns') size = 45
      
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

    cyRef.current = cy
    if (setCyInstance) setCyInstance(cy)

    return () => {
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

  return (
    <Box sx={{ position: 'relative' }}>
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
      </Box>
    </Box>
  )
}

export default GraphView
