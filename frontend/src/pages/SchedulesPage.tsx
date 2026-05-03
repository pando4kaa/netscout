import { useState, useEffect, useCallback } from 'react'
import {
  Container,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  CircularProgress,
  Alert,
  TextField,
  Switch,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Stack,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import ScheduleIcon from '@mui/icons-material/Schedule'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { scanApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useLocaleFormatters } from '../i18n/format'

interface ScheduleItem {
  id: number
  domain: string
  interval_hours: number
  enabled: boolean
  last_run_at: string | null
  created_at: string | null
}

const SchedulesPage = () => {
  const { t } = useTranslation()
  const { formatDateTime } = useLocaleFormatters()
  const { isAuthenticated } = useAuth()
  const [schedules, setSchedules] = useState<ScheduleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scheduleFormOpen, setScheduleFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [newDomain, setNewDomain] = useState('')
  const [newInterval, setNewInterval] = useState(24)
  const [deleteTarget, setDeleteTarget] = useState<ScheduleItem | null>(null)

  const loadSchedules = useCallback(async () => {
    try {
      const data = await scanApi.getSchedules()
      setSchedules(data.schedules || [])
    } catch (err) {
      setError(t('errors.failedToLoadSchedules'))
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    if (isAuthenticated) {
      loadSchedules()
    } else {
      setLoading(false)
    }
  }, [isAuthenticated, loadSchedules])

  const openAddDialog = () => {
    setEditingId(null)
    setNewDomain('')
    setNewInterval(24)
    setScheduleFormOpen(true)
  }

  const openEditDialog = (row: ScheduleItem) => {
    setEditingId(row.id)
    setNewDomain(row.domain)
    setNewInterval(row.interval_hours)
    setScheduleFormOpen(true)
  }

  const closeFormDialog = () => {
    setScheduleFormOpen(false)
    setEditingId(null)
  }

  const handleSaveSchedule = async () => {
    if (!newDomain.trim()) return
    try {
      if (editingId !== null) {
        await scanApi.updateSchedule(editingId, {
          domain: newDomain.trim(),
          interval_hours: newInterval,
        })
      } else {
        await scanApi.createSchedule(newDomain.trim(), newInterval)
      }
      closeFormDialog()
      setNewDomain('')
      setNewInterval(24)
      loadSchedules()
    } catch (err) {
      setError(
        editingId !== null ? t('errors.failedToUpdateSchedule') : t('errors.failedToCreateSchedule')
      )
      console.error(err)
    }
  }

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return
    try {
      await scanApi.deleteSchedule(deleteTarget.id)
      setDeleteTarget(null)
      loadSchedules()
    } catch (err) {
      setError(t('errors.failedToDeleteSchedule'))
      console.error(err)
    }
  }

  const handleToggle = async (id: number, enabled: boolean) => {
    try {
      await scanApi.toggleSchedule(id, enabled)
      loadSchedules()
    } catch (err) {
      console.error(err)
    }
  }

  const formatDate = (iso: string | null) => {
    if (!iso) return '-'
    try {
      return formatDateTime(iso)
    } catch {
      return iso
    }
  }

  if (!isAuthenticated) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 6, textAlign: 'center' }}>
          <ScheduleIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            {t('schedules.signInTitle')}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            {t('schedules.signInBody')}
          </Typography>
          <Button component={Link} to="/login" variant="contained" sx={{ mr: 1 }}>
            {t('navigation.signIn')}
          </Button>
          <Button component={Link} to="/register" variant="outlined">
            {t('navigation.register')}
          </Button>
        </Box>
      </Container>
    )
  }

  if (loading) {
    return (
      <Container maxWidth="lg">
        <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
          <CircularProgress />
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 3 }}>
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: { xs: 'stretch', sm: 'center' },
            gap: 2,
            mb: 3,
          }}
        >
          <Typography
            variant="h4"
            component="h1"
            sx={{ minWidth: 0, pr: { sm: 2 }, typography: { xs: 'h5', sm: 'h4' } }}
          >
            {t('schedules.title')}
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openAddDialog}
            sx={{
              alignSelf: { xs: 'stretch', sm: 'auto' },
              flexShrink: 0,
              whiteSpace: { sm: 'nowrap' },
            }}
          >
            {t('schedules.addSchedule')}
          </Button>
        </Box>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {schedules.length > 0 ? (
          <TableContainer component={Paper}>
            <Table size="small" sx={{ '& td, & th': { verticalAlign: 'middle' } }}>
              <TableHead>
                <TableRow>
                  <TableCell>{t('common.domain')}</TableCell>
                  <TableCell>{t('common.interval')}</TableCell>
                  <TableCell>{t('common.lastRun')}</TableCell>
                  <TableCell>{t('common.enabled')}</TableCell>
                  <TableCell align="right">{t('common.actions')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {schedules.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell sx={{ fontFamily: 'monospace' }}>{row.domain}</TableCell>
                    <TableCell>{t('common.everyHours', { count: row.interval_hours })}</TableCell>
                    <TableCell>{formatDate(row.last_run_at)}</TableCell>
                    <TableCell>
                      <Switch
                        checked={row.enabled}
                        onChange={(e) => handleToggle(row.id, e.target.checked)}
                        color="primary"
                      />
                    </TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end" alignItems="center">
                        <IconButton
                          size="small"
                          onClick={() => openEditDialog(row)}
                          aria-label={t('schedules.editSchedule')}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => setDeleteTarget(row)}
                          color="error"
                          aria-label={t('common.delete')}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <ScheduleIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="body1" color="text.secondary" gutterBottom>
              {t('schedules.empty')}
            </Typography>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={openAddDialog} sx={{ mt: 2 }}>
              {t('schedules.addSchedule')}
            </Button>
          </Paper>
        )}
      </Box>

      <Dialog open={scheduleFormOpen} onClose={closeFormDialog} maxWidth="xs" fullWidth>
        <DialogTitle>
          {editingId !== null ? t('schedules.editScheduledScan') : t('schedules.addScheduledScan')}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus={editingId === null}
            margin="dense"
            label={t('common.domain')}
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            fullWidth
            placeholder="example.com"
          />
          <TextField
            margin="dense"
            label={t('schedules.intervalHours')}
            type="number"
            value={newInterval}
            onChange={(e) => setNewInterval(Math.max(1, parseInt(e.target.value, 10) || 24))}
            fullWidth
            inputProps={{ min: 1, max: 168 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeFormDialog}>{t('common.cancel')}</Button>
          <Button onClick={handleSaveSchedule} variant="contained" disabled={!newDomain.trim()}>
            {editingId !== null ? t('common.save') : t('common.add')}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle>{t('schedules.confirmDeleteTitle')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {deleteTarget
              ? t('schedules.confirmDeleteBody', { domain: deleteTarget.domain })
              : null}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>{t('common.cancel')}</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained">
            {t('common.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default SchedulesPage
