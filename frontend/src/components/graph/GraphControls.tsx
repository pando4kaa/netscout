import { useState, useCallback, useEffect } from 'react'
import {
  Box,
  Button,
  ButtonGroup,
  Tooltip,
  Paper,
  Typography,
  Divider,
  FormGroup,
  FormControlLabel,
  Checkbox,
  TextField,
  InputAdornment,
  Slider,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import FullscreenIcon from '@mui/icons-material/Fullscreen'
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit'
import { Core } from 'cytoscape'
import ZoomInIcon from '@mui/icons-material/ZoomIn'
import ZoomOutIcon from '@mui/icons-material/ZoomOut'
import FitScreenIcon from '@mui/icons-material/FitScreen'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong'
import DownloadIcon from '@mui/icons-material/Download'
import GridViewIcon from '@mui/icons-material/GridView'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import BubbleChartIcon from '@mui/icons-material/BubbleChart'
import RadioButtonCheckedIcon from '@mui/icons-material/RadioButtonChecked'
import ScatterPlotIcon from '@mui/icons-material/ScatterPlot'

interface GraphControlsProps {
  cy: Core | null
  onLayoutChange?: (layout: string) => void
  graphWrapperRef?: React.RefObject<HTMLDivElement | null>
}

const LAYOUTS = [
  { 
    name: 'concentric', 
    label: 'Radial', 
    icon: <RadioButtonCheckedIcon fontSize="small" />,
    options: {
      concentric: (node: any) => {
        const type = node.data('type')
        if (type === 'domain') return 100
        if (type === 'ip') return 75
        if (type === 'ns') return 60
        if (type === 'mx') return 60
        if (type === 'certificate' || type === 'port') return 20
        return 35
      },
      levelWidth: () => 3,
      minNodeSpacing: 70,
      spacingFactor: 2,
      animate: true,
      animationDuration: 500,
    }
  },
  { 
    name: 'cose', 
    label: 'Force', 
    icon: <BubbleChartIcon fontSize="small" />,
    options: {
      nodeRepulsion: 8000,
      idealEdgeLength: 100,
      edgeElasticity: 100,
      nestingFactor: 1.2,
      gravity: 0.25,
      numIter: 1000,
      animate: true,
      animationDuration: 500,
    }
  },
  { 
    name: 'breadthfirst', 
    label: 'Tree', 
    icon: <AccountTreeIcon fontSize="small" />,
    options: {
      directed: true,
      spacingFactor: 1.5,
      avoidOverlap: true,
      animate: true,
      animationDuration: 500,
    }
  },
  { 
    name: 'circle', 
    label: 'Circle', 
    icon: <ScatterPlotIcon fontSize="small" />,
    options: {
      animate: true,
      animationDuration: 500,
      avoidOverlap: true,
      spacingFactor: 1.2,
    }
  },
  { 
    name: 'grid', 
    label: 'Grid', 
    icon: <GridViewIcon fontSize="small" />,
    options: {
      animate: true,
      animationDuration: 500,
      avoidOverlap: true,
      spacingFactor: 1.2,
    }
  },
]

const NODE_TYPE_OPTIONS = [
  { key: 'domain', label: 'Domain' },
  { key: 'subdomain', label: 'Subdomain' },
  { key: 'ip', label: 'IP' },
  { key: 'mx', label: 'MX' },
  { key: 'ns', label: 'NS' },
  { key: 'certificate', label: 'Certificate' },
  { key: 'port', label: 'Port' },
] as const

const MIN_ZOOM = 0.2
const MAX_ZOOM = 3

const GraphControls = ({ cy, onLayoutChange, graphWrapperRef }: GraphControlsProps) => {
  const [activeLayout, setActiveLayout] = useState('concentric')
  const [visibleTypes, setVisibleTypes] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(NODE_TYPE_OPTIONS.map((o) => [o.key, true]))
  )
  const [searchQuery, setSearchQuery] = useState('')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [zoomValue, setZoomValue] = useState(1)

  const applyFilter = useCallback(
    (types: Record<string, boolean>) => {
      if (!cy) return
      cy.nodes().forEach((node) => {
        const nodeType = node.data('type')
        if (types[nodeType] !== false) {
          node.show()
        } else {
          node.hide()
        }
      })
    },
    [cy]
  )

  const handleFilterChange = (key: string, checked: boolean) => {
    const next = { ...visibleTypes, [key]: checked }
    setVisibleTypes(next)
    applyFilter(next)
  }

  useEffect(() => {
    if (cy) applyFilter(visibleTypes)
  }, [cy, visibleTypes, applyFilter])

  useEffect(() => {
    if (cy) {
      setZoomValue(cy.zoom())
      const onZoom = () => setZoomValue(cy.zoom())
      cy.on('zoom', onZoom)
      return () => cy.off('zoom', onZoom)
    }
  }, [cy])

  const handleSearch = () => {
    if (!cy || !searchQuery.trim()) return
    const q = searchQuery.trim().toLowerCase()
    const match = cy.nodes().filter((n: any) => {
      const label = (n.data('fullLabel') || n.data('label') || n.data('id') || '').toLowerCase()
      return label.includes(q)
    })
    if (match.length > 0) {
      const toFit = match.length === 1 ? match.union(match.neighborhood()) : match
      cy.animate({ fit: { eles: toFit, padding: 80 }, duration: 400 })
      cy.elements().removeClass('highlighted')
      match.addClass('highlighted')
      setTimeout(() => match.removeClass('highlighted'), 2000)
    }
  }

  const handleFullscreen = () => {
    if (!graphWrapperRef?.current) return
    if (!document.fullscreenElement) {
      graphWrapperRef.current.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  useEffect(() => {
    const onFullscreenChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', onFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', onFullscreenChange)
  }, [])

  const handleZoomSlider = (_: Event, value: number | number[]) => {
    const v = Array.isArray(value) ? value[0] : value
    setZoomValue(v)
    if (cy) {
      cy.zoom({
        level: v,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
      })
    }
  }

  const handleLayoutChange = (layoutName: string, options: any = {}) => {
    if (cy) {
      setActiveLayout(layoutName)
      cy.layout({ name: layoutName, ...options }).run()
      onLayoutChange?.(layoutName)
    }
  }

  const handleZoomIn = () => {
    if (cy) {
      cy.zoom({
        level: cy.zoom() * 1.3,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
      })
    }
  }

  const handleZoomOut = () => {
    if (cy) {
      cy.zoom({
        level: cy.zoom() / 1.3,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
      })
    }
  }

  const handleFit = () => {
    if (cy) {
      cy.fit(undefined, 50)
    }
  }

  const handleCenter = () => {
    if (cy) {
      cy.center()
    }
  }

  const handleReset = () => {
    if (cy) {
      cy.reset()
      cy.fit(undefined, 50)
    }
  }

  const handleExportPNG = () => {
    if (cy) {
      const png = cy.png({
        full: true,
        scale: 2,
        bg: '#fafafa',
      })
      const link = document.createElement('a')
      link.href = png
      link.download = `graph-${new Date().toISOString().slice(0, 10)}.png`
      link.click()
    }
  }

  const handleExportJSON = () => {
    if (cy) {
      const elements = cy.elements().jsons()
      const data = { nodes: elements.filter((e: any) => e.group === 'nodes'), edges: elements.filter((e: any) => e.group === 'edges') }
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `graph-${new Date().toISOString().slice(0, 10)}.json`
      link.click()
      URL.revokeObjectURL(link.href)
    }
  }

  const handleExportGEXF = () => {
    if (!cy) return
    const nodes = cy.nodes()
    const edges = cy.edges()
    const escapeXml = (s: string) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">\n<graph mode="static" defaultedgetype="directed">\n<nodes>\n'
    nodes.forEach((node: any) => {
      const d = node.data()
      xml += `<node id="${escapeXml(d.id)}" label="${escapeXml(d.label || d.id)}">`
      if (d.type) xml += `<attvalues><attvalue for="0" value="${escapeXml(d.type)}"/></attvalues>`
      xml += '</node>\n'
    })
    xml += '</nodes>\n<edges>\n'
    edges.forEach((edge: any, i: number) => {
      const d = edge.data()
      xml += `<edge id="e${i}" source="${escapeXml(d.source)}" target="${escapeXml(d.target)}"/>\n`
    })
    xml += '</edges>\n</graph>\n</gexf>'
    const blob = new Blob([xml], { type: 'application/xml' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `graph-${new Date().toISOString().slice(0, 10)}.gexf`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  return (
    <Paper sx={{ p: 2, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2 }}>
      {/* Search */}
      <Box sx={{ minWidth: 220 }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Search
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
          <TextField
            size="small"
            placeholder="Subdomain, IP..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              },
            }}
            sx={{ flex: 1, '& .MuiInputBase-root': { bgcolor: 'background.paper' } }}
          />
          <Button size="small" variant="contained" onClick={handleSearch}>
            Find
          </Button>
        </Box>
      </Box>

      <Divider orientation="vertical" flexItem />

      {/* Layout buttons */}
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Layout
        </Typography>
        <ButtonGroup variant="outlined" size="small">
          {LAYOUTS.map((layout) => (
            <Tooltip key={layout.name} title={layout.label}>
              <Button
                onClick={() => handleLayoutChange(layout.name, layout.options)}
                variant={activeLayout === layout.name ? 'contained' : 'outlined'}
                sx={{ minWidth: 40 }}
              >
                {layout.icon}
              </Button>
            </Tooltip>
          ))}
        </ButtonGroup>
      </Box>

      <Divider orientation="vertical" flexItem />

      {/* Zoom controls */}
      <Box sx={{ minWidth: 140 }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Zoom
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Tooltip title="Zoom Out">
            <Button size="small" onClick={handleZoomOut} sx={{ minWidth: 36 }}>
              <ZoomOutIcon fontSize="small" />
            </Button>
          </Tooltip>
          <Slider
            value={zoomValue}
            min={MIN_ZOOM}
            max={MAX_ZOOM}
            step={0.1}
            onChange={handleZoomSlider}
            sx={{ width: 80 }}
            size="small"
          />
          <Tooltip title="Zoom In">
            <Button size="small" onClick={handleZoomIn} sx={{ minWidth: 36 }}>
              <ZoomInIcon fontSize="small" />
            </Button>
          </Tooltip>
        </Box>
      </Box>

      <Divider orientation="vertical" flexItem />

      {/* View controls */}
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          View
        </Typography>
        <ButtonGroup variant="outlined" size="small">
          {graphWrapperRef && (
            <Tooltip title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen mode'}>
              <Button onClick={handleFullscreen}>
                {isFullscreen ? <FullscreenExitIcon fontSize="small" /> : <FullscreenIcon fontSize="small" />}
              </Button>
            </Tooltip>
          )}
          <Tooltip title="Fit to Screen">
            <Button onClick={handleFit}>
              <FitScreenIcon fontSize="small" />
            </Button>
          </Tooltip>
          <Tooltip title="Center">
            <Button onClick={handleCenter}>
              <CenterFocusStrongIcon fontSize="small" />
            </Button>
          </Tooltip>
          <Tooltip title="Reset View">
            <Button onClick={handleReset}>
              <RestartAltIcon fontSize="small" />
            </Button>
          </Tooltip>
        </ButtonGroup>
      </Box>

      <Divider orientation="vertical" flexItem />

      {/* Node type filter */}
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Filter
        </Typography>
        <FormGroup row sx={{ flexWrap: 'wrap', gap: 0 }}>
          {NODE_TYPE_OPTIONS.map(({ key, label }) => (
            <FormControlLabel
              key={key}
              control={
                <Checkbox
                  size="small"
                  checked={visibleTypes[key] !== false}
                  onChange={(_, checked) => handleFilterChange(key, checked)}
                />
              }
              label={label}
              sx={{ mr: 1 }}
            />
          ))}
        </FormGroup>
      </Box>

      <Divider orientation="vertical" flexItem />

      {/* Export */}
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Export
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          <Tooltip title="Download as PNG">
            <Button variant="outlined" size="small" onClick={handleExportPNG} startIcon={<DownloadIcon />}>
              PNG
            </Button>
          </Tooltip>
          <Tooltip title="Download as JSON">
            <Button variant="outlined" size="small" onClick={handleExportJSON}>
              JSON
            </Button>
          </Tooltip>
          <Tooltip title="Download as GEXF (Gephi)">
            <Button variant="outlined" size="small" onClick={handleExportGEXF}>
              GEXF
            </Button>
          </Tooltip>
        </Box>
      </Box>
    </Paper>
  )
}

export default GraphControls
