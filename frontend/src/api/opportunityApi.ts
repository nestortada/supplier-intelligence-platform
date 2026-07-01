import { apiRequest, buildQuery } from './http'
import type {
  CatalogUploadResponse,
  JobStatus,
  ProductAnalysisDetail,
  ProductDatabaseClearResponse,
  ProductJobResponse,
  ProductSelectionClearResponse,
  ProductSelectionResponse,
  RankingFilters,
  RankingItem,
  SalePerformance,
  SelectedProductItem,
} from '../types/opportunity'

const RANKING_IMPORT_SUPPLIER = 'Ranking Import'

function numericFilter(value: string): number | undefined {
  if (value.trim() === '') {
    return undefined
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

export function uploadCatalogFile(file: File): Promise<CatalogUploadResponse> {
  const formData = new FormData()
  formData.set('file', file)
  formData.set('supplier_name', RANKING_IMPORT_SUPPLIER)

  return apiRequest<CatalogUploadResponse>('/catalogs/upload', {
    method: 'POST',
    body: formData,
  })
}

export function enrichPendingProducts(): Promise<ProductJobResponse> {
  return apiRequest<ProductJobResponse>('/products/enrich-apify', {
    method: 'POST',
    body: JSON.stringify({
      all_pending: true,
      force_refresh: true,
      run_analysis_after: true,
    }),
  })
}

export function analyzeAllProducts(): Promise<ProductJobResponse> {
  return apiRequest<ProductJobResponse>('/products/analyze', {
    method: 'POST',
    body: JSON.stringify({
      all: true,
    }),
  })
}

export function fetchJobStatus(jobId: number): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/jobs/${jobId}`)
}

export function fetchJobs(filters: { type?: string; status?: string } = {}): Promise<JobStatus[]> {
  return apiRequest<JobStatus[]>(
    `/jobs${buildQuery({
      type: filters.type,
      status: filters.status,
    })}`,
  )
}

export function cancelJob(jobId: number): Promise<JobStatus> {
  return apiRequest<JobStatus>(`/jobs/${jobId}/cancel`, {
    method: 'PATCH',
  })
}

export function fetchOpportunityRanking(filters: RankingFilters): Promise<RankingItem[]> {
  return apiRequest<RankingItem[]>(
    `/products/ranking${buildQuery({
      min_score: filters.minScore || undefined,
      status: filters.recommendation === 'all' ? undefined : filters.recommendation,
      min_roi: filters.minRoi ? filters.minRoi / 100 : undefined,
      min_margin: filters.minMargin || undefined,
      min_sales: filters.minSales || undefined,
      sellers_min: numericFilter(filters.sellersMin),
      sellers_max: numericFilter(filters.sellersMax),
    })}`,
  )
}

export function fetchProductAnalysisDetail(productId: number): Promise<ProductAnalysisDetail> {
  return apiRequest<ProductAnalysisDetail>(`/products/${productId}/analysis`)
}

export function deleteProduct(productId: number): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/products/${productId}`, {
    method: 'DELETE',
  })
}

export function deleteAllProducts(): Promise<ProductDatabaseClearResponse> {
  return apiRequest<ProductDatabaseClearResponse>('/products/database', {
    method: 'DELETE',
  })
}

export function fetchSelectedProducts(): Promise<SelectedProductItem[]> {
  return apiRequest<SelectedProductItem[]>('/products/selected')
}

export function updateProductSelection(
  productId: number,
  input: { selectedForSale: boolean; salePerformance?: SalePerformance | null },
): Promise<ProductSelectionResponse> {
  return apiRequest<ProductSelectionResponse>(`/products/${productId}/selection`, {
    method: 'PATCH',
    body: JSON.stringify({
      selected_for_sale: input.selectedForSale,
      sale_performance: input.salePerformance ?? null,
    }),
  })
}

export function updateSelectedProductPerformance(
  productId: number,
  salePerformance: SalePerformance | null,
): Promise<ProductSelectionResponse> {
  return apiRequest<ProductSelectionResponse>('/products/selected/performance', {
    method: 'PATCH',
    body: JSON.stringify({
      product_id: productId,
      sale_performance: salePerformance,
    }),
  })
}

export function clearSelectedProducts(): Promise<ProductSelectionClearResponse> {
  return apiRequest<ProductSelectionClearResponse>('/products/selected', {
    method: 'DELETE',
  })
}

export function fetchProducts(filters: { status?: string; pageSize?: number } = {}): Promise<{ items: any[]; total: number }> {
  return apiRequest<{ items: any[]; total: number }>(
    `/products${buildQuery({
      status: filters.status,
      page_size: filters.pageSize,
    })}`,
  )
}
