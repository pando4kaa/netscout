import { useState, useMemo } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TablePagination,
  InputAdornment,
  IconButton,
  Tooltip,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'

interface SubdomainsListProps {
  subdomains: string[]
  targetDomain: string
}

const SubdomainsList = ({ subdomains, targetDomain }: SubdomainsListProps) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(25)

  const filteredSubdomains = useMemo(() => {
    if (!searchQuery) return subdomains
    return subdomains.filter((sub) =>
      sub.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [subdomains, searchQuery])

  const paginatedSubdomains = useMemo(() => {
    const start = page * rowsPerPage
    return filteredSubdomains.slice(start, start + rowsPerPage)
  }, [filteredSubdomains, page, rowsPerPage])

  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage)
  }

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10))
    setPage(0)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const copyAllSubdomains = () => {
    navigator.clipboard.writeText(filteredSubdomains.join('\n'))
  }

  if (!subdomains || subdomains.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary">No subdomains found</Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Header with search and stats */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6">
                Discovered Subdomains
              </Typography>
              <Chip label={`${subdomains.length} total`} color="primary" />
              {searchQuery && (
                <Chip label={`${filteredSubdomains.length} filtered`} color="secondary" variant="outlined" />
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Copy all subdomains">
                <Chip
                  label="Copy All"
                  onClick={copyAllSubdomains}
                  icon={<ContentCopyIcon />}
                  clickable
                  variant="outlined"
                />
              </Tooltip>
            </Box>
          </Box>

          <TextField
            fullWidth
            size="small"
            placeholder="Search subdomains..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              setPage(0)
            }}
            sx={{ mt: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
        </CardContent>
      </Card>

      {/* Subdomains Table */}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>Subdomain</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedSubdomains.map((subdomain, index) => (
              <TableRow key={subdomain} hover>
                <TableCell sx={{ color: 'text.secondary', width: 60 }}>
                  {page * rowsPerPage + index + 1}
                </TableCell>
                <TableCell>
                  <Typography
                    variant="body2"
                    sx={{ fontFamily: 'monospace' }}
                  >
                    {subdomain}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Copy">
                    <IconButton
                      size="small"
                      onClick={() => copyToClipboard(subdomain)}
                    >
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Open in new tab">
                    <IconButton
                      size="small"
                      component="a"
                      href={`https://${subdomain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <OpenInNewIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={filteredSubdomains.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>
    </Box>
  )
}

export default SubdomainsList
