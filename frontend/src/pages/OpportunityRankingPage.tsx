import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Download,
  ExternalLink,
  FileSpreadsheet,
  Loader2,
  RefreshCcw,
  Search,
  Trash2,
  Upload,
  XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ChangeEvent, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  cancelJob,
  deleteAllProducts,
  deleteProduct,
  enrichPendingProducts,
  fetchJobs,
  fetchJobStatus,
  fetchOpportunityRanking,
  uploadCatalogFile,
} from '../api/opportunityApi'
import ProgressBar from '../components/ProgressBar'
import { useToast } from '../hooks/useToast'
import type { CatalogUploadResponse, JobStatus, RankingFilters, RankingItem } from '../types/opportunity'
import { cx } from '../utils/classNames'
import { formatDateTime, formatNumber, formatPercent } from '../utils/format'

type WorkflowPhase = 'idle' | 'uploading' | 'apify' | 'analysis' | 'complete' | 'error' | 'canceled'

const defaultFilters: RankingFilters = {
  minScore: 0,
  recommendation: 'all',
  minRoi: 0,
  minMargin: 0,
  minSales: 0,
  sellersMin: '',
  sellersMax: '',
}

const terminalStatuses = new Set(['completed', 'failed', 'error', 'canceled'])
const activeStatuses = new Set(['pending', 'in_progress'])

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

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

function completedJob(job: JobStatus | null): boolean {
  return job ? job.status === 'completed' : false
}

