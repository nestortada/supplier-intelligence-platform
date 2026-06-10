import { AlertTriangle, CheckCircle2, Send } from 'lucide-react'
import type { EmailLog } from '../types/api'
import { formatNumber, formatPercent } from '../utils/format'

type KpiCardsProps = {
  logs: EmailLog[]
  loading: boolean
}

type KpiCardProps = {
  label: string
  value: string
  icon: typeof Send
  tone: 'primary' | 'success' | 'danger'
  loading: boolean
}

const toneClass = {
  primary: 'bg-primary/15 text-primary shadow-glow',
  success: 'bg-success/15 text-success shadow-successGlow',
  danger: 'bg-danger/15 text-danger',
}

function KpiCard({ label, value, icon: Icon, tone, loading }: KpiCardProps) {
  return (
    <article className="glass-panel glow-border rounded-xl p-5">
      <div className="flex items-center gap-4">
        <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${toneClass[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase text-muted">{label}</p>
          {loading ? (
            <div className="mt-2 h-8 w-24 animate-pulse rounded bg-white/10" />
          ) : (
            <p className="mt-1 font-display text-3xl font-semibold text-text">{value}</p>
          )}
        </div>
      </div>
    </article>
  )
}

export default function KpiCards({ logs, loading }: KpiCardsProps) {
  const sent = logs.filter((log) => log.status === 'sent').length
  const failed = logs.filter((log) => log.status === 'failed').length
  const total = logs.length
  const successRate = total > 0 ? (sent / total) * 100 : 0

  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <KpiCard icon={Send} label="Total enviados" loading={loading} tone="primary" value={formatNumber(sent)} />
      <KpiCard
        icon={CheckCircle2}
        label="Éxito en envío"
        loading={loading}
        tone="success"
        value={formatPercent(successRate)}
      />
      <KpiCard
        icon={AlertTriangle}
        label="Envíos fallidos"
        loading={loading}
        tone="danger"
        value={formatNumber(failed)}
      />
    </section>
  )
}
