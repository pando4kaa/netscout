import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

interface AddEntityDialogProps {
  open: boolean
  onClose: () => void
  onAdd: (entityType: string, entityValue: string) => Promise<void>
}

const AddEntityDialog = ({ open, onClose, onAdd }: AddEntityDialogProps) => {
  const { t } = useTranslation()
  const [entityType, setEntityType] = useState('domain')
  const [entityValue, setEntityValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAdd = async () => {
    const value = entityValue.trim()
    if (!value) return
    setError(null)
    setLoading(true)
    try {
      await onAdd(entityType, value)
      setEntityValue('')
      onClose()
    } catch (err) {
      setError(t('investigations.failedToAddEntity'))
    } finally {
      setLoading(false)
    }
  }

  const entityTypes = [
    { value: 'domain', label: t('common.domain') },
    { value: 'subdomain', label: t('results.subdomain') },
    { value: 'ip', label: t('investigations.ipAddress') },
  ]

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t('investigations.addEntity')}</DialogTitle>
      <DialogContent>
        <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
          <InputLabel>{t('investigations.entityType')}</InputLabel>
          <Select
            value={entityType}
            label={t('investigations.entityType')}
            onChange={(e) => setEntityType(e.target.value)}
          >
            {entityTypes.map((type) => (
              <MenuItem key={type.value} value={type.value}>
                {type.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          fullWidth
          label={entityType === 'ip' ? t('investigations.ipAddress') : t('investigations.domainOrSubdomain')}
          value={entityValue}
          onChange={(e) => setEntityValue(e.target.value)}
          placeholder={entityType === 'ip' ? '1.2.3.4' : 'example.com'}
          error={!!error}
          helperText={error}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} sx={{ textTransform: 'none' }}>
          {t('common.cancel')}
        </Button>
        <Button
          onClick={handleAdd}
          variant="contained"
          disabled={!entityValue.trim() || loading}
          sx={{ textTransform: 'none' }}
        >
          {loading ? t('investigations.adding') : t('common.add')}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default AddEntityDialog
