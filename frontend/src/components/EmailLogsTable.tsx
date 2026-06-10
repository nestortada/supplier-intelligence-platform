import { Info, Loader2, RefreshCcw, Search } from 'lucide-react'
import { useState } from 'react'
import type { EmailLog, EmailLogFilters } from '../types/api'
import { formatDateTime } from '../utils/format'
import StatusBadge from './StatusBadge'

type EmailLogsTableProps = {
  logs: EmailLog[]
  filters: EmailLogFilters
  loading: boolean
  error: string | null
  onFiltersChange: (filters: EmailLogFilters) => void
  onRefresh: () => void
  onRetry: (log: EmailLog) => Promise<void>
}

function supplierName(log: EmailLog): string {
  return log.supplier_name || log.supplier_company || (log.supplier_id ? `Proveedor ${log.supplier_id}` : 'Sin proveedor')
}

export default function EmailLogsTable({
  logs,
  filters,
  loading,
  error,
  onFiltersChange,
  onRefresh,
  onRetry,
}: EmailLogsTableProps) {
  const [detailsLog, setDetailsLog] = useState<EmailLog | null>(null)
  const [retryingLogId, setRetryingLogId] = useState<number | null>(null)

  const handleRetry = async (log: EmailLog) => {
    setRetryingLogId(log.id)
    try {
      await onRetry(log)
    } finally {
      setRetryingLogId(null)
    }
  }

  return (
    <section className="glass-panel rounded-xl p-5 lg:p-6">
      <div className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h2 className="font-display text-2xl font-semibold text-text">Historial de envíos</h2>
          <p className="text-sm text-muted">Auditoría de cada correo procesado.</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-[10rem_10rem_1fr_auto]">
          <select
            className="field"
            onChange={(event) =>
              onFiltersChange({
                ...filters,
                status: event.target.value as EmailLogFilters['status'],
              })
            }
            value={filters.status}
          >
            <option value="all">Todos</option>
            <option value="sent">Enviados</option>
            <option value="failed">Fallidos</option>
          </select>

          <select
            className="field"
            onChange={(event) =>
              onFiltersChange({
                ...filters,
                lookupType: event.target.value as EmailLogFilters['lookupType'],
                lookupValue: '',
              })
            }
            value={filters.lookupType}
          >
            <option value="none">Sin ID</option>
            <option value="supplier">Proveedor</option>
            <option value="campaign">Campaña</option>
          </select>

          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              className="field pl-10"
              disabled={filters.lookupType === 'none'}
              min="1"
              onChange={(event) =>
                onFiltersChange({
                  ...filters,
                  lookupValue: event.target.value,
                })
              }
              placeholder="ID"
              type="number"
              value={filters.lookupValue}
            />
          </div>

          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-outline/40 px-3 py-2 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-primary"
            onClick={onRefresh}
            type="button"
          >
            <RefreshCcw className="h-4 w-4" />
            Actualizar
          </button>
        </div>
      </div>

      {error ? <div className="mb-4 rounded-xl border border-danger/20 bg-danger/10 p-4 text-sm text-danger">{error}</div> : null}

      <div className="custom-scrollbar overflow-x-auto">
        <table className="w-full min-w-[840px] border-collapse text-left">
          <thead>
            <tr className="border-b border-outline/40">
              <th className="px-4 py-3 text-xs font-semibold uppercase text-muted">Log</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase text-muted">Proveedor</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase text-muted">Email</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase text-muted">Estado</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase text-muted">Fecha</th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-muted">Accion</th>
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 5 }).map((_, index) => (
                  <tr className="border-b border-outline/20" key={index}>
                    <td className="px-4 py-4" colSpan={6}>
                      <div className="h-8 animate-pulse rounded bg-white/10" />
                    </td>
                  </tr>
                ))
              : null}

            {!loading && logs.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-sm text-muted" colSpan={6}>
                  No hay logs para los filtros actuales.
                </td>
              </tr>
            ) : null}

            {!loading
              ? logs.map((log) => (
                  <tr className="group border-b border-outline/20 transition hover:bg-white/5" key={log.id}>
                    <td className="px-4 py-4 font-mono text-sm text-muted">LOG-{log.id}</td>
                    <td className="px-4 py-4">
                      <div className="max-w-[14rem] truncate text-sm font-semibold text-text">{supplierName(log)}</div>
                      <div className="text-xs text-muted">ID {log.supplier_id ?? 'N/D'}</div>
                    </td>
                    <td className="px-4 py-4 text-sm text-muted">{log.to_email ?? 'Sin email'}</td>
                    <td className="px-4 py-4">
                      <StatusBadge status={log.status} />
                    </td>
                    <td className="px-4 py-4 text-sm text-muted">{formatDateTime(log.sent_at)}</td>
                    <td className="px-4 py-4">
                      <div className="flex justify-end gap-2">
                        <button
                          className="rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-primary"
                          onClick={() => setDetailsLog(log)}
                          type="button"
                        >
                          <span className="sr-only">Ver detalles</span>
                          <Info className="h-4 w-4" />
                        </button>
                        {log.status === 'failed' && log.supplier_id ? (
                          <button
                            className="rounded-lg p-2 text-danger transition hover:bg-danger/10 disabled:cursor-not-allowed disabled:opacity-50"
                            disabled={retryingLogId === log.id}
                            onClick={() => void handleRetry(log)}
                            type="button"
                          >
                            <span className="sr-only">Reintentar envío</span>
                            {retryingLogId === log.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RefreshCcw className="h-4 w-4" />
                            )}
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))
              : null}
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-sm text-muted">Mostrando {logs.length} registros.</div>

      {detailsLog ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-xl rounded-xl p-5">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h3 className="font-display text-xl font-semibold text-text">Detalle del log LOG-{detailsLog.id}</h3>
                <p className="text-sm text-muted">{detailsLog.to_email ?? 'Sin destinatario'}</p>
              </div>
              <button
                className="rounded-lg px-3 py-1.5 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-text"
                onClick={() => setDetailsLog(null)}
                type="button"
              >
                Cerrar
              </button>
            </div>

            <div className="space-y-4 text-sm">
              <div>
                <p className="font-semibold text-text">Error</p>
                <p className="mt-1 rounded-lg border border-outline/30 bg-background/60 p-3 text-muted">
                  {detailsLog.error_message || 'Sin mensaje de error.'}
                </p>
              </div>
              <div>
                <p className="font-semibold text-text">Respuesta del proveedor</p>
                <p className="custom-scrollbar mt-1 max-h-48 overflow-auto rounded-lg border border-outline/30 bg-background/60 p-3 text-muted">
                  {detailsLog.provider_response || 'Sin respuesta registrada.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
