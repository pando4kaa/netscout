import { useState } from 'react'
import {
  Box,
  Button,
  ButtonGroup,
  IconButton,
  Tooltip,
  Paper,
  Slider,
  Typography,
  Divider,
} from '@mui/material'
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
        if (type === 'ip') return 70
        if (type === 'ns') return 50
        if (type === 'mx') return 50
        return 30
      },
      levelWidth: () => 1,
      minNodeSpacing: 25,
      spacingFactor: 0.95,
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

const GraphControls = ({ cy, onLayoutChange }: GraphControlsProps) => {
  const [activeLayout, setActiveLayout] = useState('concentric')

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

  return (
    <Paper sx={{ p: 2, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2 }}>
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
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Zoom
        </Typography>
        <ButtonGroup variant="outlined" size="small">
          <Tooltip title="Zoom Out">
            <Button onClick={handleZoomOut}>
              <ZoomOutIcon fontSize="small" />
            </Button>
          </Tooltip>
          <Tooltip title="Zoom In">
            <Button onClick={handleZoomIn}>
              <ZoomInIcon fontSize="small" />
            </Button>
          </Tooltip>
        </ButtonGroup>
      </Box>

      <Divider orientation="vertical" flexItem />

      {/* View controls */}
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          View
        </Typography>
        <ButtonGroup variant="outlined" size="small">
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

      {/* Export */}
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Export
        </Typography>
        <Tooltip title="Download as PNG">
          <Button variant="outlined" size="small" onClick={handleExportPNG} startIcon={<DownloadIcon />}>
            PNG
          </Button>
        </Tooltip>
      </Box>
    </Paper>
  )
}

export default GraphControls
