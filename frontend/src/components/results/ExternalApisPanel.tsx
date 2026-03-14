import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Link,
  Tooltip,
} from '@mui/material'
import ApiIcon from '@mui/icons-material/Api'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import WarningIcon from '@mui/icons-material/Warning'
import ErrorIcon from '@mui/icons-material/Error'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'

interface ExternalApisPanelProps {
  data?: {
    virustotal?: { last_analysis_stats?: Record<string, number>; reputation?: number }
    shodan?: Record<string, { ports?: number[]; tags?: string[]; vulns?: string[] }>
    censys?: { total?: number; hosts?: Array<{ ip?: string; names?: string[] }> }
    alienvault_otx?: { pulse_count?: number; alexa_rank?: string; alexa_url?: string; whois?: string; whois_url?: string; validation?: unknown[] }
    urlscan?: {
      total?: number
      unique_count?: number
      urls?: Array<{ url: string; scan_count: number }>
      results?: Array<{ url?: string; screenshot?: string }>
    }
    threatcrowd?: { votes?: number; subdomains?: string[]; resolutions?: Array<{ ip_address?: string }> }
    bgpview?: { ips?: Record<string, { asn?: number; asn_name?: string; prefix?: string }> }
    abuseipdb?: { ips?: Record<string, { abuse_score?: number; total_reports?: number; isp?: string; country_code?: string }> }
    securitytrails?: {
      domain?: string
      subdomain_count?: number
      tags?: string[]
      current_dns?: {
        a?: { first_seen?: string; values?: Array<{ ip?: string; ip_organization?: string }> }
        mx?: { first_seen?: string; values?: Array<{ hostname?: string; priority?: number; hostname_organization?: string }> }
        ns?: { first_seen?: string; values?: Array<{ nameserver?: string; nameserver_organization?: string }> }
        txt?: { first_seen?: string; values?: Array<{ value?: string }> }
      }
    }
    phishtank?: { url?: string; in_database?: boolean; valid?: boolean; verified?: string; phish_id?: string; phish_detail_page?: string }
    zoomeye?: { domain?: string; total?: number; hosts?: Array<{ ip?: string; port?: number; country?: string; asn?: string; app?: string }> }
    criminalip?: { domain?: string; risk_score?: number; is_safe?: boolean; data?: Record<string, unknown> }
    pulsedive?: { domain?: string; risk?: string; risk_recommendation?: string; threats?: string[]; feeds?: string[]; properties?: Record<string, unknown> }
    wayback?: { domain?: string; first_snapshot_timestamp?: string; first_snapshot_url?: string; original_url?: string; error?: string }
    ssllabs?: { domain?: string; grade?: string; weak_protocols?: string[]; has_weak_protocols?: boolean; error?: string }
  }
}

function getVirusTotalVerdict(stats: Record<string, number>): { label: string; color: 'success' | 'warning' | 'error'; icon: React.ReactNode } {
  const malicious = stats?.malicious ?? 0
  const suspicious = stats?.suspicious ?? 0
  const harmless = stats?.harmless ?? 0
  const undetected = stats?.undetected ?? 0
  const total = malicious + suspicious + harmless + undetected
  if (malicious > 0) return { label: 'Malicious', color: 'error', icon: <ErrorIcon fontSize="small" /> }
  if (suspicious > 0) return { label: 'Suspicious', color: 'warning', icon: <WarningIcon fontSize="small" /> }
  if (harmless > 0 || total === 0) return { label: 'Clean', color: 'success', icon: <CheckCircleIcon fontSize="small" /> }
  return { label: 'Unknown', color: 'warning', icon: <WarningIcon fontSize="small" /> }
}