export default function OpportunityRankingPage() {
  const [filters, setFilters] = useState<RankingFilters>(defaultFilters)
  const [ranking, setRanking] = useState<RankingItem[]>([])
  const [loadingRanking, setLoadingRanking] = useState(false)
  const [rankingError, setRankingError] = useState<string | null>(null)
  const [phase, setPhase] = useState<WorkflowPhase>('idle')
  const [uploadSummary, setUploadSummary] = useState<CatalogUploadResponse | null>(null)
  const [apifyJob, setApifyJob] = useState<JobStatus | null>(null)
  const [analysisJob, setAnalysisJob] = useState<JobStatus | null>(null)
  const [workflowError, setWorkflowError] = useState<string | null>(null)
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null)
  const [deletingProductId, setDeletingProductId] = useState<number | null>(null)
  const [deletingAllProducts, setDeletingAllProducts] = useState(false)
  const [cancelingWorkflow, setCancelingWorkflow] = useState(false)
  const navigate = useNavigate()
  const { addToast } = useToast()

  const workflowActive =
    phase === 'uploading' ||
    activeStatuses.has(apifyJob?.status ?? '') ||
    activeStatuses.has(analysisJob?.status ?? '')

  const kpis = useMemo(() => {
    const buy = ranking.filter((item) => item.recommendation.status === 'buy').length
    const review = ranking.filter((item) => item.recommendation.status === 'review').length
    const averageScore =
      ranking.length > 0
        ? ranking.reduce((total, item) => total + (item.scores.final_opportunity_score ?? 0), 0) / ranking.length
        : 0

    return { buy, review, averageScore }
  }, [ranking])

  const loadRanking = useCallback(async () => {
    setLoadingRanking(true)
    setRankingError(null)
    try {
      const response = await fetchOpportunityRanking(filters)
      setRanking(response)
    } catch (caught) {
      setRankingError(caught instanceof Error ? caught.message : 'No se pudo cargar el ranking.')
    } finally {
      setLoadingRanking(false)
    }
  }, [filters])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadRanking()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadRanking])

  const waitForJob = useCallback(async (jobId: number, onUpdate: (job: JobStatus) => void) => {
    let current = await fetchJobStatus(jobId)
    onUpdate(current)

    while (!terminalStatuses.has(current.status)) {
      await sleep(2000)
      current = await fetchJobStatus(jobId)
      onUpdate(current)
    }

    if (current.status !== 'completed') {
      throw new Error(current.error_message || `Job ${current.type} finalizó con estado ${current.status}.`)
    }

    return current
  }, [])

  const waitForActiveJobByType = useCallback(async (type: string) => {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const activeJobs = await fetchJobs({ status: 'in_progress', type })
      if (activeJobs.length > 0) {
        return activeJobs[0]
      }
      await sleep(1000)
    }
    return null
  }, [])

  const monitorBackendWorkflow = useCallback(
    async (apifyJobId?: number) => {
      try {
        if (apifyJobId) {
          setPhase('apify')
          await waitForJob(apifyJobId, setApifyJob)
        }

        const activeAnalysisJob = await waitForActiveJobByType('product_analysis')
        if (activeAnalysisJob) {
          setPhase('analysis')
          setAnalysisJob(activeAnalysisJob)
          await waitForJob(activeAnalysisJob.job_id, setAnalysisJob)
        }

        setPhase('complete')
        await loadRanking()
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : 'El flujo automatico fallo.'
        if (message.toLowerCase().includes('canceled') || message.toLowerCase().includes('cancel')) {
          setPhase('canceled')
          setWorkflowError(null)
          addToast({
            tone: 'info',
            title: 'Ejecucion cancelada',
            message: 'El backend detendra el flujo antes del siguiente producto.',
          })
          return
        }
        setWorkflowError(message)
        setPhase('error')
        addToast({
          tone: 'error',
          title: 'No se pudo completar el ranking',
          message,
        })
      }
    },
    [addToast, loadRanking, waitForActiveJobByType, waitForJob],
  )

  useEffect(() => {
    let cancelled = false

    const resumeActiveWorkflow = async () => {
      try {
        const [activeAnalysisJobs, activeApifyJobs] = await Promise.all([
          fetchJobs({ status: 'in_progress', type: 'product_analysis' }),
          fetchJobs({ status: 'in_progress', type: 'apify_enrichment' }),
        ])

        if (cancelled) {
          return
        }

        const activeAnalysisJob = activeAnalysisJobs[0]
        if (activeAnalysisJob) {
          setPhase('analysis')
          setAnalysisJob(activeAnalysisJob)
          void monitorBackendWorkflow()
          return
        }

        const activeApifyJob = activeApifyJobs[0]
        if (activeApifyJob) {
          setPhase('apify')
          setApifyJob(activeApifyJob)
          void monitorBackendWorkflow(activeApifyJob.job_id)
        }
      } catch {
        // Ranking load will surface API issues; resume should stay non-blocking.
      }
    }

    void resumeActiveWorkflow()

    return () => {
      cancelled = true
    }
  }, [monitorBackendWorkflow])

  const handleUploadAndAnalyze = useCallback(
    async (file: File) => {
      setWorkflowError(null)
      setUploadSummary(null)
      setApifyJob(null)
      setAnalysisJob(null)
      setSelectedFileName(file.name)

      try {
        setPhase('uploading')
        const uploaded = await uploadCatalogFile(file)
        setUploadSummary(uploaded)

        setPhase('apify')
        const apify = await enrichPendingProducts()
        setApifyJob({
          job_id: apify.job_id,
          type: 'apify_enrichment',
          status: apify.status,
          progress: apify.status === 'completed' ? 100 : 0,
          total_items: apify.total_items,
          processed_items: 0,
          failed_items: 0,
          error_message: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        if (apify.total_items > 0) {
          await monitorBackendWorkflow(apify.job_id)
        } else {
          setPhase('complete')
          await loadRanking()
        }

        addToast({
          tone: 'success',
          title: 'Ranking actualizado',
          message: `${uploaded.products_created} productos importados y analizados.`,
        })
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : 'El flujo automático falló.'
        setWorkflowError(message)
        setPhase('error')
        addToast({
          tone: 'error',
          title: 'No se pudo completar el ranking',
          message,
        })
      }
    },
    [addToast, loadRanking, monitorBackendWorkflow],
  )

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    void handleUploadAndAnalyze(file)
    event.target.value = ''
  }

  const handleCancelWorkflow = useCallback(async () => {
    const activeJob = activeStatuses.has(analysisJob?.status ?? '') ? analysisJob : activeStatuses.has(apifyJob?.status ?? '') ? apifyJob : null
    if (!activeJob) {
      setPhase('canceled')
      return
    }

    setCancelingWorkflow(true)
    try {
      const canceled = await cancelJob(activeJob.job_id)
      if (canceled.type === 'product_analysis') {
        setAnalysisJob(canceled)
      } else {
        setApifyJob(canceled)
      }
      setPhase('canceled')
      addToast({
        tone: 'info',
        title: 'Cancelacion enviada',
        message: 'El proceso se detendra antes del siguiente producto.',
      })
    } catch (caught) {
      addToast({
        tone: 'error',
        title: 'No se pudo cancelar',
        message: caught instanceof Error ? caught.message : 'Intenta nuevamente.',
      })
    } finally {
      setCancelingWorkflow(false)
    }
  }, [addToast, analysisJob, apifyJob])

  const handleDeleteProduct = useCallback(
    async (item: RankingItem) => {
      const productName = item.amazon_data?.amazon_title || item.product.product_name || `Producto ${item.product.id}`
      const confirmed = window.confirm(`Eliminar "${productName}" del ranking? Esta accion tambien elimina sus datos de Amazon y analisis.`)

      if (!confirmed) {
        return
      }

      setDeletingProductId(item.product.id)
      try {
        await deleteProduct(item.product.id)
        setRanking((current) => current.filter((rankingItem) => rankingItem.product.id !== item.product.id))
        addToast({
          tone: 'success',
          title: 'Producto eliminado',
          message: productName,
        })
      } catch (caught) {
        addToast({
          tone: 'error',
          title: 'No se pudo eliminar',
          message: caught instanceof Error ? caught.message : 'Intenta de nuevo.',
        })
      } finally {
        setDeletingProductId(null)
      }
    },
    [addToast],
  )

  const handleDeleteAllProducts = useCallback(async () => {
    const confirmed = window.confirm(
      'Eliminar todos los productos creados? Esta accion tambien elimina sus datos de Amazon y analisis, pero conserva proveedores y campanas.',
    )

    if (!confirmed) {
      return
    }

    setDeletingAllProducts(true)
    try {
      const response = await deleteAllProducts()
      setRanking([])
      addToast({
        tone: 'success',
        title: 'Productos eliminados',
        message: `${response.products_deleted} productos eliminados.`,
      })
    } catch (caught) {
      addToast({
        tone: 'error',
        title: 'No se pudieron eliminar los productos',
        message: caught instanceof Error ? caught.message : 'Intenta de nuevo.',
      })
    } finally {
      setDeletingAllProducts(false)
    }
  }, [addToast])

  const handleOpenProduct = useCallback(
    (item: RankingItem) => {
      navigate(`/ranking/${item.product.id}`)
    },
    [navigate],
  )

  return (
    <div className="mx-auto max-w-[1440px] space-y-6">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
            <BarChart3 className="h-4 w-4" />
            Opportunity Ranking
          </div>
          <h1 className="font-display text-3xl font-semibold text-text md:text-4xl">Ranking de oportunidades</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted md:text-base">
            Sube un catálogo, enriquece productos con Apify y calcula recomendaciones de compra con métricas de Amazon.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <label
            className={cx(
              'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold shadow-glow transition',
              workflowActive
                ? 'cursor-not-allowed bg-primary/50 text-[#24005f]/70'
                : 'cursor-pointer bg-primary text-[#24005f] hover:bg-primary/90',
            )}
          >
            {workflowActive ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Subir catálogo y analizar
            <input
              accept=".xlsx,.xls,.csv"
              className="sr-only"
              disabled={workflowActive}
              onChange={handleFileChange}
              type="file"
            />
          </label>
          {workflowActive ? (
            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-2.5 text-sm font-semibold text-danger transition hover:bg-danger/20 disabled:opacity-60"
              disabled={cancelingWorkflow}
              onClick={() => void handleCancelWorkflow()}
              type="button"
            >
              {cancelingWorkflow ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
              Cancelar ejecuciÃ³n
            </button>
          ) : null}
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-outline/40 px-4 py-2.5 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-primary"
            onClick={() => void loadRanking()}
            type="button"
          >
            <RefreshCcw className="h-4 w-4" />
            Actualizar ranking
          </button>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KpiCard icon={<CheckCircle2 className="h-5 w-5" />} label="Buy signals" value={formatNumber(kpis.buy)} />
        <KpiCard icon={<Search className="h-5 w-5" />} label="En revisión" value={formatNumber(kpis.review)} />
        <KpiCard icon={<BarChart3 className="h-5 w-5" />} label="Score promedio" value={formatPercent(kpis.averageScore)} />
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <WorkflowPanel
            analysisJob={analysisJob}
            apifyJob={apifyJob}
            canceling={cancelingWorkflow}
            onCancel={handleCancelWorkflow}
            phase={phase}
            selectedFileName={selectedFileName}
            uploadSummary={uploadSummary}
            workflowError={workflowError}
          />
        </div>
        <div className="xl:col-span-5">
          <FiltersPanel filters={filters} onChange={setFilters} />
        </div>
      </section>

      <section className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-2xl font-semibold text-text">Oportunidades detectadas</h2>
          <p className="text-sm text-muted">{loadingRanking ? 'Cargando ranking...' : `${ranking.length} resultados visibles`}</p>
        </div>
        <div className="flex gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm font-semibold text-danger transition hover:bg-danger/20 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={workflowActive || deletingAllProducts || ranking.length === 0}
            onClick={() => void handleDeleteAllProducts()}
            type="button"
          >
            {deletingAllProducts ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            Eliminar todos
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg border border-outline/40 px-3 py-2 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-primary" type="button">
            <Download className="h-4 w-4" />
            Summary
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-[#24005f] transition hover:bg-primary/90" type="button">
            <Download className="h-4 w-4" />
            Buy Recs
          </button>
        </div>
      </section>

      {rankingError ? (
        <div className="rounded-xl border border-danger/20 bg-danger/10 p-4 text-sm text-danger">{rankingError}</div>
      ) : null}

      {loadingRanking ? (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div className="h-80 animate-pulse rounded-xl bg-white/10" key={index} />
          ))}
        </div>
      ) : null}

      {!loadingRanking && !rankingError && ranking.length === 0 ? (
        <div className="glass-panel rounded-xl p-8 text-center">
          <FileSpreadsheet className="mx-auto h-10 w-10 text-primary" />
          <h3 className="mt-4 font-display text-xl font-semibold text-text">Sin ranking todavía</h3>
          <p className="mx-auto mt-2 max-w-xl text-sm text-muted">
            Sube un catálogo de productos para enriquecerlo con Apify y generar recomendaciones de oportunidad.
          </p>
        </div>
      ) : null}

      {!loadingRanking && ranking.length > 0 ? (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
          {ranking.map((item) => (
            <OpportunityCard
              deleting={deletingProductId === item.product.id}
              deleteDisabled={workflowActive}
              item={item}
              key={item.product.id}
              onDelete={handleDeleteProduct}
              onOpen={handleOpenProduct}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}

function KpiCard({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <article className="glass-panel glow-border rounded-xl p-5">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/15 text-primary shadow-glow">
          {icon}
        </div>
        <div>
          <p className="text-xs font-semibold uppercase text-muted">{label}</p>
          <p className="mt-1 font-display text-3xl font-semibold text-text">{value}</p>
        </div>
      </div>
    </article>
  )
}

function WorkflowPanel({
  analysisJob,
  apifyJob,
  canceling: _canceling,
  onCancel: _onCancel,
  phase,
  selectedFileName,
  uploadSummary,
  workflowError,
}: {
  analysisJob: JobStatus | null
  apifyJob: JobStatus | null
  canceling: boolean
  onCancel: () => void
  phase: WorkflowPhase
  selectedFileName: string | null
  uploadSummary: CatalogUploadResponse | null
  workflowError: string | null
}) {
  void _canceling
  void _onCancel

  return (
    <section className="glass-panel rounded-xl p-5 lg:p-6">
      <div className="mb-5 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-success/15 text-success">
          <FileSpreadsheet className="h-5 w-5" />
        </div>
        <div>
          <h2 className="font-display text-2xl font-semibold text-text">Flujo automático Apify</h2>
          <p className="text-sm text-muted">
            {selectedFileName ? `Archivo: ${selectedFileName}` : 'Usa proveedor técnico Ranking Import para la importación.'}
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <WorkflowStep
          active={phase === 'uploading'}
          complete={Boolean(uploadSummary)}
          label="Importación de catálogo"
          meta={
            uploadSummary
              ? `${uploadSummary.products_created} creados, ${uploadSummary.duplicates} duplicados, ${uploadSummary.missing_upc} sin UPC`
              : 'Esperando archivo Excel o CSV'
          }
        />
        <WorkflowStep
          active={phase === 'apify'}
          complete={completedJob(apifyJob)}
          job={apifyJob}
          label="Búsqueda en Apify"
          meta="Input por producto: identifiers, include_variants=false, stream_output=true"
        />
        <WorkflowStep
          active={phase === 'analysis'}
          complete={completedJob(analysisJob)}
          job={analysisJob}
          label="Cálculo de oportunidad"
          meta="ROI, margen, sellers, ventas estimadas, estabilidad y score final"
        />
      </div>

      {workflowError ? (
        <div className="mt-5 rounded-xl border border-danger/20 bg-danger/10 p-4 text-sm text-danger">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{workflowError}</span>
          </div>
        </div>
      ) : null}
    </section>
  )
}

function WorkflowStep({
  active,
  complete,
  job,
  label,
  meta,
}: {
  active: boolean
  complete: boolean
  job?: JobStatus | null
  label: string
  meta: string
}) {
  const progress = job?.progress ?? (complete ? 100 : 0)

  return (
    <div className="rounded-xl border border-outline/40 bg-background/50 p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text">{label}</p>
          <p className="mt-1 text-xs text-muted">{job ? `${job.processed_items}/${job.total_items} procesados` : meta}</p>
        </div>
        <span
          className={cx(
            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold',
            complete && 'border-success/20 bg-success/10 text-success',
            active && !complete && 'border-warning/20 bg-warning/10 text-warning',
            !active && !complete && 'border-outline bg-white/5 text-muted',
          )}
        >
          {active && !complete ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          {complete ? 'Completado' : active ? 'En progreso' : 'Pendiente'}
        </span>
      </div>
      <ProgressBar tone={complete ? 'success' : active ? 'warning' : 'primary'} value={progress} />
      {job?.error_message ? <p className="mt-2 text-xs text-danger">{job.error_message}</p> : null}
    </div>
  )
}

function FiltersPanel({ filters, onChange }: { filters: RankingFilters; onChange: (filters: RankingFilters) => void }) {
  return (
    <section className="glass-panel rounded-xl p-5 lg:p-6">
      <h2 className="font-display text-2xl font-semibold text-text">Filtros</h2>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
        <RangeField
          label="Min score"
          max={100}
          suffix=""
          value={filters.minScore}
          onChange={(value) => onChange({ ...filters, minScore: value })}
        />
        <label className="block">
          <span className="mb-2 block text-xs font-semibold uppercase text-muted">Recomendación</span>
          <select
            className="field"
            onChange={(event) =>
              onChange({ ...filters, recommendation: event.target.value as RankingFilters['recommendation'] })
            }
            value={filters.recommendation}
          >
            <option value="all">Todas</option>
            <option value="buy">Buy</option>
            <option value="review">Review</option>
            <option value="discard">Discard</option>
            <option value="insufficient_data">Datos insuficientes</option>
          </select>
        </label>
        <RangeField
          label="Min ROI"
          max={150}
          suffix="%"
          value={filters.minRoi}
          onChange={(value) => onChange({ ...filters, minRoi: value })}
        />
        <RangeField
          label="Min margin"
          max={100}
          prefix="$"
          value={filters.minMargin}
          onChange={(value) => onChange({ ...filters, minMargin: value })}
        />
        <label className="block">
          <span className="mb-2 block text-xs font-semibold uppercase text-muted">Min ventas mensuales</span>
          <input
            className="field"
            min="0"
            onChange={(event) => onChange({ ...filters, minSales: Number(event.target.value) })}
            type="number"
            value={filters.minSales}
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase text-muted">Sellers min</span>
            <input
              className="field"
              onChange={(event) => onChange({ ...filters, sellersMin: event.target.value })}
              placeholder="Opcional"
              type="number"
              value={filters.sellersMin}
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase text-muted">Sellers max</span>
            <input
              className="field"
              onChange={(event) => onChange({ ...filters, sellersMax: event.target.value })}
              placeholder="Opcional"
              type="number"
              value={filters.sellersMax}
            />
          </label>
        </div>
      </div>
    </section>
  )
}

function RangeField({
  label,
  max,
  onChange,
  prefix = '',
  suffix = '',
  value,
}: {
  label: string
  max: number
  onChange: (value: number) => void
  prefix?: string
  suffix?: string
  value: number
}) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center justify-between text-xs font-semibold uppercase text-muted">
        {label}
        <span className="text-primary">
          {prefix}
          {value}
          {suffix}
        </span>
      </span>
      <input
        className="w-full accent-primary"
        max={max}
        min="0"
        onChange={(event) => onChange(Number(event.target.value))}
        type="range"
        value={value}
      />
    </label>
  )
}

function OpportunityCard({
  deleteDisabled,
  deleting,
  item,
  onDelete,
  onOpen,
}: {
  deleteDisabled: boolean
  deleting: boolean
  item: RankingItem
  onDelete: (item: RankingItem) => void
  onOpen: (item: RankingItem) => void
}) {
  const amazonPrice =
    item.amazon_data?.current_price ??
    item.amazon_data?.buybox_price ??
    item.amazon_data?.amazon_price ??
    item.amazon_data?.list_price ??
    null
  const score = item.scores.final_opportunity_score ?? 0
  const tone = recommendationTone(item.recommendation.status)
  const spread =
    item.product.supplier_cost && amazonPrice ? ((amazonPrice - item.product.supplier_cost) / item.product.supplier_cost) * 100 : null

  return (
    <article
      aria-label={`Ver detalle de ${item.amazon_data?.amazon_title || item.product.product_name || `producto ${item.product.id}`}`}
      className="glass-panel cursor-pointer overflow-hidden rounded-xl transition hover:border-primary/30 hover:bg-white/[0.03] focus:outline-none focus:ring-2 focus:ring-primary/50"
      onClick={() => onOpen(item)}
      onKeyDown={(event) => {
        if (event.currentTarget !== event.target) {
          return
        }

        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onOpen(item)
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div className={cx('h-1 w-full', tone === 'success' ? 'bg-success' : tone === 'danger' ? 'bg-danger' : 'bg-primary')} />
      <div className="grid grid-cols-1 md:grid-cols-[13rem_1fr]">
        <div className="relative flex min-h-56 items-center justify-center bg-white/5 p-5">
          {item.amazon_data?.image_url ? (
            <img
              alt={item.amazon_data.amazon_title ?? item.product.product_name ?? 'Producto Amazon'}
              className="max-h-48 w-full object-contain"
              src={item.amazon_data.image_url}
            />
          ) : (
            <div className="flex h-32 w-32 items-center justify-center rounded-full bg-primary/10 text-primary">
              <FileSpreadsheet className="h-12 w-12" />
            </div>
          )}
          <span className={`absolute left-3 top-3 rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClasses(tone)}`}>
            {recommendationLabel(item.recommendation.status)}
          </span>
        </div>

        <div className="relative p-5">
          <div className="absolute right-5 top-5 flex items-center gap-2">
            <button
              aria-label="Eliminar producto"
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-danger/30 bg-danger/10 text-danger transition hover:bg-danger/20 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={deleteDisabled || deleting}
              onClick={(event) => {
                event.stopPropagation()
                onDelete(item)
              }}
              title="Eliminar producto"
              type="button"
            >
              {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            </button>
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-primary/30 bg-primary/10 shadow-glow">
              <span className="font-display text-xl font-bold text-primary">{Math.round(score)}</span>
            </div>
          </div>

          <div className="pr-28">
            <p className="text-xs font-semibold uppercase text-primary">{item.product.brand || item.product.category || 'Amazon data'}</p>
            <h3 className="mt-1 line-clamp-2 font-display text-xl font-semibold leading-tight text-text">
              {item.amazon_data?.amazon_title || item.product.product_name || 'Producto sin nombre'}
            </h3>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted">
              {item.amazon_data?.amazon_url ? (
                <a
                  className="inline-flex items-center gap-1 transition hover:text-primary"
                  href={item.amazon_data.amazon_url}
                  onClick={(event) => event.stopPropagation()}
                  rel="noreferrer"
                  target="_blank"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Amazon
                </a>
              ) : null}
              {item.amazon_data?.asin ? <span>ASIN: {item.amazon_data.asin}</span> : null}
              <span>Producto ID: {item.product.id}</span>
            </div>
          </div>

          <div className="mt-5 grid gap-3 rounded-xl border border-outline/30 bg-background/50 p-4 sm:grid-cols-3">
            <Metric label="Costo proveedor" value={money(item.product.supplier_cost)} />
            <Metric label="Precio Amazon" value={money(amazonPrice)} />
            <Metric label="Spread" tone={spread && spread > 0 ? 'success' : 'danger'} value={spread === null ? 'N/D' : formatPercent(spread)} />
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3 border-t border-outline/30 pt-4 sm:grid-cols-4">
            <Metric label="ROI" tone="success" value={percentFromRatio(item.analysis.roi)} />
            <Metric label="Ganancia neta" value={money(item.analysis.net_profit)} />
            <Metric label="Ventas mes" value={formatNumber(item.amazon_data?.estimated_sales ?? 0)} />
            <Metric label="Sellers" value={item.amazon_data?.sellers_count ? `${item.amazon_data.sellers_count}` : 'N/D'} />
          </div>

          <div className="mt-5 rounded-xl border border-outline/30 bg-background/40 p-3">
            <p className="text-sm font-semibold text-text">{item.recommendation.reason || 'Sin explicación disponible.'}</p>
            {item.recommendation.risks.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {item.recommendation.risks.slice(0, 3).map((risk) => (
                  <span className="rounded-full border border-warning/20 bg-warning/10 px-2.5 py-1 text-xs text-warning" key={risk}>
                    {risk}
                  </span>
                ))}
              </div>
            ) : null}
            <p className="mt-3 text-xs text-muted">
              Actualizado {formatDateTime(item.analysis.analyzed_at)}
            </p>
          </div>
        </div>
      </div>
    </article>
  )
}

function Metric({ label, tone, value }: { label: string; tone?: 'success' | 'danger'; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase text-muted">{label}</p>
      <p className={cx('mt-1 text-sm font-bold text-text', tone === 'success' && 'text-success', tone === 'danger' && 'text-danger')}>
        {value}
      </p>
    </div>
  )
}
