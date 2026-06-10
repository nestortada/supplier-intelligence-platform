import { buildQuery, apiRequest } from './http'
import type {
  CampaignListResponse,
  CampaignStatus,
  CreateCampaignInput,
  EmailLog,
  EmailLogFilters,
  SendEmailResponse,
  SupplierDatabaseClearResponse,
  SupplierListResponse,
  SupplierUploadResponse,
} from '../types/api'

type SupplierQuery = {
  search?: string
  hasValidEmail?: boolean
  page?: number
  pageSize?: number
}

function normalizedTemplateId(templateId: string | null | undefined): string | null {
  const normalized = templateId?.trim()
  return normalized ? normalized : null
}

function numericLookup(value: string): number | undefined {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

export function fetchSuppliers(query: SupplierQuery = {}): Promise<SupplierListResponse> {
  return apiRequest<SupplierListResponse>(
    `/suppliers${buildQuery({
      search: query.search,
      has_valid_email: query.hasValidEmail,
      page: query.page ?? 1,
      page_size: query.pageSize ?? 25,
    })}`,
  )
}

export function fetchEligibleSuppliers(query: SupplierQuery = {}): Promise<SupplierListResponse> {
  return apiRequest<SupplierListResponse>(
    `/emails/eligible-suppliers${buildQuery({
      search: query.search,
      page: query.page ?? 1,
      page_size: query.pageSize ?? 25,
    })}`,
  )
}

export function uploadSuppliersFile(file: File): Promise<SupplierUploadResponse> {
  const formData = new FormData()
  formData.set('file', file)

  return apiRequest<SupplierUploadResponse>('/suppliers/upload', {
    method: 'POST',
    body: formData,
  })
}

export function clearSupplierDatabase(): Promise<SupplierDatabaseClearResponse> {
  return apiRequest<SupplierDatabaseClearResponse>('/suppliers/database', {
    method: 'DELETE',
  })
}

export function fetchEmailLogs(filters: EmailLogFilters): Promise<EmailLog[]> {
  const supplierId = filters.lookupType === 'supplier' ? numericLookup(filters.lookupValue) : undefined
  const campaignId = filters.lookupType === 'campaign' ? numericLookup(filters.lookupValue) : undefined

  return apiRequest<EmailLog[]>(
    `/emails/logs${buildQuery({
      status: filters.status === 'all' ? undefined : filters.status,
      supplier_id: supplierId,
      campaign_id: campaignId,
    })}`,
  )
}

export function fetchCampaigns(): Promise<CampaignListResponse> {
  return apiRequest<CampaignListResponse>('/emails/campaigns?page=1&page_size=10')
}

export function fetchCampaignStatus(campaignId: number): Promise<CampaignStatus> {
  return apiRequest<CampaignStatus>(`/emails/campaigns/${campaignId}`)
}

export function cancelCampaign(campaignId: number): Promise<CampaignStatus> {
  return apiRequest<CampaignStatus>(`/emails/campaigns/${campaignId}/cancel`, {
    method: 'PATCH',
  })
}

export function createSpecificCampaign(input: CreateCampaignInput): Promise<CampaignStatus> {
  return apiRequest<CampaignStatus>('/emails/campaigns', {
    method: 'POST',
    body: JSON.stringify({
      supplier_ids: input.supplierIds,
      subject: input.subject,
      template_id: normalizedTemplateId(input.templateId),
    }),
  })
}

export function createEligibleCampaign(input: CreateCampaignInput): Promise<CampaignStatus> {
  return apiRequest<CampaignStatus>('/emails/campaigns/valid-suppliers', {
    method: 'POST',
    body: JSON.stringify({
      subject: input.subject,
      template_id: normalizedTemplateId(input.templateId),
    }),
  })
}

export function retrySupplierEmail(supplierId: number, subject: string): Promise<SendEmailResponse> {
  return apiRequest<SendEmailResponse>(`/emails/send/${supplierId}`, {
    method: 'POST',
    body: JSON.stringify({ subject }),
  })
}
