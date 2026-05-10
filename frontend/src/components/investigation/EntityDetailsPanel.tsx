import { useState } from 'react'
import {
  Paper,
  Typography,
  Box,
  Chip,
  Stack,
  TextField,
  Button,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import SecurityIcon from '@mui/icons-material/Security'
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import DnsIcon from '@mui/icons-material/Dns'
import EmailIcon from '@mui/icons-material/Email'
import InfoIcon from '@mui/icons-material/Info'
import EditIcon from '@mui/icons-material/Edit'
import SaveIcon from '@mui/icons-material/Save'
import CancelIcon from '@mui/icons-material/Cancel'
import { useTranslation } from 'react-i18next'

interface EntityDetailsPanelProps {
  nodeId: string | null
  nodeType: string | null
  nodeValue: string | null
  nodeData?: Record<string, unknown>
  investigationId?: string | null
  onSaveNotesTags?: (cyId: string, notes: string, tags: string[]) => Promise<void>
}

const HIDDEN_KEYS = new Set([
  'id',
  'investigation_id',
  'scan_id',
  'last_scan',
  'element_id',
  'label',
  'type',
])

const LABEL_KEY_MAP: Record<string, string> = {
  name: 'investigations.name',
  address: 'investigations.ipAddress',
  host: 'results.host',
  port: 'investigations.types.port',
  ip: 'investigations.types.ip',
  number: 'investigations.types.asn',
  registrar: 'results.registrar',
  creation_date: 'results.created',
  expiration_date: 'results.expires',
  name_servers: 'results.nameServers',
  emails: 'results.contactEmails',
  status: 'common.status',
  issuer: 'investigations.issuer',
  is_expired: 'results.expired',
  service: 'investigations.service',
  source: 'investigations.source',
  org: 'investigations.organization',
  notes: 'investigations.notes',
  tags: 'results.tags',
}

function formatValue(value: unknown, yes: string, no: string): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? yes : no
  if (Array.isArray(value)) return value.join(', ') || '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function getIcon(key: string) {
  if (['registrar', 'creation_date', 'expiration_date', 'status'].includes(key))
    return <CalendarMonthIcon sx={{ fontSize: 14, opacity: 0.7 }} />
  if (['name_servers', 'address', 'host', 'ip'].includes(key))
    return <DnsIcon sx={{ fontSize: 14, opacity: 0.7 }} />
  if (key === 'emails') return <EmailIcon sx={{ fontSize: 14, opacity: 0.7 }} />
  if (['issuer', 'is_expired'].includes(key))
    return <SecurityIcon sx={{ fontSize: 14, opacity: 0.7 }} />
  return <InfoIcon sx={{ fontSize: 14, opacity: 0.7 }} />
}

