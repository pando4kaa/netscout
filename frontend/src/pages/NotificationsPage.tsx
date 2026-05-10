import {
  Box,
  Typography,
  Paper,
  List,
  ListItemButton,
  ListItemText,
  Chip,
  Button,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive'
import { useState, useEffect, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authApi, notificationsApi, type Notification } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import NotificationDetailDialog from '../components/notifications/NotificationDetailDialog'
import { useLocaleFormatters } from '../i18n/format'

const severityColors: Record<string, 'default' | 'warning' | 'error'> = {
  info: 'default',
  warning: 'warning',
  critical: 'error',
}

const NotificationsPage = () => {
  const { t } = useTranslation()
  const { formatDateTime } = useLocaleFormatters()
  const [searchParams, setSearchParams] = useSearchParams()
  const { isAuthenticated, user, updateUser } = useAuth()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [domainFilter, setDomainFilter] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [selected, setSelected] = useState<Notification | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const fetchNotifications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await notificationsApi.list({
        limit: 100,
        offset: 0,
        domain: domainFilter || undefined,
        unread_only: unreadOnly,
      })
      setNotifications(data.notifications)
      setUnreadCount(data.unread_count)
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'response' in e
        ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : e instanceof Error ? e.message : t('errors.failedToLoad')
      setError(typeof msg === 'string' ? msg : t('errors.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [domainFilter, unreadOnly, t])

  useEffect(() => {
    if (isAuthenticated) fetchNotifications()
  }, [isAuthenticated, fetchNotifications])

  // Handle unsubscribe from email link (?unsubscribe=1)
  const [unsubscribed, setUnsubscribed] = useState(false)
  useEffect(() => {
    if (!isAuthenticated || unsubscribed) return
    if (searchParams.get('unsubscribe') === '1' && user?.email_notifications_enabled) {
      authApi.updateEmailNotifications(false).then(() => {
        updateUser({ email_notifications_enabled: false })
        setUnsubscribed(true)
        setSearchParams({})
      }).catch(() => {})
    }
  }, [isAuthenticated, searchParams, user?.email_notifications_enabled, unsubscribed])

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead()
      setUnreadCount(0)
      setNotifications((prev) => prev.map((n) => ({ ...n, read_at: new Date().toISOString() })))
    } catch {
      // ignore
    }
  }

  const handleSelect = (n: Notification) => {
    setSelected(n)
    setDetailOpen(true)
    if (!n.read_at) {
      notificationsApi.markRead(n.id).then(() => {
        setUnreadCount((c) => Math.max(0, c - 1))
        setNotifications((prev) =>
          prev.map((item) => (item.id === n.id ? { ...item, read_at: new Date().toISOString() } : item))
        )
      })
    }
  }

  const handleDetailClose = () => {
    setDetailOpen(false)
    setSelected(null)
  }

  if (!isAuthenticated) {
    return (
      <Box sx={{ textAlign: 'center', py: 6 }}>
        <Typography variant="h6" gutterBottom>
          {t('notifications.signInTitle')}
        </Typography>
        <Button component={Link} to="/login" variant="contained">
          {t('navigation.signIn')}
        </Button>
      </Box>
    )
  }

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: { xs: 'stretch', sm: 'flex-start' },
          gap: 2,
          mb: 3,
        }}
      >
        <Box sx={{ display: 'flex', gap: 2, minWidth: 0, flex: { sm: 1 } }}>
          <NotificationsActiveIcon
            sx={{ fontSize: 36, color: 'primary.main', flexShrink: 0, mt: { xs: 0, sm: 0.25 } }}
          />
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="h4" fontWeight={600} sx={{ typography: { xs: 'h5', sm: 'h4' } }}>
              {t('notifications.title')}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t('notifications.subtitle')}
            </Typography>
          </Box>
        </Box>
        {unreadCount > 0 && (
          <Button
            variant="outlined"
            onClick={handleMarkAllRead}
            size="small"
            sx={{
              alignSelf: { xs: 'stretch', sm: 'center' },
              flexShrink: 0,
              whiteSpace: { sm: 'nowrap' },
            }}
          >
            {t('notifications.markAllRead', { count: unreadCount })}
          </Button>
        )}
      </Box>

      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <TextField
          size="small"
          placeholder={t('notifications.filterByDomain')}
          value={domainFilter}
          onChange={(e) => setDomainFilter(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 220 }}
        />
        <Button
          variant={unreadOnly ? 'contained' : 'outlined'}
          size="small"
          onClick={() => setUnreadOnly(!unreadOnly)}
        >
          {t('notifications.unreadOnly')}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {unsubscribed && (
        <Alert severity="info" sx={{ mb: 2 }} onClose={() => setUnsubscribed(false)}>
          {t('notifications.disabled')}
        </Alert>
      )}

      <Paper sx={{ overflow: 'hidden' }}>
        {loading ? (
          <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : notifications.length === 0 ? (
          <Box sx={{ py: 6, textAlign: 'center', color: 'text.secondary' }}>
            <Typography>{t('notifications.empty')}</Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              {t('notifications.emptyHint')}
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {notifications.map((n) => (
              <ListItemButton
                key={n.id}
                onClick={() => handleSelect(n)}
                sx={{
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                  bgcolor: n.read_at ? undefined : 'action.hover',
                }}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                      <Typography variant="subtitle1" fontWeight={n.read_at ? 400 : 600}>
                        {n.domain}
                      </Typography>
                      <Chip label={n.type} size="small" color={severityColors[n.severity] || 'default'} />
                      {!n.read_at && (
                        <Chip label={t('common.new')} size="small" color="primary" sx={{ height: 20 }} />
                      )}
                    </Box>
                  }
                  secondary={
                    <>
                      <Typography variant="body2" color="text.secondary">
                        {n.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {formatDateTime(n.created_at)}
                      </Typography>
                    </>
                  }
                />
              </ListItemButton>
            ))}
          </List>
        )}
      </Paper>

      <NotificationDetailDialog
        open={detailOpen}
        onClose={handleDetailClose}
        notification={selected}
        onReportLoaded={() => {}}
      />
    </Box>
  )
}

export default NotificationsPage
