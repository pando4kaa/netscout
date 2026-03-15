import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { ScanResults } from '../../types'
import HelpTooltip from '../common/HelpTooltip'

interface TechStackPanelProps {
  techStack: ScanResults['tech_stack']
}

const TechStackPanel = ({ techStack }: TechStackPanelProps) => {
  if (!techStack || Object.keys(techStack).length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary">No technology data available</Typography>
        </CardContent>
      </Card>
    )
  }

  const entries = Object.entries(techStack)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="h6">Technology Stack</Typography>
        <HelpTooltip topic="tech_stack" />
      </Box>
      {entries.map(([url, data]: [string, any]) => (
        <Accordion key={url}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="subtitle1" sx={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                {url.replace(/^https?:\/\//, '')}
              </Typography>
              {data?.server && (
                <Chip label={data.server} size="small" color="primary" />
              )}
              {data?.error && (
                <Chip label="Error" size="small" color="error" />
              )}
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            {data?.error ? (
              <Typography color="error" variant="body2">{data.error}</Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {data?.technologies?.length > 0 && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">Technologies</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 0.5 }}>
                      {data.technologies.map((t: string, i: number) => (
                        <Chip key={i} label={t} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </Box>
                )}
                {data?.server && (
                  <Typography variant="body2"><strong>Server:</strong> {data.server}</Typography>
                )}
                {data?.x_powered_by && (
                  <Typography variant="body2"><strong>X-Powered-By:</strong> {data.x_powered_by}</Typography>
                )}
                {data?.favicon_hash != null && (
                  <Typography variant="body2"><strong>Favicon hash:</strong> {data.favicon_hash}</Typography>
                )}
                {data?.meta_generator && (
                  <Typography variant="body2"><strong>Meta generator:</strong> {data.meta_generator}</Typography>
                )}
                {data?.meta_cms && (
                  <Typography variant="body2"><strong>CMS:</strong> {data.meta_cms}</Typography>
                )}
                {data?.robots_txt && (
                  <Box>
                    <Typography variant="body2"><strong>robots.txt:</strong></Typography>
                    <Paper variant="outlined" sx={{ p: 1, mt: 0.5, maxHeight: 120, overflow: 'auto' }}>
                      <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                        {data.robots_txt.slice(0, 500)}{data.robots_txt.length > 500 ? '...' : ''}
                      </Typography>
                    </Paper>
                  </Box>
                )}
                {data?.security_txt && (
                  <Box>
                    <Typography variant="body2"><strong>security.txt:</strong></Typography>
                    <Paper variant="outlined" sx={{ p: 1, mt: 0.5, maxHeight: 120, overflow: 'auto' }}>
                      <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                        {data.security_txt.slice(0, 500)}{data.security_txt.length > 500 ? '...' : ''}
                      </Typography>
                    </Paper>
                  </Box>
                )}
                {data?.security_headers && (
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>Security Headers</Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography variant="caption">
                        <strong>HSTS:</strong> {data.security_headers.strict_transport_security ? (
                          <Chip label="Present" size="small" color="success" sx={{ ml: 0.5, height: 18 }} />
                        ) : (
                          <Chip label="Absent" size="small" color="warning" sx={{ ml: 0.5, height: 18 }} />
                        )}
                        {data.security_headers.strict_transport_security && (
                          <Typography component="span" variant="caption" sx={{ fontFamily: 'monospace', ml: 0.5 }}>
                            {String(data.security_headers.strict_transport_security).slice(0, 60)}...
                          </Typography>
                        )}
                      </Typography>
                      <Typography variant="caption">
                        <strong>X-Frame-Options:</strong> {data.security_headers.x_frame_options ? (
                          <Chip label={data.security_headers.x_frame_options} size="small" color="success" sx={{ ml: 0.5, height: 18 }} />
                        ) : (
                          <Chip label="Absent" size="small" color="warning" sx={{ ml: 0.5, height: 18 }} />
                        )}
                      </Typography>
                      <Typography variant="caption">
                        <strong>Content-Security-Policy:</strong> {data.security_headers.content_security_policy ? (
                          <Chip label="Present" size="small" color="success" sx={{ ml: 0.5, height: 18 }} />
                        ) : (
                          <Chip label="Absent" size="small" color="warning" sx={{ ml: 0.5, height: 18 }} />
                        )}
                      </Typography>
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  )
}

export default TechStackPanel
