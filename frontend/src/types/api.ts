export type CampaignStatusValue =
  | 'draft'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'error'
  | 'pending'
  | string

export type EmailLogStatus = 'pending' | 'sent' | 'failed' | string

export type Supplier = {
  id: number
  supplier_name: string | null
  company: string | null
  email: string | null
  website: string | null
  phone: string | null
  city: string | null
  country: string | null
  category: string | null
  status: string
  is_valid_email: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export type SupplierListResponse = {
  items: Supplier[]
  total: number
  page: number
  page_size: number
}

export type SupplierUploadResponse = {
  success: boolean
  total_rows: number
  valid_emails: number
  invalid_emails: number
  duplicates_removed: number
  suppliers_created: number
  suppliers_skipped: number
}

export type SupplierDatabaseClearResponse = {
  success: boolean
  suppliers_deleted: number
  products_deleted: number
  email_logs_deleted: number
  email_campaigns_deleted: number
}

export type CampaignStatus = {
  campaign_id: number
  status: CampaignStatusValue
  total: number
  sent: number
  failed: number
  pending: number
}

export type CampaignSummary = CampaignStatus & {
  subject: string | null
  template_id: string | null
  created_at: string
  updated_at: string
}

export type CampaignListResponse = {
  items: CampaignSummary[]
  total: number
  page: number
  page_size: number
}

export type EmailLog = {
  id: number
  campaign_id: number | null
  supplier_id: number | null
  supplier_name: string | null
  supplier_company: string | null
  to_email: string | null
  status: EmailLogStatus
  provider_response: string | null
  error_message: string | null
  sent_at: string | null
}

export type EmailLogLookupType = 'none' | 'supplier' | 'campaign'

export type EmailLogFilters = {
  status: 'all' | 'sent' | 'failed'
  lookupType: EmailLogLookupType
  lookupValue: string
}

export type CreateCampaignInput = {
  subject: string
  templateId: string | null
  supplierIds: number[]
}

export type LaunchCampaignInput = CreateCampaignInput & {
  target: 'eligible' | 'specific'
}

export type SendEmailResponse = {
  success: boolean
  supplier_id: number
  email_log_id: number | null
  status: string
  error: string | null
}
