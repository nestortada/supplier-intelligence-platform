import { AlertTriangle, Check, Clock, Loader2, MailCheck } from 'lucide-react'
import { cx } from '../utils/classNames'

type StatusBadgeProps = {
  status: string
}

function statusLabel(status: string): string {
  const normalized = status.toLowerCase()
  const labels: Record<string, string> = {
    sent: 'Enviado',
    failed: 'Fallido',
    in_progress: 'En progreso',
    completed: 'Completada',
    canceled: 'Cancelada',
    error: 'Error',
    pending: 'Pendiente',
    draft: 'Borrador',
  }

  return labels[normalized] ?? status
}

function statusIcon(status: string) {
  const normalized = status.toLowerCase()
  if (normalized === 'sent') {
    return <MailCheck className="h-3.5 w-3.5" />
  }
  if (normalized === 'completed') {
    return <Check className="h-3.5 w-3.5" />
  }
  if (normalized === 'failed' || normalized === 'error') {
    return <AlertTriangle className="h-3.5 w-3.5" />
  }
  if (normalized === 'in_progress') {
    return <Loader2 className="h-3.5 w-3.5 animate-spin" />
  }

  return <Clock className="h-3.5 w-3.5" />
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase()

  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold',
        normalized === 'sent' || normalized === 'completed'
          ? 'border-success/20 bg-success/10 text-success'
          : null,
        normalized === 'failed' || normalized === 'error' ? 'border-danger/20 bg-danger/10 text-danger' : null,
        normalized === 'in_progress' ? 'border-warning/20 bg-warning/10 text-warning' : null,
        normalized === 'pending' || normalized === 'draft' || normalized === 'canceled' ? 'border-outline bg-white/5 text-muted' : null,
      )}
    >
      {statusIcon(status)}
      {statusLabel(status)}
    </span>
  )
}
