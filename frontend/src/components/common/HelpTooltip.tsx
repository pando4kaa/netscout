import { IconButton, Popover, Typography, Box } from '@mui/material'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import { useState } from 'react'

export interface HelpContent {
  title: string
  what: string
  whyImportant: string
  whyBad?: string
  tips?: string
}

const HELP_CONTENT: Record<string, HelpContent> = {
  security_alerts: {
    title: 'Security Alerts',
    what: 'The system shows automatically detected risks: Subdomain Takeover (when a subdomain points to an unconfigured service), expired SSL certificates, open dangerous ports (e.g. databases), outdated software versions with known vulnerabilities.',
    whyImportant: 'Each alert is a potential entry point for an attacker. The sooner you detect a problem, the less chance of compromise.',
    whyBad: 'If you ignore alerts, an attacker can exploit the vulnerability: gain access to data, redirect traffic to a phishing site, or take the service down.',
    tips: 'Check each alert manually. Some may be false positives, but it is better to verify than to miss one.',
  },
  risk_score: {
    title: 'Risk Score',
    what: 'A number from 0 to 100 showing the overall risk level for the domain. Calculated by weights: Subdomain Takeover (+10), open DB ports (+5), expired SSL (+5), outdated tech (+1–5).',
    whyImportant: 'Lets you understand how secure a domain is at a glance. No need to review all details separately.',
    whyBad: 'A high score means multiple issues at once. This may attract pentesters or attackers.',
    tips: '≥20 — high risk, urgent action needed. 10–19 — medium, plan fixes. <10 — low, but still check alerts.',
  },
  subdomains: {
    title: 'Subdomains',
    what: 'List of subdomains (e.g. mail.example.com, api.example.com) found via Certificate Transparency (crt.sh) and other sources. Shows all known subdomains for your domain.',
    whyImportant: 'Test or dev subdomains are often forgotten. They may have weak protection or point to outdated services.',
    whyBad: 'A forgotten subdomain (e.g. staging.example.com) may provide access to internal systems or be vulnerable to Subdomain Takeover.',
    tips: 'Review the list regularly. Remove or secure subdomains that are no longer in use.',
  },
  subdomain_takeover: {
    title: 'Subdomain Takeover',
    what: 'Vulnerability when a subdomain (e.g. blog.example.com) points to a third-party service (GitHub Pages, Heroku, S3) that nobody has registered. An attacker can claim this "free" service and gain control of the subdomain.',
    whyImportant: 'This allows an attacker to create phishing pages under your domain, steal cookies, bypass CORS.',
    whyBad: 'Users trust your domain. If blog.example.com shows malicious content — that is your reputation damage.',
    tips: 'Check all CNAME records. If they point to third-party services — either configure them (create a page) or remove the DNS record.',
  },
  ssl_expired: {
    title: 'Expired SSL Certificate',
    what: 'The certificate protecting HTTPS connections has expired. The browser will show "Connection not secure" warning; users may not be able to access the site.',
    whyImportant: 'Without a valid certificate, traffic is not encrypted. Someone on the network can intercept passwords and data.',
    whyBad: 'Man-in-the-middle attacks, loss of trust, Google downgrades such sites in search.',
    tips: 'Renew the certificate. Let\'s Encrypt is free. Set up automatic renewal (e.g. Certbot).',
  },
  open_port: {
    title: 'Open Ports',
    what: 'Ports are "doors" on the server. Each service listens on its port: 21 (FTP), 22 (SSH), 80 (HTTP), 443 (HTTPS), 3306 (MySQL), 5432 (PostgreSQL), 6379 (Redis), 3389 (RDP). If a port is open — it can be accessed from the internet.',
    whyImportant: 'Database and admin service ports should not be accessible externally. Otherwise — direct access without authorization.',
    whyBad: 'Open port 3306 (MySQL) — attacker can brute-force password. Open 22 (SSH) — brute force or exploit of outdated version.',
    tips: 'Restrict access via firewall. Allow access only from specific IPs or via VPN.',
  },
  expired_ssl: {
    title: 'Expired SSL Certificate',
    what: 'Certificate has expired. Connection without encryption or with browser warning.',
    whyImportant: 'Users may not trust the site; traffic may be intercepted.',
    whyBad: 'Man-in-the-middle attacks, loss of trust, SEO penalties.',
    tips: 'Renew the certificate (Let\'s Encrypt is free).',
  },
  outdated_tech: {
    title: 'Outdated Technologies',
    what: 'Detected software versions with known vulnerabilities (CVE). E.g. Nginx 1.18.0, Apache 2.4.49, OpenSSH 7.4 — have exploits that give full server access.',
    whyImportant: 'The older the version, the more likely there is a ready exploit. Updates are the simplest protection.',
    whyBad: 'Ready exploit scripts exist. An attacker can get root access in minutes.',
    tips: 'Regularly update Nginx, Apache, OpenSSH, PHP, Node, etc. Enable automatic security updates.',
  },
  ip_addresses: {
    title: 'IP Addresses',
    what: 'A records (IPv4) and AAAA records (IPv6) are the addresses that the domain and subdomains point to. When you enter example.com in the browser — DNS first returns the IP (e.g. 93.184.216.34), and only then the browser connects to the server.',
    whyImportant: 'Helps understand where the site is physically located, how many servers are used, and whether there is a CDN.',
    whyBad: 'Too many different IPs may indicate DDoS infrastructure or distributed attack. Unknown IPs — verify if you added them.',
    tips: 'Ensure all IPs belong to your infrastructure or your hosting provider.',
  },
  mx_records: {
    title: 'MX Records (Mail Servers)',
    what: 'Define where emails to @yourdomain.com are sent. Each record has a priority: the server with the lowest number (e.g. 10) is tried first, then the backup (20).',
    whyImportant: 'Proper configuration protects against spoofing (forging emails from your domain) and phishing.',
    whyBad: 'Without SPF/DMARC anyone can send emails "from" your domain. This is used for phishing.',
    tips: 'Configure SPF, DKIM and DMARC. Allow sending emails only from your servers.',
  },
  ssl_certificates: {
    title: 'SSL Certificates',
    what: 'Certificates for HTTPS. Contain: Subject (domain name), Issuer (who issued it), SAN (Subject Alternative Names — list of all covered domains), start and end dates.',
    whyImportant: 'Encrypt traffic between browser and server. Without them, passwords and data are transmitted in plain text.',
    whyBad: 'Expired or self-signed certificate — browser will show a warning. Users may not access the site.',
    tips: 'Check validity period. SAN shows which subdomains are covered — ensure all needed ones are included.',
  },
  port_scan: {
    title: 'Port Scanning',
    what: 'The system checks which ports are open on your domain\'s IP addresses. This shows which services are accessible from the internet: web (80, 443), SSH (22), databases (3306, 5432, 6379), RDP (3389), etc.',
    whyImportant: 'Database and admin tool ports should not be open externally. If they are open — that is a risk.',
    whyBad: 'Open MySQL (3306) or Redis (6379) without password — attacker can extract all data or get a shell.',
    tips: 'Restrict access to ports 22, 3306, 5432, 6379, 3389. Allow only from trusted networks.',
  },
  tech_stack: {
    title: 'Technology Stack',
    what: 'Detected technologies: web server (Nginx, Apache), language (PHP, Node), frameworks (Laravel, Express), CMS (WordPress). Data comes from HTTP headers (Server, X-Powered-By) and server responses.',
    whyImportant: 'Helps assess the attack surface. If WordPress is detected — check plugins. If PHP 7.2 — it is outdated.',
    whyBad: 'Outdated versions have known CVEs. An attacker can find an exploit for your version.',
    tips: 'Check versions. Hide or minimize Server, X-Powered-By headers.',
  },
  whois: {
    title: 'WHOIS',
    what: 'Public database of domain registration: who is the registrar, when created, when it expires, which name servers are used. This information is available to anyone.',
    whyImportant: 'Allows checking if the domain is approaching expiration. An expired domain can be re-registered.',
    whyBad: 'If the domain expires — attackers can buy it. You lose brand and traffic.',
    tips: 'Enable auto-renew. Add multiple contact emails. Enable transfer lock.',
  },
  dns: {
    title: 'DNS Records',
    what: 'DNS (Domain Name System) is the internet\'s "phone book". When you enter example.com, DNS converts it to an IP address. Record types: A (IPv4), AAAA (IPv6), MX (mail), TXT (text, verification), NS (name servers), CNAME (alias), SOA (zone parameters).',
    whyImportant: 'DNS is the foundation of the internet. Without it, the browser does not know where to connect. DNS errors can break the site or email.',
    whyBad: 'If an attacker gains access to the DNS panel (via password leak), they can change records and redirect traffic to their servers. Phishing, data theft.',
    tips: 'Secure access to the DNS panel (2FA, strong password). Enable DNSSEC to protect against response spoofing.',
  },
  // DNS record types (detailed)
  dns_a_record: {
    title: 'A Records (IPv4)',
    what: 'An A record maps a domain or subdomain to an IPv4 address (e.g. 93.184.216.34). When a user enters example.com, the browser requests the A record and gets the IP to connect to.',
    whyImportant: 'This is the foundation of websites. Without an A record, the domain will not open in the browser.',
    whyBad: 'If an attacker changes the A record to their IP — all traffic goes to their server. Phishing, data theft.',
    tips: 'Verify that A records point to your servers. Use CDN (Cloudflare, etc.) for additional protection.',
  },
  dns_aaaa_record: {
    title: 'AAAA Records (IPv6)',
    what: 'Same as A record, but for IPv6 (e.g. 2606:2800:220:1:248:1893:25c8:1946). IPv6 is the new standard gradually replacing IPv4 due to address exhaustion.',
    whyImportant: 'More networks support IPv6 only. Without AAAA records — some users may not be able to access.',
    whyBad: 'Missing AAAA is not critical, but limits availability. Verify that IPv6 addresses belong to you.',
    tips: 'If hosting supports IPv6 — add AAAA records. This improves availability.',
  },
  dns_mx_record: {
    title: 'MX Records (Mail Servers)',
    what: 'Define where to send emails to @yourdomain.com. Each record has: priority (lower = more important) and mail server hostname. E.g.: 10 mail.example.com, 20 backup.example.com.',
    whyImportant: 'Without MX records, emails to your domain will not be delivered. With wrong ones — they go to other servers.',
    whyBad: 'If MX points to an unknown server — someone may read your mail. Verify hostname and priorities.',
    tips: 'Configure SPF, DKIM, DMARC. Use a reliable mail provider (Google Workspace, Microsoft 365).',
  },
  dns_ns_record: {
    title: 'NS Records (Name Servers)',
    what: 'Specify which servers are responsible for this domain\'s DNS. E.g. ns1.cloudflare.com, ns2.cloudflare.com. The domain registrar knows these addresses and routes queries to them.',
    whyImportant: 'NS controls all other DNS records. Whoever owns NS — owns the domain from a DNS perspective.',
    whyBad: 'Changing NS to unknown servers — attacker gets full control. Can redirect traffic, forge mail.',
    tips: 'Secure access to the registrar panel. Enable transfer lock. Do not change NS without understanding the consequences.',
  },
  dns_txt_record: {
    title: 'TXT Records',
    what: 'Text records for various purposes: domain verification (Google, Microsoft), SPF (allowed mail servers), DKIM (email signing), DMARC (policy for handling mismatches). Can contain arbitrary text.',
    whyImportant: 'SPF/DKIM/DMARC protect against email spoofing. Verification records confirm you own the domain.',
    whyBad: 'Missing SPF — anyone can send emails "from your domain". Phishing in your company\'s name.',
    tips: 'Add SPF, DKIM, DMARC. Check TXT records after changes to mail configuration.',
  },
  dns_soa_record: {
    title: 'SOA Records',
    what: 'Start of Authority — technical record with DNS zone parameters: primary name server, admin email, serial number, refresh timeouts. Used for replication between DNS servers.',
    whyImportant: 'Required for proper DNS operation. Usually configured by the hosting provider.',
    whyBad: 'Incorrect SOA can cause DNS update issues between servers.',
    tips: 'If using external DNS (Cloudflare, Route53) — SOA is managed by them. Rarely needs manual changes.',
  },
  dns_cname_record: {
    title: 'CNAME Records',
    what: 'Alias: one domain points to another. E.g. www.example.com → example.com, or blog.example.com → myblog.github.io. The browser gets the IP from the target domain.',
    whyImportant: 'Allows using third-party services (GitHub Pages, Heroku) without changing IP. Convenient for subdomains.',
    whyBad: 'If CNAME points to a third-party service (e.g. xxx.github.io) that you have not configured — Subdomain Takeover is possible.',
    tips: 'Check all CNAMEs. If they point to third-party services — configure them or remove the record.',
  },
  dns_email_security: {
    title: 'Email Security (SPF, DMARC, DKIM)',
    what: 'SPF — list of IPs/domains allowed to send email from your domain. DMARC — policy for handling emails that fail verification. DKIM — cryptographic signing of emails.',
    whyImportant: 'Without these records, anyone can send emails "from" your domain. This is the basis of phishing.',
    whyBad: 'Missing DMARC — mail servers do not know what to do with forged emails. They may land in inbox.',
    tips: 'Configure SPF (allow only your servers), DKIM (sign emails), DMARC (policy=reject or quarantine for forgeries).',
  },
  dns_zone_transfer: {
    title: 'Zone Transfer (AXFR)',
    what: 'AXFR — mechanism for copying the entire DNS zone from one server to another. Used for replication between primary and secondary name servers.',
    whyImportant: 'If AXFR is available to anyone — an attacker can get the full list of all subdomains and records. This exposes infrastructure.',
    whyBad: 'Open AXFR — information leak. Attacker sees all internal subdomains.',
    tips: 'AXFR should be available only to secondary name servers. Restrict by IP.',
  },
  dns_ptr_record: {
    title: 'PTR Records (Reverse DNS)',
    what: 'Reverse DNS: IP → hostname. E.g. 93.184.216.34 → example.com. Used for mail verification (many servers reject emails without PTR), logging.',
    whyImportant: 'Some mail servers check PTR. If missing or mismatched — emails may go to spam.',
    whyBad: 'Incorrect PTR may point to another domain — confusion, possible mail issues.',
    tips: 'Configure PTR for mail servers. Contact your hosting provider — this is usually set in the panel.',
  },
  // Other panels
  geo_map: {
    title: 'Geolocation',
    what: 'The map shows the geographic location of your domain\'s IP addresses. Each marker is an IP with known latitude and longitude (from GeoLite2 database).',
    whyImportant: 'Helps understand where servers are physically located. Useful for detecting unexpected locations (e.g. server in a country you do not work with).',
    whyBad: 'Servers in unexpected countries may indicate compromise or use of cheap hosting by attackers.',
    tips: 'Verify that all locations match your infrastructure. CDN shows many points — that is normal.',
  },
  external_apis: {
    title: 'External APIs',
    what: 'Data from various security services: VirusTotal (antivirus engines), Shodan (ports, vulnerabilities), Censys, AlienVault OTX (threat intel), URLScan, PhishTank (phishing), AbuseIPDB, BGPView, SSL Labs, etc.',
    whyImportant: 'Each service has its own knowledge base. Together they give a broader picture: whether the domain is in threat lists, which ports are open, whether there is phishing.',
    whyBad: 'If VirusTotal shows "malicious" — domain is on blacklists. PhishTank "in database" — phishing. AlienVault pulses — domain mentioned in threat reports.',
    tips: 'Some APIs require keys (VIRUSTOTAL_API_KEY etc.). Add them to .env for full checks.',
  },
  // Individual API descriptions
  api_virustotal: {
    title: 'VirusTotal',
    what: 'Free Google service that analyzes domains and URLs using 70+ antivirus engines and security tools. Checks if the object is on blacklists.',
    whyImportant: 'Quickly shows if the domain is flagged as malicious. If at least one engine marked it as malicious — that is a serious signal.',
    whyBad: 'Malicious > 0 — domain on blacklists. Suspicious > 0 — suspicious activity. Reputation < 0 — degraded reputation.',
    tips: 'Requires VIRUSTOTAL_API_KEY. Malicious/Suspicious/Harmless/Undetected — count of engines with each verdict.',
  },
  api_alienvault_otx: {
    title: 'AlienVault OTX',
    what: 'Open Threat Exchange — crowdsourced threat intelligence platform. Thousands of researchers share IoCs (indicators of compromise): IPs, domains, hashes.',
    whyImportant: 'Threat pulses — reports containing your domain. If pulse_count > 0 — domain mentioned in threat intel. Alexa rank — site popularity.',
    whyBad: 'Pulses > 0 — verification recommended. Domain may be linked to threats (phishing, malware, C2).',
    tips: 'Requires ALIENVAULT_OTX_API_KEY. WHOIS and Alexa links — for detailed investigation.',
  },
  api_urlscan: {
    title: 'URLScan.io',
    what: 'URL scanning service: opens the page, takes a screenshot, records network requests, collects links. Shows what happens when the site is opened.',
    whyImportant: 'Helps detect redirects to phishing, malware downloads, suspicious scripts. total scans — how many times scanned; unique URLs — found links.',
    whyBad: 'Large number of unique URLs may indicate dynamic content or suspicious activity.',
    tips: 'Works automatically. Shows URL list with scan counts. Click — opens details on urlscan.io.',
  },
  api_shodan: {
    title: 'Shodan',
    what: 'Search engine for internet-connected devices. Indexes open ports, service banners, vulnerabilities. Shows what is accessible from the internet on each IP.',
    whyImportant: 'Detects open ports (DB, RDP, SSH), tags (web server, CMS), vulnerabilities (CVE). Helps assess attack surface.',
    whyBad: 'Vulns — known vulnerabilities. Open ports 3389 (RDP), 3306 (MySQL) — critical risks.',
    tips: 'Requires SHODAN_API_KEY. Table: IP, ports, tags, vulnerabilities for each domain host.',
  },
  api_censys: {
    title: 'Censys',
    what: 'Internet scanning platform (from ZMap team). Collects data on servers, certificates, open ports. Alternative to Shodan.',
    whyImportant: 'Total hosts — number of IPs associated with the domain. Names — hostname for each IP. Helps understand infrastructure.',
    whyBad: 'Many unknown hosts — verify they all belong to you.',
    tips: 'Requires CENSYS_API_KEY. Shows IPs and associated names.',
  },
  api_threatcrowd: {
    title: 'ThreatCrowd',
    what: 'Crowdsourced threat database. Users vote domains/IPs as malicious. Collects related subdomains, resolutions (IPs) from threat reports.',
    whyImportant: 'Votes — count of "malicious" votes. Subdomains — subdomains from threat reports. Resolutions — IPs from threat intel.',
    whyBad: 'High votes — community considers domain suspicious. Check related subdomains.',
    tips: 'Works automatically. Community-driven — data from security researchers.',
  },
  api_bgpview: {
    title: 'BGPView',
    what: 'BGP (Border Gateway Protocol) data: ASN (autonomous system), network prefix for each IP. Shows who owns the network block.',
    whyImportant: 'ASN — provider identifier (e.g. Cloudflare, AWS). Prefix — IP range. Helps understand hosting and geolocation.',
    whyBad: 'Unexpected ASN — IP may belong to a different provider than you expected.',
    tips: 'Works automatically. Table: IP, ASN (provider name), prefix.',
  },
  api_abuseipdb: {
    title: 'AbuseIPDB',
    what: 'IP reputation database: reports on spam, DDoS, malicious activity. Abuse score 0–100, total reports — how many times reported.',
    whyImportant: 'Abuse score ≥ 50 — high risk. ≥ 25 — medium. ISP and Country — who owns the IP and where it is located.',
    whyBad: 'High abuse score — IP was used for attacks. Your server may be compromised or in a shared pool.',
    tips: 'Requires ABUSEIPDB_API_KEY. Check IPs with high score.',
  },
  api_securitytrails: {
    title: 'SecurityTrails',
    what: 'DNS history and infrastructure database. Subdomain count — indexed subdomains. Current DNS — current A, MX, NS, TXT with first seen dates.',
    whyImportant: 'Helps detect historical DNS changes. Tags — domain categories. First seen — when the record appeared.',
    whyBad: 'Sudden DNS changes — possible compromise. Unknown tags — verify.',
    tips: 'Requires SECURITYTRAILS_API_KEY. Shows history and current DNS state.',
  },
  api_phishtank: {
    title: 'PhishTank',
    what: 'Phishing URL database. Checks if domain or URL is in the list of confirmed phishing sites. Community-driven, free.',
    whyImportant: 'In database = true — domain was used for phishing. Phish ID — link to details. Verified — whether confirmed by humans.',
    whyBad: 'If in database — domain is on phishing blacklist. Critical for reputation.',
    tips: 'Works automatically. May return 403 due to Cloudflare — add delay or use API key.',
  },
  api_zoomeye: {
    title: 'ZoomEye',
    what: 'Chinese search engine for internet-connected devices (Shodan alternative). Indexes hosts, ports, countries, ASN, applications.',
    whyImportant: 'Total — number of hosts found. IP, Port, Country, ASN, App — details for each. Different perspective compared to Shodan.',
    whyBad: 'Open dangerous ports — check the table.',
    tips: 'Requires ZOOMEYE_API_KEY. Table: IP, port, country, ASN, detected application.',
  },
  api_criminalip: {
    title: 'Criminal IP',
    what: 'Threat intel service: risk score 0–100, is_safe (yes/no). Analyzes domain for links to malware, phishing, botnets.',
    whyImportant: 'Risk score ≥ 70 — high risk. is_safe = false — domain is unsafe per service assessment.',
    whyBad: 'High risk score — domain in threat intel. Verification needed.',
    tips: 'Requires CRIMINALIP_API_KEY. Shows overall security assessment.',
  },
  api_pulsedive: {
    title: 'Pulsedive',
    what: 'Threat intel platform: risk (low/medium/high/critical), threats (detected threats), feeds (sources that flagged the object).',
    whyImportant: 'Risk — overall level. Threats — specific threats (malware, phishing). Feeds — which databases contain this domain.',
    whyBad: 'High/critical risk — domain in threat intel. Review threats and feeds.',
    tips: 'Works automatically. Risk recommendation — advice from the service.',
  },
  api_wayback: {
    title: 'Web Archive (Wayback Machine)',
    what: 'Internet archive from Internet Archive. Stores web page snapshots since 1996. First snapshot — earliest saved version of the domain.',
    whyImportant: 'Helps see site history: what was there before, whether content changed. Useful for investigations.',
    whyBad: 'Empty result — domain was never archived or request error.',
    tips: 'Works automatically. First snapshot URL — link to archived version.',
  },
  api_ssllabs: {
    title: 'SSL Labs',
    what: 'Qualys service for TLS/SSL audit. Checks protocols (TLS 1.0, 1.1, SSLv3), ciphers, grade (A–F). Weak protocols — outdated insecure protocols.',
    whyImportant: 'Grade A — good. Weak protocols (TLS 1.0, SSLv3) — vulnerable to attacks. Helps assess encryption.',
    whyBad: 'Weak protocols — possible downgrade attacks. Grade below A — improvement needed.',
    tips: 'Works automatically. Checks main domain on HTTPS.',
  },
  graph_view: {
    title: 'Relationship Graph',
    what: 'Visualization of links between domain, subdomains, IPs, MX, NS. Each node — entity, each edge — connection (e.g. subdomain → IP).',
    whyImportant: 'Lets you see infrastructure structure at a glance. Easier to find "orphaned" subdomains or unexpected connections.',
    whyBad: 'Complex graph with many unknown nodes may indicate branched infrastructure or mixed data.',
    tips: 'Use different layouts (radial, tree, force). Click on node shows details. Export to PNG or JSON for reports.',
  },
  domain_info: {
    title: 'Domain Information',
    what: 'Basic WHOIS data: domain, registrar, creation and expiration dates. This is the domain\'s "passport".',
    whyImportant: 'Expiration date — when to renew the domain. Registrar — who to contact for issues.',
    whyBad: 'Expired domain can be re-registered. Wrong contacts — you will not receive notifications.',
    tips: 'Enable auto-renew. Verify contact details in WHOIS.',
  },
  correlation: {
    title: 'Correlation',
    what: 'Links between IPs and subdomains: which subdomains point to one IP, reverse DNS (PTR) for IPs. Shows how different parts of infrastructure are connected.',
    whyImportant: 'One IP can serve many subdomains. Helps understand architecture and detect unexpected connections.',
    whyBad: 'Unexpected connections (e.g. corporate subdomain on shared IP with unknown site) — possible risk.',
    tips: 'Verify that all subdomains on each IP are yours. PTR records should match your brand.',
  },
  name_servers: {
    title: 'Name Servers',
    what: 'NS records — servers responsible for the domain\'s DNS. All queries for IP, MX, TXT etc. go to them. Usually registrar or CDN servers (Cloudflare, etc.).',
    whyImportant: 'Whoever controls NS — controls DNS. Changing NS changes the entire domain configuration.',
    whyBad: 'Unknown NS — verify if you configured them. Possible compromise or error.',
    tips: 'Use a reliable DNS provider. Enable 2FA on the registrar panel.',
  },
  subdomains_preview: {
    title: 'Subdomains Preview',
    what: 'First 20 subdomains from the full list. Full list — on the "Subdomains" tab.',
    whyImportant: 'Quick overview without switching tabs. Helps assess scale.',
    tips: 'Click on subdomain in full list to copy, open in new tab.',
  },
}

