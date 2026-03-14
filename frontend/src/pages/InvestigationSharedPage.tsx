import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Container,
  Typography,
  Box,
  Button,
  CircularProgress,
  Alert,
  Grid,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Chip,
  IconButton,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { Link, useParams } from 'react-router-dom'
import { investigationsApi } from '../services/api'
import { GraphNode, GraphEdge } from '../types'
import InvestigationCanvas from '../components/investigation/InvestigationCanvas'
import EntityDetailsPanel from '../components/investigation/EntityDetailsPanel'
import InvestigationGeoMap from '../components/investigation/InvestigationGeoMap'
import type { NodeSingular } from 'cytoscape'

const getEntityValueFromNode = (data: Record<string, unknown>): string => {
  const nodeType = String(data.type || 'domain')
  if (nodeType === 'domain' || nodeType === 'subdomain' || nodeType === 'technology') {
    return String(data.name || data.label || data.id || '')
  }
  if (nodeType === 'ip') return String(data.address || data.label || data.id || '')
  if (nodeType === 'mx' || nodeType === 'ns' || nodeType === 'certificate') {
    return String(data.host || data.label || data.id || '')
  }
  if (nodeType === 'asn') return String(data.number || data.label || data.id || '')
  if (nodeType === 'port') return String(data.port || data.label || data.id || '')
  return String(data.label || data.id || '')
}

const InvestigationSharedPage = () => {
  const { token } = useParams<{ token: string }>()
  const [investigation, setInvestigation] = useState<{
    id: string
    name: string
    graph: { nodes: GraphNode[]; edges: GraphEdge[] }
    read_only?: boolean
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<{
    id: string
    type: string
    value: string
    data?: Record<string, unknown>
  } | null>(null)
  const [showEdgeLabels, setShowEdgeLabels] = useState(false)
  const [typeFilter, setTypeFilter] = useState<Record<string, boolean>>({
    domain: true,
    subdomain: true,
    ip: true,
    mx: true,
    ns: true,
    certificate: true,
    port: true,
    technology: true,
    asn: true,
  })

  const loadInvestigation = useCallback(async () => {
    if (!token) return
    try {
      const data = await investigationsApi.getShared(token)
      setInvestigation(data)
    } catch (err) {
      setError('Share link not found or expired')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadInvestigation()
  }, [loadInvestigation])

  const handleNodeRightClickNoop = useCallback(() => {}, [])

  const handleNodeClick = useCallback((node: NodeSingular) => {
    const data = node.data() as Record<string, unknown>
    setSelectedNode({
      id: data.id as string,
      type: (data.type as string) || 'domain',
      value: getEntityValueFromNode(data),
      data,
    })
  }, [])

  const allNodes = (investigation?.graph?.nodes ?? []) as GraphNode[]
  const allEdges = (investigation?.graph?.edges ?? []) as GraphEdge[]
  const { nodes, edges } = useMemo(() => {
    const filteredNodeIds = new Set(
      allNodes.filter((n) => typeFilter[n.data?.type ?? ''] !== false).map((n) => n.data.id)
    )
    return {
      nodes: allNodes.filter((n) => filteredNodeIds.has(n.data.id)),
      edges: allEdges.filter(
        (e) =>
          filteredNodeIds.has(e.data.source) && filteredNodeIds.has(e.data.target)
      ),
    }
  }, [allNodes, allEdges, typeFilter])

  if (loading || !token) {
    return (
      <Container maxWidth="xl" sx={{ py: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    )
  }

  if (error || !investigation) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Alert severity="error">{error || 'Investigation not found'}</Alert>
        <Button component={Link} to="/" sx={{ mt: 2, textTransform: 'none' }}>
          Back to Home
        </Button>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <IconButton component={Link} to="/" size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h5" fontWeight={600}>
          {investigation.name}
        </Typography>
        <Chip label="Read-only" size="small" color="default" variant="outlined" />
      </Box>

      <Box sx={{ mb: 2 }}>
        <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
          Filter by type:
        </Typography>
        <FormGroup row>
          {(['domain', 'subdomain', 'ip', 'mx', 'ns', 'certificate', 'port', 'technology', 'asn'] as const).map(
            (t) => (
              <FormControlLabel
                key={t}
                control={
                  <Checkbox
                    size="small"
                    checked={typeFilter[t] !== false}
                    onChange={(_, checked) => setTypeFilter((prev) => ({ ...prev, [t]: checked }))}
                  />
                }
                label={t}
              />
            )
          )}
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={showEdgeLabels}
                onChange={(_, checked) => setShowEdgeLabels(checked)}
              />
            }
            label="edge labels"
          />
        </FormGroup>
      </Box>

      <Grid container spacing={2}>
        <Grid item xs={12} md={9}>
          <InvestigationCanvas
            nodes={nodes}
            edges={edges}
            onNodeRightClick={handleNodeRightClickNoop}
            onNodeClick={handleNodeClick}
            showEdgeLabels={showEdgeLabels}
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <EntityDetailsPanel
              nodeId={selectedNode?.id ?? null}
              nodeType={selectedNode?.type ?? null}
              nodeValue={selectedNode?.value ?? null}
              nodeData={selectedNode?.data}
            />
            <InvestigationGeoMap nodes={allNodes} />
          </Box>
        </Grid>
      </Grid>
    </Container>
  )
}

export default InvestigationSharedPage
