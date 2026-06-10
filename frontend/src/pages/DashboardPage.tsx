import {
  ArrowRight,
  BarChart3,
  Cpu,
  Factory,
  Mail,
  PackageOpen,
  Percent,
  Radar,
  RefreshCcw,
  ShoppingCart,
  Target,
  UploadCloud,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchDashboardSummary,
  fetchDashboardSupplierPerformance,
  fetchDashboardTopOpportunities,
} from '../api/dashboardApi'
import type { DashboardSupplierPerformance, DashboardSummary, DashboardTopOpportunity } from '../types/dashboard'
import { cx } from '../utils/classNames'
import { formatNumber } from '../utils/format'

type DashboardData = {
  summary: DashboardSummary
  opportunities: DashboardTopOpportunity[]
  suppliers: DashboardSupplierPerformance[]
}

type Tone = 'primary' | 'success' | 'warning' | 'danger'

const decimalFormatter = new Intl.NumberFormat('es-CO', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0,
})

function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/D'
  }

  return `${decimalFormatter.format(value * 100)}%`
}

function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/D'
  }

  return `${Math.round(value)}`
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

function recommendationTone(status: string | null | undefined): Tone {
  if (status === 'buy') {
    return 'success'
  }
  if (status === 'review') {
    return 'warning'
  }
  if (status === 'discard') {
    return 'danger'
  }
  return 'primary'
}

function toneClass(tone: Tone): string {
  const classes = {
    danger: 'border-danger/25 bg-danger/10 text-danger',
    primary: 'border-primary/25 bg-primary/10 text-primary',
    success: 'border-success/25 bg-success/10 text-success',
    warning: 'border-warning/25 bg-warning/10 text-warning',
  }

  return classes[tone]
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const [summary, opportunities, suppliers] = await Promise.all([
        fetchDashboardSummary(),
        fetchDashboardTopOpportunities(10),
        fetchDashboardSupplierPerformance(),
      ])
      setData({ summary, opportunities, suppliers })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo cargar el dashboard.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadDashboard()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadDashboard])

  const supplierNames = new Map<number, string>()
  data?.suppliers.forEach((supplier) => {
    if (supplier.supplier_name) {
      supplierNames.set(supplier.supplier_id, supplier.supplier_name)
    }
  })
  const maxSupplierVolume = data?.suppliers.length
    ? Math.max(...data.suppliers.map((supplier) => supplier.recommended_products))
    : 0

  return (
    <div className="mx-auto w-[calc(100vw-3rem)] max-w-[1440px] min-w-0 space-y-6 overflow-x-hidden sm:w-auto">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-success/20 bg-success/10 px-3 py-1 text-sm font-semibold text-success">
            <span className="h-2 w-2 rounded-full bg-success shadow-[0_0_10px_rgba(78,222,163,0.8)]" />
            Sistema conectado
          </div>
          <h1 className="font-display text-3xl font-semibold text-text md:text-4xl">Resumen ejecutivo</h1>
          <p className="mt-2 max-w-[20rem] break-words text-sm text-muted sm:max-w-3xl md:text-base">
            Vista central de proveedores, campanas, productos analizados y oportunidades de compra listas para priorizar.
          </p>
        </div>

        <button
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-outline/40 px-4 py-2.5 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-primary"
          onClick={() => void loadDashboard()}
          type="button"
        >
          <RefreshCcw className={cx('h-4 w-4', loading && 'animate-spin')} />
          Actualizar
        </button>
      </header>

      {error ? (
        <section className="rounded-xl border border-danger/20 bg-danger/10 p-4 text-sm text-danger">
          {error}
        </section>
      ) : null}

      {loading && !data ? <DashboardSkeleton /> : null}

      {data ? (
        <>
          <section className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
            <KpiCard
              icon={<Factory className="h-5 w-5" />}
              label="Proveedores"
              meta={`${formatNumber(data.summary.valid_emails)} emails validos`}
              tone="primary"
              value={formatNumber(data.summary.total_suppliers)}
            />
            <KpiCard
              icon={<Mail className="h-5 w-5" />}
              label="Emails enviados"
              meta="Outreach acumulado"
              tone="success"
              value={formatNumber(data.summary.emails_sent)}
            />
            <KpiCard
              icon={<UploadCloud className="h-5 w-5" />}
              label="Productos cargados"
              meta="Catalogos importados"
              tone="warning"
              value={formatNumber(data.summary.products_uploaded)}
            />
            <KpiCard
              icon={<Cpu className="h-5 w-5" />}
              label="Analizados"
              meta="Con score calculado"
              tone="primary"
              value={formatNumber(data.summary.products_analyzed)}
            />
            <KpiCard
              icon={<ShoppingCart className="h-5 w-5" />}
              label="Oportunidades"
              meta="Recomendacion comprar"
              tone="success"
              value={formatNumber(data.summary.products_recommended)}
            />
            <KpiCard
              icon={<Percent className="h-5 w-5" />}
              label="ROI promedio"
              meta="Sobre analisis recientes"
              tone="warning"
              value={formatRatio(data.summary.average_roi)}
            />
            <KpiCard
              icon={<Radar className="h-5 w-5" />}
              label="Score promedio"
              meta="/100"
              tone="primary"
              value={formatScore(data.summary.average_opportunity_score)}
            />
          </section>

          <section className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-3">
            <TopOpportunitiesTable opportunities={data.opportunities} supplierNames={supplierNames} />
            <SupplierVolumeChart maxValue={maxSupplierVolume} suppliers={data.suppliers} />
          </section>
        </>
      ) : null}
    </div>
  )
}

