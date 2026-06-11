export type CatalogUploadResponse = {
  success: boolean
  products_detected: number
  products_created: number
  duplicates: number
  missing_upc: number
  errors: number
}

export type ProductJobResponse = {
  success: boolean
  job_id: number
  total_items: number
  status: string
}

export type ProductDatabaseClearResponse = {
  success: boolean
  products_deleted: number
  amazon_data_deleted: number
  analyses_deleted: number
}

export type SalePerformance = 'high' | 'medium' | 'low'

export type ProductSelectionResponse = {
  success: boolean
  product: ProductPayload
}

export type ProductSelectionClearResponse = {
  success: boolean
  updated: number
}

export type JobStatus = {
  job_id: number
  type: string
  status: string
  progress: number
  total_items: number
  processed_items: number
  failed_items: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export type ProductPayload = {
  id: number
  supplier_id: number | null
  product_name: string | null
  description: string | null
  sku: string | null
  upc: string | null
  ean: string | null
  gtin: string | null
  brand: string | null
  category: string | null
  supplier_cost: number | null
  case_quantity: number | null
  uom: string | null
  status: string
  selected_for_sale: boolean
  sale_performance: SalePerformance | null
  selected_at: string | null
  created_at: string
  updated_at: string
}

export type AmazonDataPayload = {
  id: number
  product_id: number
  asin: string | null
  amazon_title: string | null
  amazon_url: string | null
  image_url: string | null
  current_price: number | null
  buybox_price: number | null
  amazon_price: number | null
  list_price: number | null
  currency: string | null
  rating: number | null
  reviews_count: number | null
  sellers_count: number | null
  estimated_sales: number | null
  price_history_json: string | null
  sellers_history_json: string | null
  captured_at: string
}

export type ProductAnalysisPayload = {
  id: number
  product_id: number
  net_profit: number | null
  margin: number | null
  roi: number | null
  profitability_score: number | null
  roi_score: number | null
  sales_score: number | null
  price_stability_score: number | null
  sellers_score: number | null
  data_quality_score: number | null
  final_opportunity_score: number | null
  recommendation_status: string | null
  recommendation_reason: string | null
  risks: string[]
  analyzed_at: string
}

export type RankingScores = {
  profitability_score: number | null
  roi_score: number | null
  sales_score: number | null
  price_stability_score: number | null
  sellers_score: number | null
  data_quality_score: number | null
  final_opportunity_score: number | null
}

export type RecommendationPayload = {
  status: string | null
  reason: string | null
  risks: string[]
}

export type RankingItem = {
  product: ProductPayload
  amazon_data: AmazonDataPayload | null
  analysis: ProductAnalysisPayload
  scores: RankingScores
  recommendation: RecommendationPayload
}

export type SelectedProductItem = {
  product: ProductPayload
  amazon_data: AmazonDataPayload | null
  analysis: ProductAnalysisPayload | null
  scores: RankingScores | null
  recommendation: RecommendationPayload
  sale_performance: SalePerformance | null
  selected_at: string | null
}

export type FinancialAnalysisPayload = {
  supplier_cost: number | null
  amazon_price: number | null
  referral_fee: number | null
  fba_fee: number | null
  shipping_cost: number | null
  prep_fee: number | null
  other_costs: number | null
  total_cost: number | null
  net_profit: number | null
  margin: number | null
  roi: number | null
}

export type PriceHistoryMetrics = {
  has_price_history: boolean
  average_price: number | null
  min_price: number | null
  max_price: number | null
  standard_deviation: number | null
  coefficient_of_variation: number | null
  price_drop_30_days: number | null
  number_of_price_changes: number
  null_price_count: number
  null_price_rate: number
}

export type ProductAnalysisDetail = {
  product: ProductPayload
  amazon_data: AmazonDataPayload | null
  financial_analysis: FinancialAnalysisPayload
  scores: RankingScores
  recommendation: RecommendationPayload
  risks: string[]
  price_history: Array<number | null>
  price_history_metrics: PriceHistoryMetrics
  sellers_history: unknown
}

export type RankingFilters = {
  minScore: number
  recommendation: 'all' | 'buy' | 'review' | 'discard' | 'insufficient_data'
  minRoi: number
  minMargin: number
  minSales: number
  sellersMin: string
  sellersMax: string
}
