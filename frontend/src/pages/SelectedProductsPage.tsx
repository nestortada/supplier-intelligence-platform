import {
  BarChart3,
  CheckSquare,
  ExternalLink,
  Loader2,
  PackageOpen,
  RefreshCcw,
  Trash2,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  clearSelectedProducts,
  fetchSelectedProducts,
  updateProductSelection,
  updateSelectedProductPerformance,
} from '../api/opportunityApi'
import ConfirmDialog from '../components/ConfirmDialog'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { useToast } from '../hooks/useToast'
import type { SalePerformance, SelectedProductItem } from '../types/opportunity'
import { cx } from '../utils/classNames'
import { formatDateTime, formatNumber, formatPercent } from '../utils/format'

const performanceLabels: Record<SalePerformance, string> = {
  high: 'Alto',
  medium: 'Medio',
  low: 'Bajo',
}

const selectedProductsRealtimeEvents = [
  'product.selection_updated',
  'products.selection_cleared',
  'products.updated',
  'products.deleted',
  'product.deleted',
  'webhook.received',
]

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/D'
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value)
}

function percentFromRatio(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/D'
  }

  return formatPercent(value * 100)
}

function recommendationLabel(status: string | null | undefined): string {
  const labels: Record<string, string> = {
    buy: 'Comprar',
    discard: 'Descartar',
    enriched: 'Enriquecido',
    insufficient_data: 'Datos insuficientes',
    pending_analysis: 'Pendiente',
    review: 'Revisar',
  }

  return labels[status ?? ''] ?? 'Sin estado'
}

function performanceTone(performance: SalePerformance | null): string {
  if (performance === 'high') {
    return 'border-success/30 bg-success/10 text-success'
  }
  if (performance === 'medium') {
    return 'border-warning/30 bg-warning/10 text-warning'
  }
  if (performance === 'low') {
    return 'border-danger/30 bg-danger/10 text-danger'
  }
  return 'border-outline/40 bg-white/[0.03] text-muted'
}

