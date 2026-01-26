import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'
import { buildGraphElements } from '../../utils/graphBuilder'
import { ScanResults } from '../../types'

interface GraphViewProps {
  data: ScanResults | null
  setCyInstance?: (cy: cytoscape.Core | null) => void
}

const GraphView = ({ data, setCyInstance }: GraphViewProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  useEffect(() => {
    if (!containerRef.current || !data) {
      if (setCyInstance) setCyInstance(null)
      return
    }

    const elements = buildGraphElements(data)

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            width: 30,
            height: 30,
            'background-color': 'data(color)',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': '#ccc',
            'target-arrow-color': '#ccc',
            'target-arrow-shape': 'triangle',
          },
        },
      ],
      layout: {
        name: 'grid',
      },
    })

    cyRef.current = cy
    if (setCyInstance) setCyInstance(cy)

    return () => {
      cy.destroy()
      if (setCyInstance) setCyInstance(null)
    }
  }, [data, setCyInstance])

  if (!data) {
    return (
      <div style={{ width: '100%', height: '600px', border: '1px solid #ccc', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p>No data available</p>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '600px', border: '1px solid #ccc' }}
    />
  )
}

export default GraphView
