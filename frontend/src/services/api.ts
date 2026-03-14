import axios from 'axios'
import { ScanResults } from '../types'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

export interface HistoryFilters {
  limit?: number
  offset?: number
  domain?: string
  risk_min?: number
  risk_max?: number
  date_from?: string
  date_to?: string
}

export const scanApi = {
  startScan: async (domain: string) => {
    const response = await api.post('/scan', { domain })
    return response.data
  },

  getResults: async (scanId: string) => {
    const response = await api.get(`/scan/${scanId}`)
    const data = response.data
    if (data.results) return data.results
    return null
  },

  getHistory: async (filters?: HistoryFilters) => {
    const params = new URLSearchParams()
    if (filters?.limit) params.set('limit', String(filters.limit))
    if (filters?.offset) params.set('offset', String(filters.offset))
    if (filters?.domain) params.set('domain', filters.domain)
    if (filters?.risk_min != null) params.set('risk_min', String(filters.risk_min))
    if (filters?.risk_max != null) params.set('risk_max', String(filters.risk_max))
    if (filters?.date_from) params.set('date_from', filters.date_from)
    if (filters?.date_to) params.set('date_to', filters.date_to)
    const url = params.toString() ? `/scan/history?${params}` : '/scan/history'
    const response = await api.get(url)
    return response.data
  },

  compareScans: async (scanId1: string, scanId2: string) => {
    const response = await api.get('/scan/compare', {
      params: { scan_id_1: scanId1, scan_id_2: scanId2 },
    })
    return response.data
  },

  getSchedules: async () => {
    const response = await api.get('/schedules')
    return response.data
  },

  createSchedule: async (domain: string, intervalHours: number = 24) => {
    const response = await api.post('/schedules', { domain, interval_hours: intervalHours })
    return response.data
  },

  deleteSchedule: async (scheduleId: number) => {
    const response = await api.delete(`/schedules/${scheduleId}`)
    return response.data
  },

  toggleSchedule: async (scheduleId: number, enabled: boolean) => {
    const response = await api.patch(`/schedules/${scheduleId}`, { enabled })
    return response.data
  },
}

export const authApi = {
  register: async (email: string, username: string, password: string) => {
    const response = await api.post('/auth/register', { email, username, password })
    return response.data
  },

  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    return response.data
  },

  updateEmailNotifications: async (enabled: boolean) => {
    const response = await api.patch('/auth/me', { email_notifications_enabled: enabled })
    return response.data
  },
}

export const investigationsApi = {
  list: async () => {
    const response = await api.get('/investigations')
    return response.data
  },

  create: async (name: string = 'New Investigation') => {
    const response = await api.post('/investigations', { name })
    return response.data
  },

  get: async (id: string) => {
    const response = await api.get(`/investigations/${id}`)
    return response.data
  },

  update: async (id: string, name: string) => {
    const response = await api.patch(`/investigations/${id}`, { name })
    return response.data
  },

  delete: async (id: string) => {
    const response = await api.delete(`/investigations/${id}`)
    return response.data
  },

  addEntity: async (id: string, entityType: string, entityValue: string) => {
    const response = await api.post(`/investigations/${id}/entities`, {
      entity_type: entityType,
      entity_value: entityValue,
    })
    return response.data
  },

  updateEntityMetadata: async (
    id: string,
    cyId: string,
    metadata: { notes?: string; tags?: string[] }
  ) => {
    const response = await api.patch(`/investigations/${id}/entities`, {
      cy_id: cyId,
      notes: metadata.notes,
      tags: metadata.tags,
    })
    return response.data
  },

  runEnricher: async (id: string, entityType: string, entityValue: string, enricherName: string) => {
    const response = await api.post(`/investigations/${id}/run-enricher`, {
      entity_type: entityType,
      entity_value: entityValue,
      enricher_name: enricherName,
    })
    return response.data
  },

  getEnricherTaskStatus: async (id: string, taskId: string) => {
    const response = await api.get(`/investigations/${id}/tasks/${taskId}`)
    return response.data
  },

  exportJson: async (id: string) => {
    const response = await api.get(`/investigations/${id}/export/json`)
    return response.data
  },

  createShareLink: async (id: string, expiresDays: number = 7) => {
    const response = await api.post(`/investigations/${id}/share`, {
      expires_days: expiresDays,
    })
    return response.data
  },

  getShared: async (token: string) => {
    const response = await api.get(`/investigations/shared/${token}`)
    return response.data
  },

  downloadCsv: async (id: string) => {
    const response = await api.get(`/investigations/${id}/export/csv`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `investigation_${id}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

export interface Notification {
  id: number
  domain: string
  scan_id: string
  scan_id_prev: string
  type: string
  title: string
  message: string
  details: Record<string, unknown>
  severity: 'info' | 'warning' | 'critical'
  read_at: string | null
  created_at: string
}

export interface NotificationReport {
  notification: { id: number; domain: string; type: string; title: string; message: string; created_at: string }
  comparison: Record<string, unknown>
}

export const notificationsApi = {
  list: async (params?: { limit?: number; offset?: number; domain?: string; unread_only?: boolean }) => {
    const search = new URLSearchParams()
    if (params?.limit) search.set('limit', String(params.limit))
    if (params?.offset) search.set('offset', String(params.offset))
    if (params?.domain) search.set('domain', params.domain)
    if (params?.unread_only) search.set('unread_only', 'true')
    const url = search.toString() ? `/notifications?${search}` : '/notifications'
    const response = await api.get(url)
    return response.data as { notifications: Notification[]; unread_count: number }
  },

  getUnreadCount: async () => {
    const response = await api.get('/notifications/unread-count')
    return response.data as { count: number }
  },

  markRead: async (id: number) => {
    const response = await api.patch(`/notifications/${id}/read`)
    return response.data
  },

  markAllRead: async () => {
    const response = await api.patch('/notifications/read-all')
    return response.data
  },

  getReport: async (id: number) => {
    const response = await api.get(`/notifications/${id}/report`)
    return response.data as NotificationReport
  },

  exportJson: async (id: number) => {
    const response = await api.get(`/notifications/${id}/export/json`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `notification_${id}_report.json`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}