export default function SelectedProductsPage() {
  const [items, setItems] = useState<SelectedProductItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updatingPerformanceId, setUpdatingPerformanceId] = useState<number | null>(null)
  const [removingProductId, setRemovingProductId] = useState<number | null>(null)
  const [clearDialogOpen, setClearDialogOpen] = useState(false)
  const [clearing, setClearing] = useState(false)
  const { addToast } = useToast()

  const loadSelectedProducts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchSelectedProducts()
      setItems(response)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los productos seleccionados.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadSelectedProducts()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadSelectedProducts])

  useRealtimeRefresh(selectedProductsRealtimeEvents, () => {
    void loadSelectedProducts()
  })

  const summary = useMemo(() => {
    const totalSales = items.reduce((total, item) => total + (item.amazon_data?.estimated_sales ?? 0), 0)
    const highPerformance = items.filter((item) => item.sale_performance === 'high').length
    const averageRoi =
      items.length > 0
        ? items.reduce((total, item) => total + (item.analysis?.roi ?? 0), 0) / items.length
        : null

    return { averageRoi, highPerformance, totalSales }
  }, [items])

  const handlePerformanceChange = useCallback(
    async (item: SelectedProductItem, performance: SalePerformance | null) => {
      setUpdatingPerformanceId(item.product.id)
      try {
        const response = await updateSelectedProductPerformance(item.product.id, performance)
        setItems((current) =>
          current.map((currentItem) =>
            currentItem.product.id === item.product.id
              ? {
                  ...currentItem,
                  product: response.product,
                  sale_performance: response.product.sale_performance,
                }
              : currentItem,
          ),
        )
        addToast({
          tone: 'success',
          title: 'Performance actualizada',
          message: item.amazon_data?.amazon_title || item.product.product_name || `Producto ${item.product.id}`,
        })
      } catch (caught) {
        addToast({
          tone: 'error',
          title: 'No se pudo guardar',
          message: caught instanceof Error ? caught.message : 'Intenta de nuevo.',
        })
      } finally {
        setUpdatingPerformanceId(null)
      }
    },
    [addToast],
  )

  const handleRemoveProduct = useCallback(
    async (item: SelectedProductItem) => {
      setRemovingProductId(item.product.id)
      try {
        await updateProductSelection(item.product.id, { selectedForSale: false })
        setItems((current) => current.filter((currentItem) => currentItem.product.id !== item.product.id))
        addToast({
          tone: 'info',
          title: 'Producto removido',
          message: item.amazon_data?.amazon_title || item.product.product_name || `Producto ${item.product.id}`,
        })
      } catch (caught) {
        addToast({
          tone: 'error',
          title: 'No se pudo remover',
          message: caught instanceof Error ? caught.message : 'Intenta de nuevo.',
        })
      } finally {
        setRemovingProductId(null)
      }
    },
    [addToast],
  )

  const handleClearSelected = useCallback(async () => {
    setClearing(true)
    try {
      const response = await clearSelectedProducts()
      setItems([])
      setClearDialogOpen(false)
      addToast({
        tone: 'success',
        title: 'Seleccion limpiada',
        message: `${response.updated} productos removidos de seleccionados.`,
      })
    } catch (caught) {
      addToast({
        tone: 'error',
        title: 'No se pudo limpiar',
        message: caught instanceof Error ? caught.message : 'Intenta de nuevo.',
      })
    } finally {
      setClearing(false)
    }
  }, [addToast])

  return (
    <div className="mx-auto max-w-[1440px] space-y-6">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
            <CheckSquare className="h-4 w-4" />
            Productos en venta
          </div>
          <h1 className="font-display text-3xl font-semibold text-text md:text-4xl">Seleccionados</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted md:text-base">
            Productos marcados desde el ranking para seguimiento de venta en Amazon.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-outline/40 px-4 py-2.5 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-primary"
            onClick={() => void loadSelectedProducts()}
            type="button"
          >
            <RefreshCcw className="h-4 w-4" />
            Actualizar
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-2.5 text-sm font-semibold text-danger transition hover:bg-danger/20 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={items.length === 0 || clearing}
            onClick={() => setClearDialogOpen(true)}
            type="button"
          >
            {clearing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            Limpiar seleccion
          </button>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <SummaryCard icon={<PackageOpen className="h-5 w-5" />} label="Productos" value={formatNumber(items.length)} />
        <SummaryCard icon={<BarChart3 className="h-5 w-5" />} label="Ventas mes" value={formatNumber(summary.totalSales)} />
        <SummaryCard icon={<CheckSquare className="h-5 w-5" />} label="Alto performance" value={formatNumber(summary.highPerformance)} />
      </section>

      {summary.averageRoi !== null ? (
        <div className="rounded-xl border border-success/20 bg-success/10 px-4 py-3 text-sm font-semibold text-success">
          ROI promedio estimado: {percentFromRatio(summary.averageRoi)}
        </div>
      ) : null}

      {error ? <div className="rounded-xl border border-danger/20 bg-danger/10 p-4 text-sm text-danger">{error}</div> : null}

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div className="h-36 animate-pulse rounded-xl bg-white/10" key={index} />
          ))}
        </div>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <section className="glass-panel rounded-xl p-8 text-center">
          <PackageOpen className="mx-auto h-10 w-10 text-primary" />
          <h2 className="mt-4 font-display text-xl font-semibold text-text">Sin productos seleccionados</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-muted">
            Marca productos desde la pagina de Productos para verlos aqui y registrar su performance.
          </p>
          <Link
            className="mt-5 inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-[#24005f] transition hover:bg-primary/90"
            to="/ranking"
          >
            Ir a Productos
          </Link>
        </section>
      ) : null}

      {!loading && items.length > 0 ? (
        <section className="space-y-4">
          {items.map((item) => (
            <SelectedProductRow
              item={item}
              key={item.product.id}
              onPerformanceChange={handlePerformanceChange}
              onRemove={handleRemoveProduct}
              removing={removingProductId === item.product.id}
              updatingPerformance={updatingPerformanceId === item.product.id}
            />
          ))}
        </section>
      ) : null}

      <ConfirmDialog
        confirmLabel="Limpiar seleccion"
        loading={clearing}
        message="Esto solo quitara los productos de la pagina Seleccionados. No borra productos, Amazon data ni analisis."
        onCancel={() => setClearDialogOpen(false)}
        onConfirm={() => void handleClearSelected()}
        open={clearDialogOpen}
        title="Limpiar productos seleccionados"
      />
    </div>
  )
}

