import axios from 'axios'
import { ScanResults } from '../types'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const scanApi = {
  startScan: async (domain: string) => {
    const response = await api.post('/scan', { domain })
    return response.data
  },

  getResults: async (scanId: string): Promise<ScanResults> => {
    const response = await api.get(`/scan/${scanId}`)
    return response.data
  },

  getHistory: async () => {
    const response = await api.get('/scan/history')
    return response.data
  },
}
