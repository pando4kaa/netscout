import { create } from 'zustand'
import { ScanResults } from '../types'

interface ScanState {
  currentScan: ScanResults | null
  scanHistory: ScanResults[]
  setCurrentScan: (scan: ScanResults | null) => void
  addToHistory: (scan: ScanResults) => void
  clearCurrentScan: () => void
}

export const useScanStore = create<ScanState>((set) => ({
  currentScan: null,
  scanHistory: [],
  setCurrentScan: (scan) => set({ currentScan: scan }),
  addToHistory: (scan) =>
    set((state) => ({
      scanHistory: [...state.scanHistory, scan],
    })),
  clearCurrentScan: () => set({ currentScan: null }),
}))