function SummaryCard({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <article className="glass-panel glow-border rounded-xl p-5">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/15 text-primary shadow-glow">{icon}</div>
        <div>
          <p className="text-xs font-semibold uppercase text-muted">{label}</p>
          <p className="font-display text-2xl font-bold text-text">{value}</p>
        </div>
      </div>
    </article>
  )
}

function SelectedProductRow({
  item,
  onPerformanceChange,
  onRemove,
  removing,
  updatingPerformance,
}: {
  item: SelectedProductItem
  onPerformanceChange: (item: SelectedProductItem, performance: SalePerformance | null) => void
  onRemove: (item: SelectedProductItem) => void
  removing: boolean
  updatingPerformance: boolean
}) {
  const amazonPrice =
    item.amazon_data?.current_price ??
    item.amazon_data?.buybox_price ??
    item.amazon_data?.amazon_price ??
    item.amazon_data?.list_price ??
    null
  const productTitle = item.amazon_data?.amazon_title || item.product.product_name || 'Producto sin nombre'

  return (
    <article className="glass-panel rounded-xl p-4 transition hover:border-primary/30 hover:bg-white/[0.03] lg:p-5">
      <div className="grid gap-5 lg:grid-cols-[6rem_minmax(14rem,1.4fr)_0.7fr_0.7fr_0.7fr_0.7fr_auto] lg:items-center">
        <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-xl border border-outline/40 bg-background/70">
          {item.amazon_data?.image_url ? (
            <img alt={productTitle} className="h-full w-full object-contain p-2" src={item.amazon_data.image_url} />
          ) : (
            <PackageOpen className="h-9 w-9 text-primary" />
          )}
        </div>

        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className={cx('rounded-full border px-2.5 py-1 text-xs font-semibold', performanceTone(item.sale_performance))}>
              {item.sale_performance ? performanceLabels[item.sale_performance] : 'Sin clasificar'}
            </span>
            <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
              {recommendationLabel(item.recommendation.status)}
            </span>
          </div>
          <h2 className="line-clamp-2 font-display text-lg font-semibold leading-tight text-text">{productTitle}</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
            {item.amazon_data?.amazon_url ? (
              <a className="inline-flex items-center gap-1 transition hover:text-primary" href={item.amazon_data.amazon_url} rel="noreferrer" target="_blank">
                <ExternalLink className="h-3.5 w-3.5" />
                Amazon
              </a>
            ) : null}
            {item.amazon_data?.asin ? <span>ASIN: {item.amazon_data.asin}</span> : null}
            {item.product.sku ? <span>SKU: {item.product.sku}</span> : null}
            <span>Seleccionado {formatDateTime(item.selected_at)}</span>
          </div>
        </div>

        <Metric label="Est. ROI" tone="success" value={percentFromRatio(item.analysis?.roi)} />
        <Metric label="Ventas mes" value={formatNumber(item.amazon_data?.estimated_sales ?? 0)} />
        <Metric label="Precio Amazon" value={money(amazonPrice)} />
        <Metric label="Costo" value={money(item.product.supplier_cost)} />

        <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
          <label className="min-w-44 flex-1">
            <span className="mb-2 block text-[10px] font-semibold uppercase text-muted">Performance</span>
            <select
              className="field py-2 text-sm"
              disabled={updatingPerformance}
              onChange={(event) => {
                const value = event.target.value
                onPerformanceChange(item, value ? (value as SalePerformance) : null)
              }}
              value={item.sale_performance ?? ''}
            >
              <option value="">Sin clasificar</option>
              <option value="high">Alto</option>
              <option value="medium">Medio</option>
              <option value="low">Bajo</option>
            </select>
          </label>
          <button
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-3 text-sm font-semibold text-danger transition hover:bg-danger/20 disabled:cursor-not-allowed disabled:opacity-60 lg:w-10 lg:px-0"
            disabled={removing}
            onClick={() => onRemove(item)}
            title="Quitar de seleccionados"
            type="button"
          >
            {removing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            <span className="lg:sr-only">Quitar</span>
          </button>
        </div>
      </div>
    </article>
  )
}

function Metric({ label, tone, value }: { label: string; tone?: 'success' | 'danger'; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-semibold uppercase text-muted">{label}</p>
      <p className={cx('mt-1 truncate text-sm font-bold text-text', tone === 'success' && 'text-success', tone === 'danger' && 'text-danger')}>
        {value}
      </p>
    </div>
  )
}
