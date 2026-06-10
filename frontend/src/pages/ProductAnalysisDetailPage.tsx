import {
  AlertTriangle,
  ArrowLeft,
  ExternalLink,
  FileSpreadsheet,
  ImageIcon,
  PackageSearch,
  Radar,
  ShieldCheck,
  ShoppingCart,
  Star,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchProductAnalysisDetail } from '../api/opportunityApi'
import type { ProductAnalysisDetail } from '../types/opportunity'
import { cx } from '../utils/classNames'
import { formatDateTime, formatNumber, formatPercent } from '../utils/format'

function money(value: number | null | undefined, maximumFractionDigits = 2): string {
  if (value === null || value === undefined) {
    return 'N/D'
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits,
  }).format(value)
}

function percentFromRatio(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/D'
  }

  return formatPercent(value * 100)
}

function textValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return 'N/D'
  }

  return String(value)
}

function recommendationLabel(status: string | null | undefined): string {
  const labels: Record<string, string> = {
    buy: 'Comprar',
    review: 'Revisar',
    discard: 'Descartar',
    insufficient_data: 'Datos insuficientes',
  }

  return labels[status ?? ''] ?? 'Sin estado'
}

function recommendationTone(status: string | null | undefined): 'success' | 'primary' | 'warning' | 'danger' {
  if (status === 'buy') {
    return 'success'
  }
  if (status === 'review') {
    return 'primary'
  }
  if (status === 'discard') {
    return 'danger'
  }
  return 'warning'
}

function toneClasses(tone: ReturnType<typeof recommendationTone>): string {
  const classes = {
    success: 'border-success/30 bg-success/10 text-success',
    primary: 'border-primary/30 bg-primary/10 text-primary',
    warning: 'border-warning/30 bg-warning/10 text-warning',
    danger: 'border-danger/30 bg-danger/10 text-danger',
  }

  return classes[tone]
}

function numberFromUnknown(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value === 'string') {
    const parsed = Number(value.replace(/[$,]/g, '').trim())
    return Number.isFinite(parsed) ? parsed : null
  }

  if (Array.isArray(value)) {
    for (const item of [...value].reverse()) {
      const parsed = numberFromUnknown(item)
      if (parsed !== null) {
        return parsed
      }
    }
  }

  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    for (const key of ['value', 'price', 'count', 'sellers', 'new', 'current']) {
      const parsed = numberFromUnknown(record[key])
      if (parsed !== null) {
        return parsed
      }
    }
  }

  return null
}

function normalizeSeries(value: unknown): Array<number | null> {
  if (!Array.isArray(value)) {
    return []
  }

  return value.map((item) => numberFromUnknown(item))
}

type ChartShape = {
  linePoints: string
  areaPoints: string
}

