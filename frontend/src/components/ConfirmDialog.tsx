import { AlertTriangle, Loader2, X } from 'lucide-react'
import type { ReactNode } from 'react'

type ConfirmDialogProps = {
  cancelLabel?: string
  children?: ReactNode
  confirmLabel: string
  danger?: boolean
  loading?: boolean
  message: string
  onCancel: () => void
  onConfirm: () => void
  open: boolean
  title: string
}

export default function ConfirmDialog({
  cancelLabel = 'Cancelar',
  children,
  confirmLabel,
  danger = true,
  loading = false,
  message,
  onCancel,
  onConfirm,
  open,
  title,
}: ConfirmDialogProps) {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-outline/50 bg-panelHigh p-5 shadow-glow">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${danger ? 'bg-danger/15 text-danger' : 'bg-primary/15 text-primary'}`}>
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-display text-xl font-semibold text-text">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted">{message}</p>
            </div>
          </div>
          <button
            className="rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-text"
            disabled={loading}
            onClick={onCancel}
            type="button"
          >
            <span className="sr-only">Cerrar</span>
            <X className="h-4 w-4" />
          </button>
        </div>

        {children ? <div className="mt-4 rounded-lg border border-outline/30 bg-background/50 p-3 text-sm text-muted">{children}</div> : null}

        <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            className="inline-flex items-center justify-center rounded-lg border border-outline/40 px-4 py-2.5 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-text disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loading}
            onClick={onCancel}
            type="button"
          >
            {cancelLabel}
          </button>
          <button
            className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
              danger
                ? 'border border-danger/30 bg-danger/15 text-danger hover:bg-danger/25'
                : 'bg-primary text-[#24005f] hover:bg-primary/90'
            }`}
            disabled={loading}
            onClick={onConfirm}
            type="button"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
