import { apiRequest, buildQuery } from './http'
import type { DashboardSupplierPerformance, DashboardSummary, DashboardTopOpportunity } from '../types/dashboard'

export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>('/dashboard/summary')
}

export function fetchDashboardTopOpportunities(limit = 10): Promise<DashboardTopOpportunity[]> {
  return apiRequest<DashboardTopOpportunity[]>(`/dashboard/top-opportunities${buildQuery({ limit })}`)
}

export function fetchDashboardSupplierPerformance(): Promise<DashboardSupplierPerformance[]> {
  return apiRequest<DashboardSupplierPerformance[]>('/dashboard/supplier-performance')
}