const ExternalApisPanel = ({ data }: ExternalApisPanelProps) => {
  if (!data || Object.keys(data).length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary">
            No external API data. URLScan, BGPView, ThreatCrowd, PhishTank, Pulsedive, Web Archive, SSL Labs run automatically. Add VIRUSTOTAL_API_KEY, ALIENVAULT_OTX_API_KEY, ABUSEIPDB_API_KEY, SECURITYTRAILS_API_KEY, ZOOMEYE_API_KEY or CRIMINALIP_API_KEY to .env for more.
          </Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {data.virustotal && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> VirusTotal
            </Typography>
            {data.virustotal.last_analysis_stats && (
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                  {(() => {
                    const verdict = getVirusTotalVerdict(data.virustotal.last_analysis_stats)
                    return (
                      <Chip
                        icon={verdict.icon}
                        label={verdict.label}
                        color={verdict.color}
                        size="small"
                        sx={{ fontWeight: 600 }}
                      />
                    )
                  })()}
                  {data.virustotal.reputation != null && (
                    <Typography variant="body2" color="text.secondary">
                      Reputation score: {data.virustotal.reputation}
                    </Typography>
                  )}
                </Box>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Tooltip title="Engines that flagged as malicious">
                    <Chip label={`Malicious: ${data.virustotal.last_analysis_stats.malicious ?? 0}`} size="small" color="error" variant="outlined" />
                  </Tooltip>
                  <Tooltip title="Engines that flagged as suspicious">
                    <Chip label={`Suspicious: ${data.virustotal.last_analysis_stats.suspicious ?? 0}`} size="small" color="warning" variant="outlined" />
                  </Tooltip>
                  <Tooltip title="Engines that found no harmful content">
                    <Chip label={`Harmless: ${data.virustotal.last_analysis_stats.harmless ?? 0}`} size="small" color="success" variant="outlined" />
                  </Tooltip>
                  <Tooltip title="Engines with no detection">
                    <Chip label={`Undetected: ${data.virustotal.last_analysis_stats.undetected ?? 0}`} size="small" variant="outlined" />
                  </Tooltip>
                </Box>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {data.shodan && Object.keys(data.shodan).length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> Shodan
            </Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>IP</TableCell>
                    <TableCell>Ports</TableCell>
                    <TableCell>Tags</TableCell>
                    <TableCell>Vulns</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(data.shodan).map(([ip, info]) => (
                    <TableRow key={ip}>
                      <TableCell>{ip}</TableCell>
                      <TableCell>{(info.ports || []).join(', ')}</TableCell>
                      <TableCell>{(info.tags || []).join(', ')}</TableCell>
                      <TableCell>{(info.vulns || []).slice(0, 3).join(', ')}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {data.censys && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> Censys
            </Typography>
            <Typography variant="body2">Total hosts: {data.censys.total ?? 0}</Typography>
            {data.censys.hosts && data.censys.hosts.length > 0 && (
              <TableContainer component={Paper} variant="outlined" sx={{ mt: 1 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>IP</TableCell>
                      <TableCell>Names</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.censys.hosts.slice(0, 10).map((h, i) => (
                      <TableRow key={i}>
                        <TableCell>{h.ip}</TableCell>
                        <TableCell>{(h.names || []).join(', ')}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {data.alienvault_otx && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> AlienVault OTX
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography variant="body2">
                Threat pulses: {data.alienvault_otx.pulse_count ?? 0}
              </Typography>
              {(data.alienvault_otx.pulse_count ?? 0) > 0 && (
                <Tooltip title="Domain appears in threat intelligence reports. Review OTX for details.">
                  <Chip icon={<WarningIcon />} label="Review recommended" size="small" color="warning" variant="outlined" />
                </Tooltip>
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              {(() => {
                const alexaLink = data.alienvault_otx.alexa_url || (typeof data.alienvault_otx.alexa_rank === 'string' && data.alienvault_otx.alexa_rank.startsWith('http') ? data.alienvault_otx.alexa_rank : null)
                return alexaLink ? (
                  <Link href={alexaLink} target="_blank" rel="noopener noreferrer" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: '0.875rem' }}>
                    Alexa traffic rank <OpenInNewIcon sx={{ fontSize: 14 }} />
                  </Link>
                ) : null
              })()}
              {(() => {
                const whoisLink = data.alienvault_otx.whois_url || (typeof data.alienvault_otx.whois === 'string' && data.alienvault_otx.whois.startsWith('http') ? data.alienvault_otx.whois : null)
                return whoisLink ? (
                  <Link href={whoisLink} target="_blank" rel="noopener noreferrer" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: '0.875rem' }}>
                    WHOIS lookup <OpenInNewIcon sx={{ fontSize: 14 }} />
                  </Link>
                ) : null
              })()}
            </Box>
          </CardContent>
        </Card>
      )}

      {data.urlscan && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> URLScan.io
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {data.urlscan.total ?? 0} total scans
              {data.urlscan.unique_count != null && ` · ${data.urlscan.unique_count} unique URLs`}
              {!data.urlscan.unique_count && data.urlscan.results && ` · ${new Set(data.urlscan.results.map((r) => r.url).filter(Boolean)).size} unique URLs`}
            </Typography>
            {data.urlscan.urls && data.urlscan.urls.length > 0 ? (
              <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 200 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>URL</TableCell>
                      <TableCell align="right" sx={{ width: 90 }}>Scans</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.urlscan.urls.map((r, i) => (
                      <TableRow key={i}>
                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', wordBreak: 'break-all' }}>
                          <Link href={r.url} target="_blank" rel="noopener noreferrer" sx={{ fontSize: 'inherit' }}>
                            {r.url}
                          </Link>
                        </TableCell>
                        <TableCell align="right">{r.scan_count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : data.urlscan.results && data.urlscan.results.length > 0 ? (
              <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 0.5, maxHeight: 150, overflow: 'auto' }}>
                {[...new Set(data.urlscan.results.map((r) => r.url).filter(Boolean))].slice(0, 10).map((url, i) => (
                  <Link key={i} href={url} target="_blank" rel="noopener noreferrer" variant="body2" sx={{ wordBreak: 'break-all', fontSize: '0.75rem' }}>
                    {url}
                  </Link>
                ))}
              </Box>
            ) : null}
          </CardContent>
        </Card>
      )}

      {data.threatcrowd && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> ThreatCrowd
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Community votes: {data.threatcrowd.votes ?? 0} · Crowdsourced threat intel
            </Typography>
            {data.threatcrowd.subdomains && data.threatcrowd.subdomains.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" color="text.secondary">Related subdomains from threat reports:</Typography>
                <Box sx={{ mt: 0.5, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {data.threatcrowd.subdomains.slice(0, 8).map((s, i) => (
                    <Chip key={i} label={s} size="small" variant="outlined" sx={{ fontFamily: 'monospace' }} />
                  ))}
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {data.bgpview && data.bgpview.ips && Object.keys(data.bgpview.ips).length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> BGPView
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              ASN and BGP prefix for resolved IPs
            </Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>IP</TableCell>
                    <TableCell>ASN</TableCell>
                    <TableCell>Prefix</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(data.bgpview.ips).map(([ip, info]) => (
                    <TableRow key={ip}>
                      <TableCell>{ip}</TableCell>
                      <TableCell>{info.asn ?? '-'} {info.asn_name ? `(${info.asn_name})` : ''}</TableCell>
                      <TableCell>{info.prefix ?? '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {data.abuseipdb && data.abuseipdb.ips && Object.keys(data.abuseipdb.ips).length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> AbuseIPDB
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              IP reputation (spam, DDoS, abuse reports)
            </Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>IP</TableCell>
                    <TableCell>Abuse Score</TableCell>
                    <TableCell>Reports</TableCell>
                    <TableCell>ISP</TableCell>
                    <TableCell>Country</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(data.abuseipdb.ips).map(([ip, info]) => (
                    <TableRow key={ip}>
                      <TableCell>{ip}</TableCell>
                      <TableCell>
                        <Chip
                          label={`${info.abuse_score ?? 0}%`}
                          size="small"
                          color={(info.abuse_score ?? 0) >= 50 ? 'error' : (info.abuse_score ?? 0) >= 25 ? 'warning' : 'success'}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{info.total_reports ?? 0}</TableCell>
                      <TableCell sx={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }} title={info.isp}>
                        {info.isp ?? '-'}
                      </TableCell>
                      <TableCell>{info.country_code ?? '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {data.securitytrails && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> SecurityTrails
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {data.securitytrails.subdomain_count != null && `Subdomains indexed: ${data.securitytrails.subdomain_count}`}
              {data.securitytrails.tags && data.securitytrails.tags.length > 0 && (
                <Box component="span" sx={{ ml: 1, display: 'inline-flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {data.securitytrails.tags.map((t, i) => (
                    <Chip key={i} label={t} size="small" variant="outlined" />
                  ))}
                </Box>
              )}
            </Typography>
            {data.securitytrails.current_dns && (
              <Box sx={{ mt: 1.5 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                  Current DNS (first seen dates)
                </Typography>
                {data.securitytrails.current_dns.a?.values && data.securitytrails.current_dns.a.values.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" color="text.secondary">A records (since {data.securitytrails.current_dns.a.first_seen}):</Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.25 }}>
                      {data.securitytrails.current_dns.a.values.map((v, i) => (
                        <Chip key={i} label={`${v.ip} (${v.ip_organization || '-'})`} size="small" variant="outlined" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }} />
                      ))}
                    </Box>
                  </Box>
                )}
                {data.securitytrails.current_dns.mx?.values && data.securitytrails.current_dns.mx.values.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" color="text.secondary">MX (since {data.securitytrails.current_dns.mx.first_seen}):</Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25, mt: 0.25 }}>
                      {data.securitytrails.current_dns.mx.values.map((v, i) => (
                        <Typography key={i} variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                          {v.priority} {v.hostname} {v.hostname_organization ? `(${v.hostname_organization})` : ''}
                        </Typography>
                      ))}
                    </Box>
                  </Box>
                )}
                {data.securitytrails.current_dns.ns?.values && data.securitytrails.current_dns.ns.values.length > 0 && (
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="caption" color="text.secondary">NS (since {data.securitytrails.current_dns.ns.first_seen}):</Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.25 }}>
                      {data.securitytrails.current_dns.ns.values.map((v, i) => (
                        <Chip key={i} label={`${v.nameserver} (${v.nameserver_organization || '-'})`} size="small" variant="outlined" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }} />
                      ))}
                    </Box>
                  </Box>
                )}
                {data.securitytrails.current_dns.txt?.values && data.securitytrails.current_dns.txt.values.length > 0 && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">TXT (since {data.securitytrails.current_dns.txt.first_seen}):</Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25, mt: 0.25, maxHeight: 80, overflow: 'auto' }}>
                      {data.securitytrails.current_dns.txt.values.slice(0, 5).map((v, i) => (
                        <Typography key={i} variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.65rem', wordBreak: 'break-all' }}>
                          {String(v.value || '').slice(0, 80)}{(v.value?.length ?? 0) > 80 ? '…' : ''}
                        </Typography>
                      ))}
                      {data.securitytrails.current_dns.txt.values.length > 5 && (
                        <Typography variant="caption" color="text.secondary">+{data.securitytrails.current_dns.txt.values.length - 5} more</Typography>
                      )}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {data.phishtank && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> PhishTank
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Phishing database check for {data.phishtank.url ?? 'domain'}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              {data.phishtank.in_database ? (
                <>
                  <Chip icon={<ErrorIcon />} label="In phishing database" color="error" size="small" sx={{ fontWeight: 600 }} />
                  {data.phishtank.phish_detail_page && (
                    <Link href={data.phishtank.phish_detail_page} target="_blank" rel="noopener noreferrer" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: '0.875rem' }}>
                      Phish ID {data.phishtank.phish_id} <OpenInNewIcon sx={{ fontSize: 14 }} />
                    </Link>
                  )}
                  {data.phishtank.verified && (
                    <Chip label={`Verified: ${data.phishtank.valid ? 'Yes' : 'No'}`} size="small" variant="outlined" />
                  )}
                </>
              ) : (
                <Chip icon={<CheckCircleIcon />} label="Not in phishing database" color="success" size="small" sx={{ fontWeight: 600 }} />
              )}
            </Box>
          </CardContent>
        </Card>
      )}

      {data.zoomeye && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> ZoomEye
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Host search: {data.zoomeye.total ?? 0} results for domain:{data.zoomeye.domain ?? ''}
            </Typography>
            {data.zoomeye.hosts && data.zoomeye.hosts.length > 0 && (
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>IP</TableCell>
                      <TableCell>Port</TableCell>
                      <TableCell>Country</TableCell>
                      <TableCell>ASN</TableCell>
                      <TableCell>App</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.zoomeye.hosts.map((h, i) => (
                      <TableRow key={i}>
                        <TableCell sx={{ fontFamily: 'monospace' }}>{h.ip ?? '-'}</TableCell>
                        <TableCell>{h.port ?? '-'}</TableCell>
                        <TableCell>{h.country ?? '-'}</TableCell>
                        <TableCell>{h.asn ?? '-'}</TableCell>
                        <TableCell>{h.app ?? '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {data.criminalip && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> Criminal IP
            </Typography>
            {(() => {
              const d = data.criminalip.data as Record<string, unknown> | undefined
              const apiError = d && (d.status === 404 || (typeof d.status === 'number' && d.status >= 400))
              const apiMessage = d && typeof d.message === 'string' ? d.message : null
              if (apiError && apiMessage) {
                return (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                    <Chip icon={<WarningIcon />} label={`API: ${d.status}`} size="small" color="warning" variant="outlined" />
                    <Typography variant="body2" color="text.secondary">{apiMessage}</Typography>
                  </Box>
                )
              }
              return (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  {data.criminalip.risk_score != null && (
                    <Chip
                      label={`Risk score: ${data.criminalip.risk_score}`}
                      size="small"
                      color={data.criminalip.risk_score >= 70 ? 'error' : data.criminalip.risk_score >= 40 ? 'warning' : 'success'}
                      variant="outlined"
                    />
                  )}
                  {data.criminalip.is_safe != null && (
                    <Chip
                      icon={data.criminalip.is_safe ? <CheckCircleIcon /> : <WarningIcon />}
                      label={data.criminalip.is_safe ? 'Safe' : 'Risky'}
                      size="small"
                      color={data.criminalip.is_safe ? 'success' : 'warning'}
                    />
                  )}
                  {data.criminalip.risk_score == null && data.criminalip.is_safe == null && (
                    <Typography variant="body2" color="text.secondary">No risk data returned</Typography>
                  )}
                </Box>
              )
            })()}
          </CardContent>
        </Card>
      )}

      {data.pulsedive && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> Pulsedive
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
              {data.pulsedive.risk && (
                <Chip
                  label={`Risk: ${data.pulsedive.risk}`}
                  size="small"
                  color={data.pulsedive.risk === 'high' || data.pulsedive.risk === 'critical' ? 'error' : data.pulsedive.risk === 'medium' ? 'warning' : 'success'}
                  variant="outlined"
                />
              )}
              {data.pulsedive.risk_recommendation && (
                <Typography variant="body2" color="text.secondary">{data.pulsedive.risk_recommendation}</Typography>
              )}
            </Box>
            {data.pulsedive.threats && data.pulsedive.threats.length > 0 && (
              <Box sx={{ mb: 1 }}>
                <Typography variant="caption" color="text.secondary">Threats:</Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.25 }}>
                  {data.pulsedive.threats.map((t, i) => {
                    const label = typeof t === 'string' ? t : (t && typeof t === 'object' && ('name' in t ? String((t as { name?: string }).name) : 'title' in t ? String((t as { title?: string }).title) : null)) || JSON.stringify(t).slice(0, 30)
                    return <Chip key={i} label={label} size="small" color="error" variant="outlined" />
                  })}
                </Box>
              </Box>
            )}
            {data.pulsedive.feeds && data.pulsedive.feeds.length > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary">Feeds:</Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.25 }}>
                  {data.pulsedive.feeds.map((f, i) => {
                    const label = typeof f === 'string' ? f : (f && typeof f === 'object' && ('name' in f ? String((f as { name?: string }).name) : 'title' in f ? String((f as { title?: string }).title) : null)) || JSON.stringify(f).slice(0, 30)
                    return <Chip key={i} label={label} size="small" variant="outlined" />
                  })}
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {data.wayback && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> Web Archive (Wayback Machine)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              First available snapshot for domain
            </Typography>
            {data.wayback.error ? (
              <Chip icon={<WarningIcon />} label={data.wayback.error} size="small" color="warning" variant="outlined" />
            ) : data.wayback.first_snapshot_url ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                {data.wayback.first_snapshot_timestamp && (
                  <Chip label={data.wayback.first_snapshot_timestamp} size="small" variant="outlined" />
                )}
                <Link href={data.wayback.first_snapshot_url} target="_blank" rel="noopener noreferrer" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: '0.875rem' }}>
                  View snapshot <OpenInNewIcon sx={{ fontSize: 14 }} />
                </Link>
              </Box>
            ) : null}
          </CardContent>
        </Card>
      )}

      {data.ssllabs && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ApiIcon /> SSL Labs
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              TLS/cipher audit (weak protocols: TLS 1.0, TLS 1.1, SSLv3)
            </Typography>
            {data.ssllabs.error ? (
              <Chip icon={<WarningIcon />} label={data.ssllabs.error} size="small" color="warning" variant="outlined" />
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                {data.ssllabs.grade && (
                  <Chip label={`Grade: ${data.ssllabs.grade}`} size="small" color="primary" variant="outlined" />
                )}
                {data.ssllabs.has_weak_protocols && data.ssllabs.weak_protocols && data.ssllabs.weak_protocols.length > 0 ? (
                  <Chip
                    icon={<WarningIcon />}
                    label={`Weak: ${data.ssllabs.weak_protocols.join(', ')}`}
                    size="small"
                    color="error"
                    variant="outlined"
                  />
                ) : (
                  <Chip icon={<CheckCircleIcon />} label="No weak protocols" size="small" color="success" variant="outlined" />
                )}
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  )
}

export default ExternalApisPanel