interface HelpTooltipProps {
  topic: keyof typeof HELP_CONTENT
  size?: 'small' | 'medium'
}

const HelpTooltip = ({ topic, size = 'small' }: HelpTooltipProps) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const content = HELP_CONTENT[topic]

  if (!content) return null

  const handleClick = (e: React.MouseEvent<HTMLElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setAnchorEl(e.currentTarget)
  }

  const handleClose = () => setAnchorEl(null)
  const open = Boolean(anchorEl)

  return (
    <>
      <IconButton
        size={size}
        onClick={handleClick}
        sx={{
          color: 'text.secondary',
          p: 0.25,
          '&:hover': { color: 'primary.main', bgcolor: 'action.hover' },
        }}
        aria-label={`Help: ${content.title}`}
      >
        <HelpOutlineIcon fontSize={size === 'small' ? 'small' : 'medium'} />
      </IconButton>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        slotProps={{ paper: { sx: { maxWidth: 440, p: 2 } } }}
      >
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            {content.title}
          </Typography>
          <Typography variant="body2" paragraph>
            <strong>What:</strong> {content.what}
          </Typography>
          <Typography variant="body2" paragraph>
            <strong>Why important:</strong> {content.whyImportant}
          </Typography>
          {content.whyBad && (
            <Typography variant="body2" paragraph sx={{ color: 'error.main' }}>
              <strong>Why bad:</strong> {content.whyBad}
            </Typography>
          )}
          {content.tips && (
            <Typography variant="body2" color="text.secondary">
              <strong>Tip:</strong> {content.tips}
            </Typography>
          )}
        </Box>
      </Popover>
    </>
  )
}

export default HelpTooltip
export { HELP_CONTENT }
