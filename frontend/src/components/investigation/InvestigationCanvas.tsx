import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react'
import cytoscape, { Core, NodeSingular, StylesheetJson } from 'cytoscape'
import { Box, Paper, Chip } from '@mui/material'
import { GraphNode, GraphEdge } from '../../types'
import registerLassoShiftOnly from '../../lib/cytoscape-lasso-shift-only'

let lassoShiftExtensionRegistered = false
if (!lassoShiftExtensionRegistered) {
  cytoscape.use(registerLassoShiftOnly as (ext: typeof cytoscape) => void)
  lassoShiftExtensionRegistered = true
}

/** All nodes reachable from root via outgoing edges (includes root). */
function collectDescendantNodeIds(cy: Core, rootId: string): string[] {
  const ordered: string[] = []
  const seen = new Set<string>()
  const stack = [rootId]
  while (stack.length > 0) {
    const id = stack.pop()!
    if (seen.has(id)) continue
    seen.add(id)
    ordered.push(id)
    const el = cy.getElementById(id)
    if (!el.length) continue
    el.outgoers('node').forEach((out) => {
      const oid = out.id()
      if (!seen.has(oid)) stack.push(oid)
    })
  }
  return ordered
}

export interface InvestigationCanvasHandle {
  exportPng: () => Promise<Blob>
  clearSelection: () => void
  focusNode: (nodeId: string) => void
  /** Replace selection with exactly these node ids (must exist on the graph). */
  setSelectionToIds: (nodeIds: string[]) => void
}

interface InvestigationCanvasProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  onNodeRightClick: (node: NodeSingular, x: number, y: number) => void
  onNodeClick?: (node: NodeSingular) => void
  onSelectionChange?: (nodes: NodeSingular[]) => void
  showEdgeLabels?: boolean
}

const getCytoscapeStyle = (showEdgeLabels: boolean) => [
  { selector: 'node', style: {
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
    'border-width': 3,
    'border-opacity': 0.8,
  }},
  { selector: 'node[type="domain"]', style: {
    'width': 70, 'height': 70,
    'background-color': '#1565c0', 'border-color': '#0d47a1',
    'shape': 'ellipse',
  }},
  { selector: 'node[type="subdomain"]', style: {
    'width': 40, 'height': 40,
    'background-color': '#66bb6a', 'border-color': '#2e7d32',
    'shape': 'ellipse',
  }},
  { selector: 'node[type="ip"]', style: {
    'width': 50, 'height': 50,
    'background-color': '#ffb74d', 'border-color': '#ef6c00',
    'shape': 'round-rectangle',
  }},
  { selector: 'node[type="mx"]', style: {
    'width': 45, 'height': 45,
    'background-color': '#ba68c8', 'border-color': '#8e24aa',
    'shape': 'diamond',
  }},
  { selector: 'node[type="ns"]', style: {
    'width': 45, 'height': 45,
    'background-color': '#4dd0e1', 'border-color': '#00838f',
    'shape': 'round-hexagon',
  }},
  { selector: 'node[type="certificate"]', style: {
    'width': 40, 'height': 40,
    'background-color': '#7986cb', 'border-color': '#5c6bc0',
    'shape': 'round-octagon',
  }},
  { selector: 'node[type="port"]', style: {
    'width': 35, 'height': 35,
    'background-color': '#a1887f', 'border-color': '#8d6e63',
    'shape': 'round-rectangle',
  }},
  { selector: 'node[type="technology"]', style: {
    'width': 40, 'height': 40,
    'background-color': '#90a4ae', 'border-color': '#607d8b',
    'shape': 'round-rectangle',
  }},
  { selector: 'node[type="asn"]', style: {
    'width': 45, 'height': 45,
    'background-color': '#4db6ac', 'border-color': '#00897b',
    'shape': 'round-rectangle',
  }},
  { selector: 'edge', style: {
    'width': 2.4, 'line-color': '#607d8b',
    'target-arrow-color': '#546e7a', 'target-arrow-shape': 'triangle',
    'curve-style': 'bezier', 'opacity': 0.95,
    'line-style': 'solid',
    'label': showEdgeLabels ? 'data(edgeType)' : '',
    'font-size': 9,
    'text-background-color': '#ffffff',
    'text-background-opacity': 0.85,
    'text-background-padding': 2,
    'text-rotation': 'autorotate',
  }},
  { selector: 'edge[edgeType = "HAS_SUBDOMAIN"]', style: {
    'line-color': '#66bb6a',
    'target-arrow-color': '#43a047',
    'width': 2.8,
  }},
  { selector: 'node:selected', style: {
    'border-width': 5,
    'border-color': '#d84315',
    'border-opacity': 1,
    'z-index': 9999,
  }},
]

function buildElements(nodes: GraphNode[], edges: GraphEdge[]) {
  const cyNodes = nodes.map((n) => ({
    group: 'nodes' as const,
    data: n.data,
  }))
  const cyEdges = edges.map((e) => ({
    group: 'edges' as const,
    data: e.data,
  }))
  return [...cyNodes, ...cyEdges]
}

