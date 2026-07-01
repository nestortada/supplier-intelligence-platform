import { apiRequest } from './http'
import type { SyncStatus } from '../types/opportunity'

export function fetchSyncStatus(): Promise<SyncStatus> {
  return apiRequest<SyncStatus>('/sync/status')
}

export function runSync(): Promise<SyncStatus> {
  return apiRequest<SyncStatus>('/sync/run', {
    method: 'POST',
  })
}