const EntityDetailsPanel = ({
  nodeId,
  nodeType,
  nodeValue,
  nodeData,
  investigationId,
  onSaveNotesTags,
}: EntityDetailsPanelProps) => {
  const { t } = useTranslation()
  const [editingNotesTags, setEditingNotesTags] = useState(false)
  const [notesEdit, setNotesEdit] = useState('')
  const [tagsEdit, setTagsEdit] = useState('')
  const [saving, setSaving] = useState(false)

  if (!nodeId) {
    return (
      <Paper sx={{ p: 2, height: '100%' }}>
        <Typography color="text.secondary">
          {t('investigations.clickNodeDetails')}
        </Typography>
      </Paper>
    )
  }

  const notes = (nodeData?.notes as string) ?? ''
  const tags = Array.isArray(nodeData?.tags) ? (nodeData.tags as string[]) : []
  const canEdit = Boolean(investigationId && onSaveNotesTags)

  const displayProps =
    nodeData &&
    Object.entries(nodeData)
      .filter(
        ([k, v]) =>
          !HIDDEN_KEYS.has(k) &&
          v !== null &&
          v !== undefined &&
          k !== 'notes' &&
          k !== 'tags'
      )
      .sort(([a], [b]) => {
        const order = [
          'name',
          'address',
          'host',
          'registrar',
          'creation_date',
          'expiration_date',
          'issuer',
          'is_expired',
          'port',
          'service',
          'org',
        ]
        const ai = order.indexOf(a)
        const bi = order.indexOf(b)
        if (ai >= 0 && bi >= 0) return ai - bi
        if (ai >= 0) return -1
        if (bi >= 0) return 1
        return a.localeCompare(b)
      })

  const handleStartEdit = () => {
    setNotesEdit(notes)
    setTagsEdit(tags.join(', '))
    setEditingNotesTags(true)
  }

  const handleCancelEdit = () => {
    setEditingNotesTags(false)
  }

  const handleSave = async () => {
    if (!onSaveNotesTags || !investigationId) return
    setSaving(true)
    try {
      const tagsArray = tagsEdit
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
      await onSaveNotesTags(nodeId, notesEdit, tagsArray)
      setEditingNotesTags(false)
    } finally {
      setSaving(false)
    }
  }

  const rawJson = nodeData ? JSON.stringify(nodeData, null, 2) : '{}'

  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      <Typography variant="subtitle2" color="text.secondary">
        {t('investigations.entity')}
      </Typography>
      <Typography variant="h6" sx={{ mt: 0.5 }}>
        {nodeValue || nodeId}
      </Typography>
      <Chip
        label={nodeType || '—'}
        size="small"
        sx={{ mt: 1 }}
        variant="outlined"
      />

      <Accordion defaultExpanded sx={{ boxShadow: 'none', '&::before': { display: 'none' }, mt: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle2" color="text.secondary">
            {t('investigations.notesAndTags')}
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
      {editingNotesTags ? (
        <Stack spacing={1.5}>
          <TextField
            size="small"
            multiline
            rows={3}
            label={t('investigations.notes')}
            value={notesEdit}
            onChange={(e) => setNotesEdit(e.target.value)}
            fullWidth
          />
          <TextField
            size="small"
            label={t('investigations.tagsCommaSeparated')}
            value={tagsEdit}
            onChange={(e) => setTagsEdit(e.target.value)}
            placeholder={t('investigations.tagsPlaceholder')}
            fullWidth
          />
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              size="small"
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={saving}
            >
              {t('common.save')}
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<CancelIcon />}
              onClick={handleCancelEdit}
              disabled={saving}
            >
              {t('common.cancel')}
            </Button>
          </Box>
        </Stack>
      ) : (
        <Box>
          {notes ? (
            <Typography variant="body2" sx={{ mb: 1, wordBreak: 'break-word' }}>
              {notes}
            </Typography>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {t('investigations.noNotes')}
            </Typography>
          )}
          {tags.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
              {tags.map((t) => (
                <Chip key={t} label={t} size="small" variant="outlined" />
              ))}
            </Box>
          )}
          {canEdit && (
            <IconButton size="small" onClick={handleStartEdit} title={t('investigations.editNotesAndTags')}>
              <EditIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
      )}
        </AccordionDetails>
      </Accordion>

      {displayProps && displayProps.length > 0 && (
        <Accordion defaultExpanded sx={{ boxShadow: 'none', '&::before': { display: 'none' } }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2" color="text.secondary">
              {t('investigations.properties')}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={1.5}>
              {displayProps.map(([key, value]) => (
                <Box key={key}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                  >
                    {getIcon(key)}
                    {LABEL_KEY_MAP[key] ? t(LABEL_KEY_MAP[key] as never) : key.replace(/_/g, ' ')}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.25, wordBreak: 'break-word' }}>
                    {formatValue(value, t('common.yes'), t('common.no'))}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </AccordionDetails>
        </Accordion>
      )}

      <Accordion defaultExpanded={false} sx={{ boxShadow: 'none', '&::before': { display: 'none' } }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle2" color="text.secondary">
            Raw JSON
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box
            component="pre"
            sx={{
              fontSize: 11,
              fontFamily: 'monospace',
              p: 1,
              bgcolor: 'grey.50',
              borderRadius: 1,
              overflow: 'auto',
              maxHeight: 280,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {rawJson}
          </Box>
        </AccordionDetails>
      </Accordion>
    </Paper>
  )
}

export default EntityDetailsPanel