const InvestigationCanvas = forwardRef<InvestigationCanvasHandle, InvestigationCanvasProps>(
  (
    {
      nodes,
      edges,
      onNodeRightClick,
      onNodeClick,
      onSelectionChange,
      showEdgeLabels = false,
    },
    ref
  ) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const onSelectionChangeRef = useRef(onSelectionChange)
  onSelectionChangeRef.current = onSelectionChange

  useImperativeHandle(ref, () => ({
    exportPng: (): Promise<Blob> => {
      const cy = cyRef.current
      if (!cy) return Promise.reject(new Error('Canvas not ready'))
      // Cytoscape 3.x returns a Blob synchronously for output: 'blob' (not a Promise).
      return new Promise((resolve, reject) => {
        requestAnimationFrame(() => {
          try {
            const inst = cyRef.current
            if (!inst) {
              reject(new Error('Canvas not ready'))
              return
            }
            const result = inst.png({
              output: 'blob',
              full: true,
              bg: '#fafafa',
              scale: 2,
            }) as unknown
            if (result instanceof Blob) {
              resolve(result)
              return
            }
            if (
              result &&
              typeof result === 'object' &&
              'then' in result &&
              typeof (result as PromiseLike<Blob>).then === 'function'
            ) {
              Promise.resolve(result as PromiseLike<Blob>).then(resolve, reject)
              return
            }
            reject(new Error('PNG export returned unexpected type'))
          } catch (e) {
            reject(e)
          }
        })
      })
    },
    clearSelection: () => {
      const cy = cyRef.current
      if (!cy) return
      cy.nodes().unselect()
      onSelectionChangeRef.current?.([])
    },
    focusNode: (nodeId: string) => {
      const cy = cyRef.current
      if (!cy) return
      const node = cy.getElementById(nodeId)
      if (node.length > 0) {
        cy.animate({ center: { eles: node }, zoom: 1.5 }, { duration: 300 })
      }
    },
    setSelectionToIds: (nodeIds: string[]) => {
      const cy = cyRef.current
      if (!cy) return
      const idSet = new Set(nodeIds)
      cy.batch(() => {
        cy.nodes().forEach((n) => {
          if (idSet.has(n.id())) n.select()
          else n.unselect()
        })
      })
      const selected = cy.nodes(':selected')
      onSelectionChangeRef.current?.(Array.from(selected) as NodeSingular[])
    },
  }))

  useEffect(() => {
    if (!containerRef.current) return

    const elements = buildElements(nodes, edges)

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 1.5,
      boxSelectionEnabled: true,
      style: getCytoscapeStyle(showEdgeLabels) as StylesheetJson,
      layout: {
        name: elements.length > 0 ? 'cose' : 'preset',
        fit: false,
        nodeRepulsion: 180000,
        idealEdgeLength: (edge: any) => edge.data('edgeType') === 'HAS_SUBDOMAIN' ? 60 : 90,
        edgeElasticity: (edge: any) => edge.data('edgeType') === 'HAS_SUBDOMAIN' ? 180 : 80,
        gravity: 0.25,
        numIter: 900,
        padding: 20,
        animate: false,
      },
    })

    cy.on('cxttapstart', (evt) => {
      evt.originalEvent?.preventDefault?.()
    })
    cy.on('cxttap', 'node', (evt) => {
      evt.preventDefault()
      evt.originalEvent?.preventDefault?.()
      const node = evt.target
      const pos = evt.position || evt.renderedPosition
      onNodeRightClick(node, pos.x, pos.y)
    })

    if (onNodeClick || onSelectionChange) {
      cy.on('tap', 'node', (evt) => {
        const oe = evt.originalEvent as MouseEvent | undefined
        if (oe?.shiftKey) {
          evt.preventDefault()
          const root = evt.target as NodeSingular
          const ids = collectDescendantNodeIds(cy, root.id())
          setTimeout(() => {
            cy.batch(() => {
              cy.nodes().unselect()
              ids.forEach((id) => {
                const n = cy.getElementById(id)
                if (n.nonempty()) n.select()
              })
            })
          }, 0)
          onNodeClick?.(root)
          return
        }
        onNodeClick?.(evt.target as NodeSingular)
      })
    }

    if (onSelectionChange) {
      const syncSelection = () => {
        const selected = cy.nodes(':selected')
        onSelectionChange(Array.from(selected))
      }
      cy.on('boxend', syncSelection)
      cy.on('select unselect', 'node', syncSelection)
      cy.on('tap', (evt) => {
        if (evt.target === cy) syncSelection()
      })
    }

    const rootDomain = cy.nodes('[type = "domain"]').first()
    if (rootDomain && rootDomain.length > 0) {
      cy.center(rootDomain)
    }

    try {
      ;(cy as unknown as { lassoSelectionEnabled?: (v: boolean) => void }).lassoSelectionEnabled?.(true)
    } catch {
      /* ignore if extension failed */
    }

    cyRef.current = cy

    return () => {
      try {
        ;(cy as unknown as { lassoSelectionEnabled?: (v: boolean) => void }).lassoSelectionEnabled?.(false)
      } catch {
        /* ignore */
      }
      cy.destroy()
      cyRef.current = null
    }
  }, [nodes, edges, onNodeRightClick, onNodeClick, onSelectionChange, showEdgeLabels])

  return (
    <Box sx={{ position: 'relative' }}>
      <Paper
        ref={containerRef}
        elevation={0}
        sx={{
          width: '100%',
          height: '560px',
          bgcolor: '#fafafa',
          backgroundImage: 'radial-gradient(circle, #e0e0e0 1px, transparent 1px)',
          backgroundSize: '20px 20px',
          borderRadius: 2,
          border: '1px solid #e0e0e0',
        }}
      />
      <Box sx={{ mt: 1, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Chip label="Right-click node for enrichers" size="small" variant="outlined" />
        <Chip label="Scroll to zoom" size="small" variant="outlined" />
        <Chip label="Drag to pan" size="small" variant="outlined" />
        <Chip label="Ctrl+drag (Cmd on Mac): box selection" size="small" variant="outlined" />
        <Chip label="Shift+drag: lasso selection" size="small" variant="outlined" />
        <Chip label="Shift+click node: subtree selection" size="small" variant="outlined" />
      </Box>
    </Box>
  )
})

InvestigationCanvas.displayName = 'InvestigationCanvas'

export default InvestigationCanvas
