import { useState, useEffect } from 'react'
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
  DialogActions,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import ScheduleIcon from '@mui/icons-material/Schedule'
import { Link } from 'react-router-dom'
import { scanApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

interface ScheduleItem {
  id: number
  domain: string
  interval_hours: number
  enabled: boolean
  last_run_at: string | null
  created_at: string | null
}

const SchedulesPage = () => {
  const { isAuthenticated } = useAuth()
  const [schedules, setSchedules] = useState<ScheduleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newDomain, setNewDomain] = useState('')
  const [newInterval, setNewInterval] = useState(24)

  const loadSchedules = async () => {
    try {
      const data = await scanApi.getSchedules()
      setSchedules(data.schedules || [])
    } catch (err) {
      setError('Failed to load schedules')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      loadSchedules()
    } else {
      setLoading(false)
    }
  }, [isAuthenticated])

  const handleAdd = async () => {
    if (!newDomain.trim()) return
    try {
      await scanApi.createSchedule(newDomain.trim(), newInterval)
      setDialogOpen(false)
      setNewDomain('')
      setNewInterval(24)
      loadSchedules()
    } catch (err) {
      setError('Failed to create schedule')
      console.error(err)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await scanApi.deleteSchedule(id)
      loadSchedules()
    } catch (err) {
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
      return new Date(iso).toLocaleString('uk-UA', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
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
            Sign in to schedule scans
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Create an account or sign in to set up recurring domain scans.
          </Typography>
          <Button component={Link} to="/login" variant="contained" sx={{ mr: 1 }}>
            Sign in
          </Button>
          <Button component={Link} to="/register" variant="outlined">
            Register
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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Scheduled Scans
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setDialogOpen(true)}
          >
            Add schedule
          </Button>
        </Box>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {schedules.length > 0 ? (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Domain</TableCell>
                  <TableCell>Interval</TableCell>
                  <TableCell>Last run</TableCell>
                  <TableCell>Enabled</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {schedules.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell sx={{ fontFamily: 'monospace' }}>{row.domain}</TableCell>
                    <TableCell>Every {row.interval_hours} h</TableCell>
                    <TableCell>{formatDate(row.last_run_at)}</TableCell>
                    <TableCell>
                      <Switch
                        checked={row.enabled}
                        onChange={(e) => handleToggle(row.id, e.target.checked)}
                        color="primary"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => handleDelete(row.id)} color="error">
                        <DeleteIcon />
                      </IconButton>
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
              No scheduled scans. Add a domain to run scans automatically.
            </Typography>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)} sx={{ mt: 2 }}>
              Add schedule
            </Button>
          </Paper>
        )}
      </Box>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Add scheduled scan</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Domain"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            fullWidth
            placeholder="example.com"
          />
          <TextField
            margin="dense"
            label="Interval (hours)"
            type="number"
            value={newInterval}
            onChange={(e) => setNewInterval(Math.max(1, parseInt(e.target.value) || 24))}
            fullWidth
            inputProps={{ min: 1, max: 168 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAdd} variant="contained" disabled={!newDomain.trim()}>
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default SchedulesPage