function chartShape(series: Array<number | null>): ChartShape | null {
  const width = 1000
  const height = 220
  const padding = 20
  const valid = series
    .map((value, index) => ({ index, value }))
    .filter((point): point is { index: number; value: number } => point.value !== null && Number.isFinite(point.value))

  if (valid.length < 2 || series.length < 2) {
    return null
  }

  const values = valid.map((point) => point.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = max - min || 1
  const plotWidth = width - padding * 2
  const plotHeight = height - padding * 2

  const points = valid.map((point) => {
    const x = padding + (point.index / (series.length - 1)) * plotWidth
    const y = padding + ((max - point.value) / spread) * plotHeight
    return { x, y }
  })

  const linePoints = points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ')
  const firstPoint = points[0]
  const lastPoint = points[points.length - 1]

  return {
    linePoints,
    areaPoints: `${firstPoint.x.toFixed(1)},${height - padding} ${linePoints} ${lastPoint.x.toFixed(1)},${height - padding}`,
  }
}

export default function ProductAnalysisDetailPage() {
  const { productId } = useParams<{ productId: string }>()
  const navigate = useNavigate()
  const [detail, setDetail] = useState<ProductAnalysisDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const timeout = window.setTimeout(() => {
      const parsedProductId = Number(productId)

      if (!Number.isInteger(parsedProductId) || parsedProductId <= 0) {
        if (active) {
          setDetail(null)
          setError('Producto invalido.')
          setLoading(false)
        }
        return
      }

      setLoading(true)
      setError(null)

      fetchProductAnalysisDetail(parsedProductId)
        .then((response) => {
          if (active) {
            setDetail(response)
          }
        })
        .catch((caught) => {
          if (active) {
            setDetail(null)
            setError(caught instanceof Error ? caught.message : 'No se pudo cargar el analisis.')
          }
        })
        .finally(() => {
          if (active) {
            setLoading(false)
          }
        })
    }, 0)

    return () => {
      active = false
      window.clearTimeout(timeout)
    }
  }, [productId])

  const sellersHistory = useMemo(() => normalizeSeries(detail?.sellers_history), [detail?.sellers_history])

  if (loading) {
    return (
      <div className="mx-auto max-w-[1440px] space-y-6">
        <div className="h-40 animate-pulse rounded-xl bg-white/10" />
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
          <div className="h-96 animate-pulse rounded-xl bg-white/10" />
          <div className="h-96 animate-pulse rounded-xl bg-white/10" />
          <div className="h-96 animate-pulse rounded-xl bg-white/10" />
        </div>
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="mx-auto max-w-[900px] space-y-6">
        <button
          className="inline-flex items-center gap-2 rounded-lg border border-outline/40 px-4 py-2.5 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-primary"
          onClick={() => navigate('/ranking')}
          type="button"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al ranking
        </button>
        <div className="glass-panel rounded-xl border border-danger/20 p-6">
          <div className="flex items-start gap-3 text-danger">
            <AlertTriangle className="mt-1 h-5 w-5 shrink-0" />
            <div>
              <h1 className="font-display text-2xl font-semibold">No se pudo cargar el detalle</h1>
              <p className="mt-2 text-sm text-muted">{error || 'Analisis no disponible.'}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const productTitle = detail.amazon_data?.amazon_title || detail.product.product_name || 'Producto sin nombre'
  const tone = recommendationTone(detail.recommendation.status)
  const score = detail.scores.final_opportunity_score ?? 0
  const amazonPrice =
    detail.financial_analysis.amazon_price ??
    detail.amazon_data?.current_price ??
    detail.amazon_data?.buybox_price ??
    detail.amazon_data?.amazon_price ??
    detail.amazon_data?.list_price ??
    null

  return (
    <div className="mx-auto max-w-[1440px] space-y-6">
      <header className="glass-panel relative overflow-hidden rounded-xl p-5 lg:p-6">
        <div className="absolute left-0 top-0 h-full w-1 bg-primary shadow-glow" />
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <button
              className="mb-4 inline-flex items-center gap-2 rounded-lg border border-outline/40 px-3 py-2 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-primary"
              onClick={() => navigate('/ranking')}
              type="button"
            >
              <ArrowLeft className="h-4 w-4" />
              Volver al ranking
            </button>
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <span className={cx('inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold', toneClasses(tone))}>
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                {recommendationLabel(detail.recommendation.status)}
              </span>
              {detail.amazon_data?.asin ? <span className="font-mono text-sm text-muted">ASIN: {detail.amazon_data.asin}</span> : null}
              <span className="text-sm text-muted">Producto ID: {detail.product.id}</span>
            </div>
            <h1 className="max-w-5xl font-display text-3xl font-semibold leading-tight text-text md:text-4xl">{productTitle}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-muted">
              {detail.amazon_data?.rating ? (
                <span className="inline-flex items-center gap-1">
                  <Star className="h-4 w-4 fill-warning text-warning" />
                  <span className="font-semibold text-text">{detail.amazon_data.rating}</span>
                  {detail.amazon_data.reviews_count ? <span>({formatNumber(detail.amazon_data.reviews_count)} reviews)</span> : null}
                </span>
              ) : null}
              <span className="inline-flex items-center gap-1">
                <ShieldCheck className="h-4 w-4 text-primary" />
                {detail.recommendation.reason || 'Sin explicacion disponible.'}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            {detail.amazon_data?.amazon_url ? (
              <a
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-[#24005f] shadow-glow transition hover:bg-primary/90"
                href={detail.amazon_data.amazon_url}
                rel="noreferrer"
                target="_blank"
              >
                <ShoppingCart className="h-4 w-4" />
                Ver en Amazon
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            ) : null}
          </div>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        <ProductOverviewCard detail={detail} />
        <UnitEconomicsCard amazonPrice={amazonPrice} detail={detail} />
        <OpportunityMatrixCard detail={detail} score={score} />
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        <RiskIntelligenceCard risks={detail.recommendation.risks.length > 0 ? detail.recommendation.risks : detail.risks} />
        <HistoryChart
          priceHistory={detail.price_history}
          priceMetrics={detail.price_history_metrics}
          sellersHistory={sellersHistory}
        />
      </section>
    </div>
  )
}

function ProductOverviewCard({ detail }: { detail: ProductAnalysisDetail }) {
  return (
    <article className="glass-panel rounded-xl p-5 xl:col-span-4">
      <SectionTitle icon={<PackageSearch className="h-4 w-4" />} title="Product Overview" />
      <div className="mt-5 aspect-square overflow-hidden rounded-lg border border-outline/30 bg-white/5 p-4">
        {detail.amazon_data?.image_url ? (
          <img
            alt={detail.amazon_data.amazon_title ?? detail.product.product_name ?? 'Producto Amazon'}
            className="h-full w-full object-contain"
            src={detail.amazon_data.image_url}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center rounded-lg bg-primary/10 text-primary">
            <ImageIcon className="h-14 w-14" />
          </div>
        )}
      </div>
      <div className="mt-5 space-y-1">
        <InfoRow label="Marca" value={textValue(detail.product.brand)} />
        <InfoRow label="Categoria" value={textValue(detail.product.category)} />
        <InfoRow label="SKU" value={textValue(detail.product.sku)} />
        <InfoRow label="UPC" value={textValue(detail.product.upc)} />
        <InfoRow label="EAN" value={textValue(detail.product.ean)} />
        <InfoRow label="GTIN" value={textValue(detail.product.gtin)} />
        <InfoRow label="Case qty" value={textValue(detail.product.case_quantity)} />
        <InfoRow label="Status" value={textValue(detail.product.status)} />
        <InfoRow label="Actualizado" value={formatDateTime(detail.product.updated_at)} />
      </div>
    </article>
  )
}

function UnitEconomicsCard({ amazonPrice, detail }: { amazonPrice: number | null; detail: ProductAnalysisDetail }) {
  const financial = detail.financial_analysis

  return (
    <article className="glass-panel rounded-xl p-5 xl:col-span-4">
      <SectionTitle icon={<Wallet className="h-4 w-4" />} title="Unit Economics" />
      <div className="mt-5 flex justify-center">
        <div className="flex h-44 w-44 flex-col items-center justify-center rounded-full border-[12px] border-primary/40 bg-background/70 text-center shadow-glow">
          <span className="text-xs font-semibold uppercase text-muted">Sale Price</span>
          <span className="mt-1 font-display text-3xl font-bold text-text">{money(amazonPrice)}</span>
        </div>
      </div>
      <div className="mt-6 grid grid-cols-2 gap-3">
        <MetricTile label="Supplier cost" value={money(financial.supplier_cost)} />
        <MetricTile label="Amazon price" value={money(amazonPrice)} />
        <MetricTile label="Referral fee" value={money(financial.referral_fee)} />
        <MetricTile label="FBA fee" value={money(financial.fba_fee)} />
        <MetricTile label="Shipping" value={money(financial.shipping_cost)} />
        <MetricTile label="Prep + other" value={money((financial.prep_fee ?? 0) + (financial.other_costs ?? 0))} />
        <MetricTile label="Total cost" value={money(financial.total_cost)} />
        <MetricTile label="Net profit" tone={financial.net_profit && financial.net_profit > 0 ? 'success' : 'danger'} value={money(financial.net_profit)} />
        <MetricTile label="ROI" tone="primary" value={percentFromRatio(financial.roi)} />
        <MetricTile label="Margin" tone="success" value={percentFromRatio(financial.margin)} />
      </div>
    </article>
  )
}

function OpportunityMatrixCard({ detail, score }: { detail: ProductAnalysisDetail; score: number }) {
  return (
    <article className="glass-panel rounded-xl p-5 xl:col-span-4">
      <SectionTitle icon={<Radar className="h-4 w-4" />} title="Opportunity Matrix" />
      <div className="mt-5 rounded-xl border border-primary/20 bg-primary/10 p-5 text-center">
        <div className="mx-auto flex h-28 w-28 items-center justify-center rounded-full border border-primary/40 bg-background/70 shadow-glow">
          <span className="font-display text-4xl font-bold text-primary">{Math.round(score)}</span>
        </div>
        <p className="mt-3 text-sm font-semibold text-text">Final Opportunity Score</p>
        <p className="mt-1 text-xs text-muted">Actualizado {formatDateTime(detail.product.updated_at)}</p>
      </div>
      <div className="mt-5 space-y-4">
        <ScoreRow label="Profitability" value={detail.scores.profitability_score} />
        <ScoreRow label="ROI" value={detail.scores.roi_score} />
        <ScoreRow label="Sales" value={detail.scores.sales_score} />
        <ScoreRow label="Price stability" value={detail.scores.price_stability_score} />
        <ScoreRow label="Sellers" value={detail.scores.sellers_score} />
        <ScoreRow label="Data quality" value={detail.scores.data_quality_score} />
      </div>
    </article>
  )
}

function RiskIntelligenceCard({ risks }: { risks: string[] }) {
  return (
    <article className="glass-panel rounded-xl border-l-4 border-l-warning p-5 xl:col-span-4">
      <SectionTitle icon={<AlertTriangle className="h-4 w-4 text-warning" />} title="Risk Intelligence" />
      {risks.length > 0 ? (
        <ul className="mt-5 space-y-3">
          {risks.map((risk) => (
            <li className="flex items-start gap-3 rounded-lg border border-warning/20 bg-warning/10 p-3 text-sm text-text" key={risk}>
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-warning" />
              <span>{risk}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-5 rounded-lg border border-success/20 bg-success/10 p-4 text-sm text-success">
          No hay riesgos detectados para este producto.
        </div>
      )}
    </article>
  )
}

function HistoryChart({
  priceHistory,
  priceMetrics,
  sellersHistory,
}: {
  priceHistory: Array<number | null>
  priceMetrics: ProductAnalysisDetail['price_history_metrics']
  sellersHistory: Array<number | null>
}) {
  const priceShape = chartShape(priceHistory)
  const sellersShape = chartShape(sellersHistory)
  const priceValues = priceHistory.filter((value): value is number => value !== null && Number.isFinite(value))
  const hasChart = Boolean(priceShape || sellersShape)
  const maxPrice = priceValues.length > 0 ? Math.max(...priceValues) : null
  const midPrice = priceValues.length > 0 ? (Math.max(...priceValues) + Math.min(...priceValues)) / 2 : null
  const minPrice = priceValues.length > 0 ? Math.min(...priceValues) : null

  return (
    <article className="glass-panel rounded-xl p-5 xl:col-span-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle icon={<TrendingUp className="h-4 w-4" />} title="Price & Competition History" />
        <div className="flex flex-wrap gap-4 text-xs text-muted">
          <span className="inline-flex items-center gap-2">
            <span className="h-1 w-5 rounded-full bg-primary" />
            Buy Box Price
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-1 w-5 rounded-full border border-muted" />
            New Sellers
          </span>
        </div>
      </div>

      {hasChart ? (
        <div className="mt-6">
          <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricTile label="Avg price" value={money(priceMetrics.average_price)} />
            <MetricTile label="Min price" value={money(priceMetrics.min_price)} />
            <MetricTile label="Max price" value={money(priceMetrics.max_price)} />
            <MetricTile label="Price changes" value={formatNumber(priceMetrics.number_of_price_changes)} />
          </div>
          <div className="relative h-72 rounded-xl border border-outline/30 bg-background/50 p-4">
            <div className="absolute bottom-10 left-4 top-4 flex flex-col justify-between text-[10px] font-semibold text-muted">
              <span>{money(maxPrice, 0)}</span>
              <span>{money(midPrice, 0)}</span>
              <span>{money(minPrice, 0)}</span>
            </div>
            <svg className="h-full w-full pl-12" preserveAspectRatio="none" viewBox="0 0 1000 220">
              <defs>
                <linearGradient id="priceHistoryGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#d0bcff" stopOpacity="0.28" />
                  <stop offset="100%" stopColor="#d0bcff" stopOpacity="0" />
                </linearGradient>
              </defs>
              <line stroke="rgba(255,255,255,0.12)" strokeDasharray="6 6" x1="20" x2="980" y1="55" y2="55" />
              <line stroke="rgba(255,255,255,0.12)" strokeDasharray="6 6" x1="20" x2="980" y1="110" y2="110" />
              <line stroke="rgba(255,255,255,0.12)" strokeDasharray="6 6" x1="20" x2="980" y1="165" y2="165" />
              {priceShape ? <polygon fill="url(#priceHistoryGradient)" points={priceShape.areaPoints} /> : null}
              {priceShape ? (
                <polyline fill="none" points={priceShape.linePoints} stroke="#d0bcff" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
              ) : null}
              {sellersShape ? (
                <polyline
                  fill="none"
                  points={sellersShape.linePoints}
                  stroke="#cbc3d7"
                  strokeDasharray="10 8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="3"
                />
              ) : null}
            </svg>
          </div>
        </div>
      ) : (
        <div className="mt-6 flex min-h-56 flex-col items-center justify-center rounded-xl border border-outline/30 bg-background/50 p-6 text-center">
          <FileSpreadsheet className="h-10 w-10 text-primary" />
          <h3 className="mt-4 font-display text-xl font-semibold text-text">Sin historial suficiente</h3>
          <p className="mt-2 max-w-lg text-sm text-muted">Este producto no tiene suficientes puntos de precio o sellers para graficar.</p>
        </div>
      )}
    </article>
  )
}

function SectionTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
      {icon}
      {title}
    </h2>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-outline/20 py-2 text-sm">
      <span className="text-muted">{label}</span>
      <span className="min-w-0 truncate text-right font-semibold text-text">{value}</span>
    </div>
  )
}

function MetricTile({ label, tone, value }: { label: string; tone?: 'success' | 'danger' | 'primary'; value: string }) {
  return (
    <div className="rounded-lg border border-outline/30 bg-background/50 p-3">
      <div className="mb-1 flex items-center gap-2">
        <span
          className={cx(
            'h-2 w-2 rounded-full',
            tone === 'success' && 'bg-success',
            tone === 'danger' && 'bg-danger',
            tone === 'primary' && 'bg-primary',
            !tone && 'bg-muted',
          )}
        />
        <span className="text-xs font-semibold uppercase text-muted">{label}</span>
      </div>
      <p className={cx('text-base font-bold text-text', tone === 'success' && 'text-success', tone === 'danger' && 'text-danger', tone === 'primary' && 'text-primary')}>
        {value}
      </p>
    </div>
  )
}

function ScoreRow({ label, value }: { label: string; value: number | null }) {
  const score = value ?? 0
  const width = Math.max(4, Math.min(100, score))

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-semibold text-text">{label}</span>
        <span className="text-muted">{value === null ? 'N/D' : `${Math.round(value)}/100`}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full bg-primary shadow-glow" style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}
