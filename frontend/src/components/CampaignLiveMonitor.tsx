import { RefreshCcw, RadioTower } from 'lucide-react'
import type { CampaignSummary } from '../types/api'
import { formatDateTime, formatNumber, formatPercent } from '../utils/format'
import ProgressBar from './ProgressBar'
import StatusBadge from './StatusBadge'

type CampaignLiveMonitorProps = {
  campaigns: CampaignSummary[]
  loading: boolean
  error: string | null
  onRefresh: () => void
}

function progressForCampaign(campaign: CampaignSummary): number {
  if (campaign.total <= 0) {
    return 100
  }

  return ((campaign.sent + campaign.failed) / campaign.total) * 100
}

function progressTone(status: string): 'success' | 'warning' | 'danger' | 'primary' {
  if (status === 'completed') {
    return 'success'
  }
  if (status === 'failed' || status === 'error') {
    return 'danger'
  }
  if (status === 'in_progress') {
    return 'warning'
  }
  return 'primary'
}

export default function CampaignLiveMonitor({ campaigns, loading, error, onRefresh }: CampaignLiveMonitorProps) {
  return (
    <section className="glass-panel rounded-xl p-5 lg:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/15 text-success">
            <RadioTower className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-display text-2xl font-semibold text-text">Monitor en vivo</h2>
            <p className="text-sm text-muted">Campañas recientes y progreso operativo.</p>
          </div>
        </div>
        <button
          className="rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-primary"
          onClick={onRefresh}
          type="button"
        >
          <span className="sr-only">Actualizar campañas</span>
          <RefreshCcw className="h-4 w-4" />
        </button>
      </div>

      <div className="custom-scrollbar max-h-[38rem] space-y-4 overflow-y-auto pr-1">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div className="h-32 animate-pulse rounded-xl bg-white/10" key={index} />
            ))}
          </div>
        ) : null}

        {!loading && error ? (
          <div className="rounded-xl border border-danger/20 bg-danger/10 p-4 text-sm text-danger">{error}</div>
        ) : null}

        {!loading && !error && campaigns.length === 0 ? (
          <div className="rounded-xl border border-outline/40 bg-background/50 p-5 text-sm text-muted">
            No hay campañas recientes.
          </div>
        ) : null}

        {!loading && !error
          ? campaigns.map((campaign) => {
              const progress = progressForCampaign(campaign)
              return (
                <article className="rounded-xl border border-outline/40 bg-background/55 p-4" key={campaign.campaign_id}>
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-primary">CMP-{campaign.campaign_id}</p>
                      <h3 className="mt-1 truncate text-sm font-semibold text-text">
                        {campaign.subject || 'Campaña sin asunto'}
                      </h3>
                      <p className="mt-1 text-xs text-muted">Actualizada {formatDateTime(campaign.updated_at)}</p>
                    </div>
                    <StatusBadge status={campaign.status} />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-muted">
                      <span>Progreso</span>
                      <span>{formatPercent(progress)}</span>
                    </div>
                    <ProgressBar tone={progressTone(campaign.status)} value={progress} />
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-muted sm:grid-cols-4">
                    <span>Enviados: {formatNumber(campaign.sent)}</span>
                    <span>Fallidos: {formatNumber(campaign.failed)}</span>
                    <span>Pendientes: {formatNumber(campaign.pending)}</span>
                    <span>Total: {formatNumber(campaign.total)}</span>
                  </div>
                </article>
              )
            })
          : null}
      </div>
    </section>
  )
}
