import { CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ToastContext } from '../contexts/toastContext'
import type { Toast, ToastTone } from '../contexts/toastContext'
import { cx } from '../utils/classNames'

type ToastProviderProps = {
  children: ReactNode
}

function toastIcon(tone: ToastTone) {
  if (tone === 'success') {
    return <CheckCircle2 className="h-5 w-5 text-success" />
  }

  if (tone === 'error') {
    return <XCircle className="h-5 w-5 text-danger" />
  }

  return <Info className="h-5 w-5 text-primary" />
}

export default function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const addToast = useCallback(
    (toast: Omit<Toast, 'id'>) => {
      const id = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
      setToasts((current) => [...current, { ...toast, id }])
      window.setTimeout(() => removeToast(id), 4500)
    },
    [removeToast],
  )

  const value = useMemo(
    () => ({
      toasts,
      addToast,
      removeToast,
    }),
    [addToast, removeToast, toasts],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-[80] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-3">
        {toasts.map((toast) => (
          <div
            className={cx(
              'glass-panel flex items-start gap-3 rounded-xl p-4 shadow-glow',
              toast.tone === 'error' && 'border-danger/30',
              toast.tone === 'success' && 'border-success/30',
            )}
            key={toast.id}
          >
            <div className="pt-0.5">{toastIcon(toast.tone)}</div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-text">{toast.title}</p>
              {toast.message ? <p className="mt-1 text-sm text-muted">{toast.message}</p> : null}
            </div>
            <button
              className="rounded-md p-1 text-muted transition hover:bg-white/10 hover:text-text"
              onClick={() => removeToast(toast.id)}
              type="button"
            >
              <span className="sr-only">Cerrar notificación</span>
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
