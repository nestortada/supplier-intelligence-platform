export type DashboardSummary = {
  total_suppliers: number
  valid_emails: number
  emails_sent: number
  products_uploaded: number
  products_analyzed: number
  products_recommended: number
  average_roi: number | null
  average_opportunity_score: number | null
}

export type DashboardTopOpportunity = {
  product_id: number
  product_name: string | null
  supplier_id: number | null
  category: string | null
  final_opportunity_score: number | null
  roi: number | null
  margin: number | null
  recommendation_status: string | null
}

export type DashboardSupplierPerformance = {
  supplier_id: number
  supplier_name: string | null
  recommended_products: number
}
