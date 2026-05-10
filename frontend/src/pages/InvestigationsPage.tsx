import { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  CardActions,
  Grid,
  IconButton,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import SearchIcon from '@mui/icons-material/Search'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { investigationsApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { Investigation } from '../types'
import { useLocaleFormatters } from '../i18n/format'

const InvestigationsPage = () => {
  const { t } = useTranslation()
  const { formatDateTime } = useLocaleFormatters()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [investigations, setInvestigations] = useState<Investigation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [renameId, setRenameId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  useEffect(() => {
    if (authLoading) return
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    const load = async () => {
      try {
        const data = await investigationsApi.list()
        setInvestigations(data.investigations || [])
      } catch (err) {
        setError(t('investigations.failedToLoad'))
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [authLoading, isAuthenticated, navigate, t])

  const handleCreate = async () => {
    try {
      const inv = await investigationsApi.create(t('investigations.newInvestigation'))
      navigate(`/investigations/${inv.id}`)
    } catch (err) {
      setError(t('investigations.failedToCreate'))
      console.error(err)
    }
  }

  const handleDelete = async (invId: string) => {
    if (!window.confirm(t('investigations.deleteConfirm'))) return
    try {
      await investigationsApi.delete(invId)
      setInvestigations((prev) => prev.filter((i) => i.id !== invId))
    } catch (err) {
      setError(t('investigations.failedToDelete'))
    }
  }

  const openRename = (inv: Investigation) => {
    setRenameId(inv.id)
    setRenameValue(inv.name)
  }

  const handleRename = async () => {
    if (!renameId || !renameValue.trim()) return
    try {
      await investigationsApi.update(renameId, renameValue.trim())
      setInvestigations((prev) =>
        prev.map((i) => (i.id === renameId ? { ...i, name: renameValue.trim() } : i))
      )
      setRenameId(null)
      setRenameValue('')
    } catch (err) {
      setError(t('investigations.failedToRename'))
    }
  }

  if (authLoading) {
    return (
      <Container maxWidth="lg" sx={{ py: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    )
  }

  if (!isAuthenticated) return null

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>
          {t('investigations.title')}
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreate}
          sx={{ textTransform: 'none' }}
        >
          {t('investigations.newInvestigation')}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : investigations.length === 0 ? (
        <Card sx={{ textAlign: 'center', py: 6 }}>
          <CardContent>
            <SearchIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              {t('investigations.emptyTitle')}
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              {t('investigations.emptyBody')}
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCreate}
              sx={{ textTransform: 'none' }}
            >
              {t('investigations.createFirst')}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {investigations.map((inv) => (
            <Grid item xs={12} sm={6} md={4} key={inv.id}>
              <Card>
                <CardContent>
                  <Typography variant="h6">{inv.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t('investigations.updated', { date: inv.updated_at ? formatDateTime(inv.updated_at, { dateStyle: 'medium' }) : '—' })}
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button
                    component={Link}
                    to={`/investigations/${inv.id}`}
                    size="small"
                    sx={{ textTransform: 'none' }}
                  >
                    {t('common.open')}
                  </Button>
                  <IconButton size="small" onClick={() => openRename(inv)}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" color="error" onClick={() => handleDelete(inv.id)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={Boolean(renameId)} onClose={() => setRenameId(null)}>
        <DialogTitle>{t('investigations.rename')}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t('investigations.name')}
            fullWidth
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameId(null)}>{t('common.cancel')}</Button>
          <Button onClick={handleRename} variant="contained">{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default InvestigationsPage
