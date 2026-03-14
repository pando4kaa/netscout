import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import {
  Container,
  Typography,
  Box,
  Button,
  CircularProgress,
  Alert,
  TextField,
  Grid,
  IconButton,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Stack,
  Menu,
  MenuItem,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import DownloadIcon from '@mui/icons-material/Download'
import SearchIcon from '@mui/icons-material/Search'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera'
import ShareIcon from '@mui/icons-material/Share'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { investigationsApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { InvestigationDetail, GraphNode, GraphEdge, ENRICHER_OPSEC } from '../types'
import InvestigationCanvas, {
  type InvestigationCanvasHandle,
} from '../components/investigation/InvestigationCanvas'
import InvestigationContextMenu from '../components/investigation/InvestigationContextMenu'
import AddEntityDialog from '../components/investigation/AddEntityDialog'
import EntityDetailsPanel from '../components/investigation/EntityDetailsPanel'
import InvestigationGeoMap from '../components/investigation/InvestigationGeoMap'
import InvestigationConsole, {
  formatTime,
  type ConsoleLogEntry,
  type ConsoleLogLevel,
} from '../components/investigation/InvestigationConsole'
import type { NodeSingular } from 'cytoscape'

const getEntityValueFromNode = (data: Record<string, unknown>): string => {
  const nodeType = String(data.type || 'domain')
  if (nodeType === 'domain' || nodeType === 'subdomain' || nodeType === 'technology') {
    return String(data.name || data.label || data.id || '')
  }
  if (nodeType === 'ip') {
    return String(data.address || data.label || data.id || '')
  }
  if (nodeType === 'mx' || nodeType === 'ns' || nodeType === 'certificate') {
    return String(data.host || data.label || data.id || '')
  }
  if (nodeType === 'asn') {
    return String(data.number || data.label || data.id || '')
  }
  if (nodeType === 'port') {
    return String(data.port || data.label || data.id || '')
  }
  return String(data.label || data.id || '')
}

const InvestigationDetailPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isAuthenticated, token } = useAuth()
  const [investigation, setInvestigation] = useState<InvestigationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    nodeId: string
    nodeType: string
    nodeValue: string
  } | null>(null)
  const [selectedNode, setSelectedNode] = useState<{
    id: string
    type: string
    value: string
    data?: Record<string, unknown>
  } | null>(null)
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [enricherLoading, setEnricherLoading] = useState(false)
  const [nameEditing, setNameEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLogEntry[]>([])
  const [showEdgeLabels, setShowEdgeLabels] = useState(false)
  const canvasRef = useRef<InvestigationCanvasHandle | null>(null)
  const [selectedNodes, setSelectedNodes] = useState<string[]>([])
  const [shareDialogOpen, setShareDialogOpen] = useState(false)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [confirmActiveDialog, setConfirmActiveDialog] = useState<{
    enricherName: string
    nodeType: string
    nodeValue: string
  } | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null)
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
    if (!id) return
    try {
      const data = await investigationsApi.get(id)
      setInvestigation(data)
      setEditName(data.name)
      setSelectedNode((prev) => {
        if (!prev) return prev
        const refreshed = (data.graph?.nodes || []).find((n: GraphNode) => n.data.id === prev.id)
        if (!refreshed) return prev
        const d = refreshed.data as Record<string, unknown>
        return {
          id: String(d.id),
          type: String(d.type || prev.type),
          value: getEntityValueFromNode(d),
          data: d,
        }
      })
    } catch (err) {
      setError('Failed to load investigation')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [id])

  const consoleStorageKey = useMemo(
    () => (id ? `investigation_console_logs_${id}` : ''),
    [id]
  )

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    loadInvestigation()
  }, [isAuthenticated, navigate, loadInvestigation])

  useEffect(() => {
    const preventContextMenu = (ev: Event) => {
      const target = ev.target as Element
      const inInvestigation = target?.closest?.('[data-no-context-menu]')
      const menuOpen = document.querySelector('[role="menu"]')
      if (inInvestigation || menuOpen) {
        ev.preventDefault()
        ev.stopPropagation()
      }
    }
    document.addEventListener('contextmenu', preventContextMenu, { capture: true })
    return () => document.removeEventListener('contextmenu', preventContextMenu, { capture: true })
  }, [])

  useEffect(() => {
    if (!consoleStorageKey) return
    try {
      const raw = window.localStorage.getItem(consoleStorageKey)
      if (!raw) {
        setConsoleLogs([])
        return
      }
      const parsed = JSON.parse(raw) as ConsoleLogEntry[]
      setConsoleLogs(Array.isArray(parsed) ? parsed.slice(-250) : [])
    } catch {
      setConsoleLogs([])
    }
  }, [consoleStorageKey])

  useEffect(() => {
    if (!consoleStorageKey) return
    window.localStorage.setItem(consoleStorageKey, JSON.stringify(consoleLogs.slice(-250)))
  }, [consoleLogs, consoleStorageKey])

  const handleNodeRightClick = useCallback((node: NodeSingular, x: number, y: number) => {
    const data = node.data() as Record<string, unknown>
    const nodeId = data.id as string
    const nodeType = (data.type as string) || 'domain'
    const nodeValue = getEntityValueFromNode(data) || nodeId
    setContextMenu({ x, y, nodeId, nodeType, nodeValue })
  }, [])

  const handleNodeClick = useCallback((node: NodeSingular) => {
    const data = node.data() as Record<string, unknown>
    setSelectedNode({
      id: data.id as string,
      type: (data.type as string) || 'domain',
      value: getEntityValueFromNode(data),
      data,
    })
  }, [])

  const handleSelectionChange = useCallback((selected: NodeSingular[]) => {
    setSelectedNodes(selected.map((n) => n.id()))
  }, [])

  const allNodes = (investigation?.graph?.nodes ?? []) as GraphNode[]
  const allEdges = (investigation?.graph?.edges ?? []) as GraphEdge[]

  const handleSearch = useCallback(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q || !allNodes.length) return
    const match = allNodes.find((n) => {
      const d = n.data as Record<string, unknown>
      const label = String(d?.label ?? '')
      const id = String(d?.id ?? '')
      const name = String(d?.name ?? '')
      const address = String(d?.address ?? '')
      const host = String(d?.host ?? '')
      return (
        label.toLowerCase().includes(q) ||
        id.toLowerCase().includes(q) ||
        name.toLowerCase().includes(q) ||
        address.toLowerCase().includes(q) ||
        host.toLowerCase().includes(q)
      )
    })
    if (match) {
      canvasRef.current?.focusNode(match.data.id)
    }
  }, [searchQuery, allNodes])

  const toGraphML = useCallback((nodes: GraphNode[], edges: GraphEdge[]) => {
    const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'
    xml += '  <key id="label" for="node" attr.name="label" attr.type="string"/>\n'
    xml += '  <key id="type" for="node" attr.name="type" attr.type="string"/>\n'
    xml += '  <graph id="G" edgedefault="directed">\n'
    for (const n of nodes) {
      const d = n.data as Record<string, unknown>
      const label = esc(String(d?.label ?? d?.id ?? ''))
      const type = esc(String(d?.type ?? ''))
      xml += `    <node id="${esc(String(d?.id ?? ''))}"><data key="label">${label}</data><data key="type">${type}</data></node>\n`
    }
    for (const e of edges) {
      const d = e.data as Record<string, unknown>
      const label = esc(String(d?.edgeType ?? 'RELATES_TO'))
      xml += `    <edge source="${esc(String(d?.source ?? ''))}" target="${esc(String(d?.target ?? ''))}"><data key="label">${label}</data></edge>\n`
    }
    xml += '  </graph>\n</graphml>'
    return xml
  }, [])

  const addConsoleLog = useCallback((level: ConsoleLogLevel, message: string) => {
    setConsoleLogs((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        timestamp: formatTime(),
        level,
        message,
      },
    ])
  }, [])

  const runEnricherImpl = useCallback(
    async (enricherName: string, nodeType: string, nodeValue: string) => {
      if (!id) return
      setEnricherLoading(true)
      setError(null)
      addConsoleLog('INFO', `Transform ${nodeType}_to_${enricherName} started.`)
      try {
        let result = await investigationsApi.runEnricher(
          id,
          nodeType,
          nodeValue,
          enricherName
        ) as { task_id?: string; status?: string; new_nodes?: unknown[]; new_edges?: unknown[]; message?: string; error?: string }
        if (result.task_id && result.status === 'pending') {
          addConsoleLog('INFO', 'Enricher queued, polling for result...')
          const pollInterval = 1500
          const maxAttempts = 120
          for (let i = 0; i < maxAttempts; i++) {
            await new Promise((r) => setTimeout(r, pollInterval))
            const status = await investigationsApi.getEnricherTaskStatus(id, result.task_id!)
            result = status as typeof result
            if (result.status === 'success' || result.status === 'failure') break
          }
        }
        setContextMenu(null)
        setConfirmActiveDialog(null)
        const nn = result?.new_nodes?.length ?? 0
        const ne = result?.new_edges?.length ?? 0
        if (result?.status === 'failure') {
          setError(result.error || 'Enricher failed')
          addConsoleLog('ERR', `Transform ${nodeType}_to_${enricherName} failed: ${result.error}`)
        } else if (nn > 0 || ne > 0) {
          addConsoleLog('GRPH', `${nodeValue} -> ${nn} node(s), ${ne} edge(s) found.`)
        } else {
          const msg = result?.message || 'No new data returned'
          addConsoleLog('INFO', msg)
        }
        addConsoleLog('CMPL', `Transform ${nodeType}_to_${enricherName} finished.`)
        await loadInvestigation()
        window.setTimeout(() => {
          void loadInvestigation()
        }, 450)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Enricher failed'
        setError(msg)
        addConsoleLog('ERR', `Transform ${nodeType}_to_${enricherName} failed: ${msg}`)
        console.error(err)
      } finally {
        setEnricherLoading(false)
      }
    },
    [id, loadInvestigation, addConsoleLog]
  )

  const handleRunEnricher = useCallback(
    async (enricherName: string) => {
      if (!id || !contextMenu) return
      const { nodeType, nodeValue } = contextMenu
      if (ENRICHER_OPSEC[enricherName] === 'active') {
        setConfirmActiveDialog({ enricherName, nodeType, nodeValue })
        return
      }
      await runEnricherImpl(enricherName, nodeType, nodeValue)
    },
    [id, contextMenu, runEnricherImpl]
  )

  const handleAddEntity = useCallback(
    async (entityType: string, entityValue: string) => {
      if (!id) return
      await investigationsApi.addEntity(id, entityType, entityValue)
      await loadInvestigation()
    },
    [id, loadInvestigation]
  )

  const handleSaveNotesTags = useCallback(
    async (cyId: string, notes: string, tags: string[]) => {
      if (!id) return
      await investigationsApi.updateEntityMetadata(id, cyId, { notes, tags })
      await loadInvestigation()
      setSelectedNode((prev) => {
        if (!prev || prev.id !== cyId) return prev
        return { ...prev, data: { ...prev.data, notes, tags } }
      })
    },
    [id, loadInvestigation]
  )

  const handleSaveName = async () => {
    if (!id || !editName.trim()) return
    try {
      await investigationsApi.update(id, editName.trim())
      setInvestigation((prev) => (prev ? { ...prev, name: editName.trim() } : null))
      setNameEditing(false)
    } catch (err) {
      setError('Failed to update name')
    }
  }

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

  if (!isAuthenticated) return null

  if (loading || !id) {
    return (
      <Container maxWidth="xl" sx={{ py: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    )
  }

  if (!investigation) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Alert severity="error">Investigation not found</Alert>
        <Button component={Link} to="/investigations" sx={{ mt: 2, textTransform: 'none' }}>
          Back to Investigations
        </Button>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }} data-no-context-menu>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <IconButton component={Link} to="/investigations" size="small">
          <ArrowBackIcon />
        </IconButton>
        {nameEditing ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
            <TextField
              size="small"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSaveName()}
              sx={{ minWidth: 300 }}
            />
            <Button size="small" onClick={handleSaveName} sx={{ textTransform: 'none' }}>
              Save
            </Button>
            <Button size="small" onClick={() => setNameEditing(false)} sx={{ textTransform: 'none' }}>
              Cancel
            </Button>
          </Box>
        ) : (
          <Typography variant="h5" fontWeight={600} onClick={() => setNameEditing(true)} sx={{ cursor: 'pointer' }}>
            {investigation.name}
          </Typography>
        )}
        <TextField
          size="small"
          placeholder="Search node (IP, domain...)"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          sx={{ width: 220 }}
          InputProps={{
            startAdornment: <SearchIcon sx={{ mr: 0.5, color: 'action.active', fontSize: 20 }} />,
          }}
        />
        <Button size="small" variant="outlined" onClick={handleSearch} sx={{ textTransform: 'none' }}>
          Go
        </Button>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          endIcon={<ExpandMoreIcon />}
          onClick={(e) => setExportAnchor(e.currentTarget)}
          sx={{ textTransform: 'none' }}
        >
          Export
        </Button>
        <Menu
          anchorEl={exportAnchor}
          open={Boolean(exportAnchor)}
          onClose={() => setExportAnchor(null)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        >
          <MenuItem
            onClick={async () => {
              setExportAnchor(null)
              const data = await investigationsApi.exportJson(id)
              const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
              const url = window.URL.createObjectURL(blob)
              const link = document.createElement('a')
              link.href = url
              link.download = `investigation_${id}.json`
              link.click()
              window.URL.revokeObjectURL(url)
            }}
          >
            JSON
          </MenuItem>
          <MenuItem
            onClick={() => {
              setExportAnchor(null)
              investigationsApi.downloadCsv(id)
            }}
          >
            CSV
          </MenuItem>
          <MenuItem
            onClick={() => {
              setExportAnchor(null)
              const graphml = toGraphML(allNodes, allEdges)
              const blob = new Blob([graphml], { type: 'application/xml' })
              const url = window.URL.createObjectURL(blob)
              const link = document.createElement('a')
              link.href = url
              link.download = `investigation_${id}.graphml`
              link.click()
              window.URL.revokeObjectURL(url)
            }}
          >
            GraphML
          </MenuItem>
        </Menu>
        <Button
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={() => setAddDialogOpen(true)}
          sx={{ textTransform: 'none' }}
        >
          Add Entity
        </Button>
        <Button
          variant="outlined"
          startIcon={<ShareIcon />}
          onClick={async () => {
            try {
              const result = await investigationsApi.createShareLink(id, 7)
              const base = window.location.origin
              setShareUrl(`${base}${result.share_url}`)
              setShareDialogOpen(true)
            } catch (err) {
              setError('Failed to create share link')
            }
          }}
          sx={{ textTransform: 'none' }}
        >
          Share
        </Button>
        <Button
          variant="outlined"
          startIcon={<PhotoCameraIcon />}
          onClick={async () => {
            try {
              const blob = await canvasRef.current?.exportPng()
              if (!blob) return
              const url = window.URL.createObjectURL(blob)
              const link = document.createElement('a')
              link.href = url
              link.download = `investigation_${investigation.name.replace(/\s/g, '_')}_snapshot.png`
              link.click()
              window.URL.revokeObjectURL(url)
            } catch (err) {
              setError('Failed to export snapshot')
            }
          }}
          sx={{ textTransform: 'none' }}
        >
          Snapshot
        </Button>
      </Box>

      {selectedNodes.length > 1 && (
        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="body2" color="text.secondary">
            {selectedNodes.length} nodes selected
          </Typography>
          <Button
            size="small"
            variant="outlined"
            onClick={() => {
              canvasRef.current?.clearSelection()
              setSelectedNodes([])
            }}
            sx={{ textTransform: 'none' }}
          >
            Clear selection
          </Button>
          <Button
            size="small"
            variant="outlined"
            onClick={() => {
              const selNodes = allNodes.filter((n) => selectedNodes.includes(n.data.id))
              const blob = new Blob(
                [JSON.stringify({ nodes: selNodes }, null, 2)],
                { type: 'application/json' }
              )
              const url = window.URL.createObjectURL(blob)
              const link = document.createElement('a')
              link.href = url
              link.download = `investigation_selected_${selectedNodes.length}_nodes.json`
              link.click()
              window.URL.revokeObjectURL(url)
            }}
            sx={{ textTransform: 'none' }}
          >
            Export selected
          </Button>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

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
            ref={canvasRef}
            nodes={nodes}
            edges={edges}
            onNodeRightClick={handleNodeRightClick}
            onNodeClick={handleNodeClick}
            onSelectionChange={handleSelectionChange}
            showEdgeLabels={showEdgeLabels}
          />
          <Box sx={{ mt: 2 }}>
            <InvestigationConsole
              logs={consoleLogs}
              onClear={() => setConsoleLogs([])}
              maxHeight={160}
            />
          </Box>
        </Grid>
        <Grid item xs={12} md={3}>
          <Stack spacing={2}>
            <EntityDetailsPanel
              nodeId={selectedNode?.id ?? null}
              nodeType={selectedNode?.type ?? null}
              nodeValue={selectedNode?.value ?? null}
              nodeData={selectedNode?.data}
              investigationId={id}
              onSaveNotesTags={handleSaveNotesTags}
            />
            <InvestigationGeoMap nodes={allNodes} />
          </Stack>
        </Grid>
      </Grid>

      <InvestigationContextMenu
        anchorPosition={contextMenu ? { x: contextMenu.x, y: contextMenu.y } : null}
        nodeType={contextMenu?.nodeType ?? ''}
        nodeValue={contextMenu?.nodeValue ?? ''}
        nodeId={contextMenu?.nodeId ?? ''}
        onClose={() => setContextMenu(null)}
        onRunEnricher={handleRunEnricher}
        loading={enricherLoading}
      />

      <AddEntityDialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        onAdd={handleAddEntity}
      />

      <Dialog open={shareDialogOpen} onClose={() => setShareDialogOpen(false)}>
        <DialogTitle>Share Investigation</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Anyone with this link can view the investigation (read-only). Link expires in 7 days.
          </DialogContentText>
          {shareUrl && (
            <TextField
              fullWidth
              size="small"
              value={shareUrl}
              readOnly
              onClick={(e) => (e.target as HTMLInputElement).select()}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              if (shareUrl) {
                navigator.clipboard.writeText(shareUrl)
                setShareDialogOpen(false)
              }
            }}
            sx={{ textTransform: 'none' }}
          >
            Copy & Close
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={confirmActiveDialog !== null}
        onClose={() => setConfirmActiveDialog(null)}
      >
        <DialogTitle>Active Enricher Warning</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This enricher will directly contact the target (port scan, SSL handshake, or HTTP
            requests). It may trigger IDS/IPS alerts on the target&apos;s side. Continue?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmActiveDialog(null)} sx={{ textTransform: 'none' }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="warning"
            onClick={() => {
              if (confirmActiveDialog) {
                void runEnricherImpl(
                  confirmActiveDialog.enricherName,
                  confirmActiveDialog.nodeType,
                  confirmActiveDialog.nodeValue
                )
                setConfirmActiveDialog(null)
              }
            }}
            sx={{ textTransform: 'none' }}
          >
            Continue
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default InvestigationDetailPage
