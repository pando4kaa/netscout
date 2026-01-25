import { Box, Button, ButtonGroup } from '@mui/material'
import { Core } from 'cytoscape'

interface GraphControlsProps {
  cy: Core | null
  onLayoutChange?: (layout: string) => void
}

const GraphControls = ({ cy, onLayoutChange }: GraphControlsProps) => {
  const handleLayoutChange = (layoutName: string) => {
    if (cy) {
      cy.layout({ name: layoutName }).run()
      onLayoutChange?.(layoutName)
    }
  }

  const handleFit = () => {
    if (cy) {
      cy.fit()
    }
  }

  const handleReset = () => {
    if (cy) {
      cy.reset()
      cy.fit()
    }
  }

  return (
    <Box sx={{ display: 'flex', gap: 1, p: 2, borderBottom: '1px solid #ccc' }}>
      <ButtonGroup variant="outlined" size="small">
        <Button onClick={() => handleLayoutChange('grid')}>Grid</Button>
        <Button onClick={() => handleLayoutChange('breadthfirst')}>Hierarchical</Button>
        <Button onClick={() => handleLayoutChange('cose')}>Force-directed</Button>
      </ButtonGroup>
      <ButtonGroup variant="outlined" size="small" sx={{ ml: 2 }}>
        <Button onClick={handleFit}>Fit</Button>
        <Button onClick={handleReset}>Reset</Button>
      </ButtonGroup>
    </Box>
  )
}

export default GraphControls