function KpiCard({
  icon,
  label,
  meta,
  tone,
  value,
}: {
  icon: ReactNode
  label: string
  meta: string
  tone: Tone
  value: string
}) {
  return (
    <article className="glass-panel glow-border min-w-0 overflow-hidden rounded-xl p-4 transition hover:bg-white/[0.04]">
      <div className="flex min-h-36 flex-col justify-between gap-4">
        <div
          className={cx(
            'flex h-10 w-10 items-center justify-center rounded-lg',
            tone === 'primary' && 'bg-primary/15 text-primary',
            tone === 'success' && 'bg-success/15 text-success',
            tone === 'warning' && 'bg-warning/15 text-warning',
            tone === 'danger' && 'bg-danger/15 text-danger',
          )}
        >
          {icon}
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted">{label}</p>
          <p className={cx('mt-1 font-display text-3xl font-semibold', tone === 'success' ? 'text-success' : 'text-text')}>
            {value}
          </p>
          <p className="mt-1 text-xs text-muted/75">{meta}</p>
        </div>
      </div>
    </article>
  )
}

function TopOpportunitiesTable({
  opportunities,
  supplierNames,
}: {
  opportunities: DashboardTopOpportunity[]
  supplierNames: Map<number, string>
}) {
  return (
    <section className="glass-panel rounded-xl xl:col-span-2">
      <div className="flex flex-col gap-3 border-b border-outline/40 p-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 font-display text-2xl font-semibold text-text">
            <Target className="h-6 w-6 text-primary" />
            Top 10 oportunidades
          </h2>
          <p className="mt-1 text-sm text-muted">Productos con mayor potencial de adquisicion.</p>
        </div>
        <Link className="inline-flex items-center gap-1 text-sm font-semibold text-primary transition hover:text-primary/80" to="/ranking">
          Ver ranking
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {opportunities.length === 0 ? (
        <EmptyState
          icon={<PackageOpen className="h-10 w-10" />}
          message="Sube y analiza productos para llenar esta tabla."
          title="Sin oportunidades todavia"
        />
      ) : (
        <div className="custom-scrollbar max-h-[520px] overflow-auto">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead className="sticky top-0 z-10 border-b border-outline/40 bg-panel/95 backdrop-blur-xl">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-widest text-muted">Producto</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-widest text-muted">Proveedor</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-widest text-muted">Score</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest text-muted">ROI</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest text-muted">Margen</th>
                <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-widest text-muted">Accion</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-sm text-text">
              {opportunities.map((item) => {
                const tone = recommendationTone(item.recommendation_status)
                const supplierName = item.supplier_id
                  ? supplierNames.get(item.supplier_id) ?? `Proveedor #${item.supplier_id}`
                  : 'Sin proveedor'

                return (
                  <tr className="transition hover:bg-white/[0.04]" key={item.product_id}>
                    <td className="px-4 py-4">
                      <p className="font-semibold">{item.product_name ?? `Producto #${item.product_id}`}</p>
                      <p className="mt-1 text-xs text-muted">{item.category ?? 'Sin categoria'}</p>
                    </td>
                    <td className="px-4 py-4 text-muted">{supplierName}</td>
                    <td className="px-4 py-4">
                      <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-semibold', toneClass(tone))}>
                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                        {formatScore(item.final_opportunity_score)}
                      </span>
                    </td>
                    <td className={cx('px-4 py-4 text-right font-semibold', tone === 'success' ? 'text-success' : 'text-warning')}>
                      {formatRatio(item.roi)}
                    </td>
                    <td className="px-4 py-4 text-right text-muted">{formatRatio(item.margin)}</td>
                    <td className="px-4 py-4 text-center">
                      <span className={cx('inline-flex rounded-lg border px-3 py-1 text-xs font-semibold', toneClass(tone))}>
                        {recommendationLabel(item.recommendation_status)}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function SupplierVolumeChart({
  maxValue,
  suppliers,
}: {
  maxValue: number
  suppliers: DashboardSupplierPerformance[]
}) {
  const visibleSuppliers = suppliers.slice(0, 5)

  return (
    <section className="glass-panel rounded-xl p-5">
      <div>
        <h2 className="flex items-center gap-2 font-display text-2xl font-semibold text-text">
          <BarChart3 className="h-6 w-6 text-success" />
          Volumen por proveedor
        </h2>
        <p className="mt-1 text-sm text-muted">Proveedores con mas productos recomendados.</p>
      </div>

      {visibleSuppliers.length === 0 ? (
        <EmptyState
          icon={<Factory className="h-10 w-10" />}
          message="Aun no hay proveedores con productos en comprar o revisar."
          title="Sin volumen calculado"
        />
      ) : (
        <div className="relative mt-8 flex min-h-[390px] flex-col justify-end gap-5">
          <div className="pointer-events-none absolute inset-0 grid grid-cols-5 opacity-20">
            {Array.from({ length: 5 }).map((_, index) => (
              <span className="border-l border-white/20" key={index} />
            ))}
          </div>

          {visibleSuppliers.map((supplier, index) => {
            const width = maxValue > 0 ? Math.max(8, (supplier.recommended_products / maxValue) * 100) : 0

            return (
              <div className="relative z-10" key={supplier.supplier_id}>
                <div className="mb-2 flex items-center justify-between gap-3 text-xs font-semibold text-muted">
                  <span className="truncate">{supplier.supplier_name ?? `Proveedor #${supplier.supplier_id}`}</span>
                  <span>{formatNumber(supplier.recommended_products)}</span>
                </div>
                <div className="h-6 overflow-hidden rounded-r-lg bg-white/10">
                  <div
                    className="h-full rounded-r-lg bg-gradient-to-r from-primary/50 to-primary shadow-[0_0_14px_rgba(208,188,255,0.22)] transition-all"
                    style={{ opacity: 1 - index * 0.08, width: `${width}%` }}
                  />
                </div>
              </div>
            )
          })}

          <div className="relative z-10 flex justify-between border-t border-outline/30 pt-3 text-[10px] text-muted/60">
            <span>0</span>
            <span>{formatNumber(Math.ceil(maxValue * 0.25))}</span>
            <span>{formatNumber(Math.ceil(maxValue * 0.5))}</span>
            <span>{formatNumber(Math.ceil(maxValue * 0.75))}</span>
            <span>{formatNumber(maxValue)}</span>
          </div>
        </div>
      )}
    </section>
  )
}

function EmptyState({ icon, message, title }: { icon: ReactNode; message: string; title: string }) {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center px-6 py-12 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">{icon}</div>
      <h3 className="mt-4 font-display text-xl font-semibold text-text">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-muted">{message}</p>
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
        {Array.from({ length: 7 }).map((_, index) => (
          <div className="h-40 animate-pulse rounded-xl bg-white/10" key={index} />
        ))}
      </section>
      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="h-[520px] animate-pulse rounded-xl bg-white/10 xl:col-span-2" />
        <div className="h-[520px] animate-pulse rounded-xl bg-white/10" />
      </section>
    </div>
  )
}
