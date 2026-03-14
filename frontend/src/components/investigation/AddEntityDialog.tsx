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

const ENTITY_TYPES = [
  { value: 'domain', label: 'Domain' },
  { value: 'subdomain', label: 'Subdomain' },
  { value: 'ip', label: 'IP Address' },
]

interface AddEntityDialogProps {
  open: boolean
  onClose: () => void
  onAdd: (entityType: string, entityValue: string) => Promise<void>
}

const AddEntityDialog = ({ open, onClose, onAdd }: AddEntityDialogProps) => {
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
      setError('Failed to add entity')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Entity</DialogTitle>
      <DialogContent>
        <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
          <InputLabel>Entity Type</InputLabel>
          <Select
            value={entityType}
            label="Entity Type"
            onChange={(e) => setEntityType(e.target.value)}
          >
            {ENTITY_TYPES.map((t) => (
              <MenuItem key={t.value} value={t.value}>
                {t.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          fullWidth
          label={entityType === 'ip' ? 'IP Address' : 'Domain or Subdomain'}
          value={entityValue}
          onChange={(e) => setEntityValue(e.target.value)}
          placeholder={entityType === 'ip' ? '1.2.3.4' : 'example.com'}
          error={!!error}
          helperText={error}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} sx={{ textTransform: 'none' }}>
          Cancel
        </Button>
        <Button
          onClick={handleAdd}
          variant="contained"
          disabled={!entityValue.trim() || loading}
          sx={{ textTransform: 'none' }}
        >
          {loading ? 'Adding...' : 'Add'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default AddEntityDialog
