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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  IconButton,
  Tooltip,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'
import VisibilityIcon from '@mui/icons-material/Visibility'
import CompareArrowsIcon from '@mui/icons-material/CompareArrows'
import FilterListIcon from '@mui/icons-material/FilterList'
import { scanApi, HistoryFilters } from '../services/api'
import { useScanStore } from '../store/useScanStore'
import { useAuth } from '../contexts/AuthContext'
import { ScanResults } from '../types'
import CompareResultDialog, { CompareResultData } from '../components/history/CompareResultDialog'

interface HistoryItem {
  scan_id: string
  domain: string
  created_at: string | null
  total_subdomains?: number
  total_alerts?: number
  risk_score?: number
}

const HistoryPage = () => {
  const [scans, setScans] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<HistoryFilters>({ limit: 50 })
  const [filterDomain, setFilterDomain] = useState('')
  const [filterRiskMin, setFilterRiskMin] = useState<number | ''>('')
  const [filterRiskMax, setFilterRiskMax] = useState<number | ''>('')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')
  const [compareScan1, setCompareScan1] = useState('')
  const [compareScan2, setCompareScan2] = useState('')
  const [compareOpen, setCompareOpen] = useState(false)
  const [compareResult, setCompareResult] = useState<CompareResultData | null>(null)
  const [compareError, setCompareError] = useState<string | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)
  const navigate = useNavigate()
  const { setCurrentScan } = useScanStore()
  const { isAuthenticated, isLoading: authLoading } = useAuth()

  const loadHistory = useCallback(async () => {
    setLoading(true)
    try {
      const data = await scanApi.getHistory(filters)
      setScans(data.scans || [])
    } catch (err) {
      setError('Failed to load history')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    if (authLoading) return
    loadHistory()
  }, [loadHistory, authLoading])

  const handleApplyFilters = () => {
    setFilters({
      ...filters,
      domain: filterDomain || undefined,
      risk_min: filterRiskMin !== '' ? Number(filterRiskMin) : undefined,
      risk_max: filterRiskMax !== '' ? Number(filterRiskMax) : undefined,
      date_from: filterDateFrom || undefined,
      date_to: filterDateTo || undefined,
    })
  }

  const handleCompare = async () => {
    if (!compareScan1 || !compareScan2 || compareScan1 === compareScan2) return
    setCompareLoading(true)
    setCompareResult(null)
    setCompareError(null)
    try {
      const data = await scanApi.compareScans(compareScan1, compareScan2)
      if (data.error) {
        setCompareError(data.error)
        setCompareResult(null)
      } else {
        setCompareResult(data.comparison)
        setCompareError(null)
      }
    } catch (err) {
      console.error(err)
      setCompareResult(null)
      setCompareError('Failed to compare scans')
    } finally {
      setCompareLoading(false)
    }
  }

  const compareScan1Domain = compareScan1 ? scans.find((s) => s.scan_id === compareScan1)?.domain : ''
  const scansForScan2 = compareScan1Domain
    ? scans.filter((s) => s.domain === compareScan1Domain && s.scan_id !== compareScan1)
    : scans

  const handleSetCompareScan1 = (scanId: string) => {
    setCompareScan1(scanId)
    setCompareScan2('')
  }

  const handleSetCompareScan2 = (scanId: string) => {
    setCompareScan2(scanId)
  }

  const handleOpen = async (scanId: string) => {
    try {
      const results = await scanApi.getResults(scanId)
      if (results) {
        const scanResults: ScanResults = {
          ...results,
          scan_id: scanId,
        }
        setCurrentScan(scanResults)
        navigate('/scan')
      }
    } catch (err) {
      console.error(err)
    }
  }

  const formatDate = (iso: string | null) => {
    if (!iso) return '-'
    try {
      return new Date(iso).toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    } catch {
      return iso
    }
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
        <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
          Scan History
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterListIcon /> Filters
          </Typography>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={2}>
              <TextField
                size="small"
                label="Domain"
                value={filterDomain}
                onChange={(e) => setFilterDomain(e.target.value)}
                fullWidth
                placeholder="example.com"
              />
            </Grid>
            <Grid item xs={6} sm={1.5}>
              <TextField
                size="small"
                type="number"
                label="Risk min"
                value={filterRiskMin}
                onChange={(e) => setFilterRiskMin(e.target.value === '' ? '' : Number(e.target.value))}
                fullWidth
              />
            </Grid>
            <Grid item xs={6} sm={1.5}>
              <TextField
                size="small"
                type="number"
                label="Risk max"
                value={filterRiskMax}
                onChange={(e) => setFilterRiskMax(e.target.value === '' ? '' : Number(e.target.value))}
                fullWidth
              />
            </Grid>
            <Grid item xs={6} sm={2}>
              <TextField
                size="small"
                type="date"
                label="From date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={6} sm={2}>
              <TextField
                size="small"
                type="date"
                label="To date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={2}>
              <Button variant="contained" onClick={handleApplyFilters} fullWidth>
                Apply
              </Button>
            </Grid>
          </Grid>
        </Paper>

        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <CompareArrowsIcon /> Compare scans
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Scan 1</InputLabel>
              <Select
                value={compareScan1}
                onChange={(e) => {
                  setCompareScan1(e.target.value)
                  setCompareScan2('')
                }}
                label="Scan 1"
              >
                <MenuItem value="">—</MenuItem>
                {scans.map((s) => (
                  <MenuItem key={s.scan_id} value={s.scan_id}>
                    {s.domain} ({formatDate(s.created_at)})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Scan 2</InputLabel>
              <Select
                value={compareScan2}
                onChange={(e) => setCompareScan2(e.target.value)}
                label="Scan 2"
                disabled={!compareScan1}
              >
                <MenuItem value="">—</MenuItem>
                {scansForScan2.map((s) => (
                  <MenuItem key={s.scan_id} value={s.scan_id}>
                    {s.domain} ({formatDate(s.created_at)})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="outlined"
              startIcon={<CompareArrowsIcon />}
              onClick={() => {
                setCompareOpen(true)
                setCompareResult(null)
                setCompareError(null)
                handleCompare()
              }}
              disabled={!compareScan1 || !compareScan2 || compareScan1 === compareScan2}
            >
              Compare
            </Button>
            {(compareScan1 || compareScan2) && (
              <Button
                variant="text"
                size="small"
                onClick={() => {
                  setCompareScan1('')
                  setCompareScan2('')
                }}
              >
                Reset
              </Button>
            )}
          </Box>
        </Paper>

        <CompareResultDialog
          open={compareOpen}
          onClose={() => setCompareOpen(false)}
          result={compareResult}
          error={compareError}
          loading={compareLoading}
        />

        {scans.length > 0 ? (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Domain</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Subdomains</TableCell>
                  <TableCell align="right">Alerts</TableCell>
                  <TableCell align="right">Risk</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {scans.map((row) => {
                  const isSameDomainAsScan1 = !compareScan1 || row.domain === compareScan1Domain
                  const isScan1 = row.scan_id === compareScan1
                  const isScan2 = row.scan_id === compareScan2
                  const canSetAsScan2 = compareScan1 && isSameDomainAsScan1 && !isScan1
                  return (
                    <TableRow
                      key={row.scan_id}
                      hover={isSameDomainAsScan1}
                      sx={{
                        opacity: isSameDomainAsScan1 ? 1 : 0.5,
                      }}
                    >
                      <TableCell sx={{ fontFamily: 'monospace' }}>{row.domain}</TableCell>
                      <TableCell>{formatDate(row.created_at)}</TableCell>
                      <TableCell align="right">{row.total_subdomains ?? '-'}</TableCell>
                      <TableCell align="right">{row.total_alerts ?? '-'}</TableCell>
                      <TableCell align="right">{row.risk_score ?? '-'}</TableCell>
                      <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                        <Button
                          size="small"
                          startIcon={<VisibilityIcon />}
                          onClick={() => handleOpen(row.scan_id)}
                          sx={{ mr: 0.5 }}
                        >
                          Open
                        </Button>
                        <Tooltip
                          title={
                            !compareScan1
                              ? 'Set as Scan 1 for comparison'
                              : isScan1
                                ? 'Scan 1'
                                : canSetAsScan2
                                  ? 'Set as Scan 2'
                                  : 'Compare only same domain'
                          }
                        >
                          <span>
                            <IconButton
                              size="small"
                              color={isScan1 ? 'primary' : isScan2 ? 'secondary' : 'default'}
                              onClick={() => {
                                if (!compareScan1) {
                                  handleSetCompareScan1(row.scan_id)
                                } else if (canSetAsScan2) {
                                  handleSetCompareScan2(row.scan_id)
                                }
                              }}
                              disabled={!isSameDomainAsScan1 || isScan1}
                            >
                              <CompareArrowsIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Box
            sx={{
              textAlign: 'center',
              py: 8,
              bgcolor: 'background.paper',
              borderRadius: 2,
              border: '1px dashed',
              borderColor: 'divider',
            }}
          >
            <Typography variant="body1" color="text.secondary" sx={{ fontSize: '1.1rem' }}>
              {isAuthenticated
                ? 'No scan history available'
                : 'Sign in to save scans and view your scan history'}
            </Typography>
          </Box>
        )}
      </Box>
    </Container>
  )
}

export default HistoryPage
