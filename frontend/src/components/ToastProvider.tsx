import { CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ToastContext } from '../contexts/toastContext'
import type { AppNotification, Toast, ToastTone } from '../contexts/toastContext'
import { cx } from '../utils/classNames'

type ToastProviderProps = {
  children: ReactNode
}

const NOTIFICATIONS_STORAGE_KEY = 'supplierintel.notifications'
const ACTIVE_PROFILE_STORAGE_KEY = 'supplierintel.activeProfileId'
const ACTIVE_PROFILE_NAME_STORAGE_KEY = 'supplierintel.activeProfileName'
const MAX_NOTIFICATIONS = 40

function toastIcon(tone: ToastTone) {
  if (tone === 'success') {
    return <CheckCircle2 className="h-5 w-5 text-success" />
  }

  if (tone === 'error') {
    return <XCircle className="h-5 w-5 text-danger" />
  }

  return <Info className="h-5 w-5 text-primary" />
}

function readStoredNotifications(): AppNotification[] {
  try {
    const raw = window.localStorage.getItem(NOTIFICATIONS_STORAGE_KEY)
    if (!raw) {
      return []
    }

    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function storeNotifications(notifications: AppNotification[]) {
  window.localStorage.setItem(NOTIFICATIONS_STORAGE_KEY, JSON.stringify(notifications))
}

function readActiveProfileId(): number | undefined {
  const raw = window.localStorage.getItem(ACTIVE_PROFILE_STORAGE_KEY)
  if (!raw) {
    return undefined
  }

  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : undefined
}

function readActiveProfileName(): string | undefined {
  return window.localStorage.getItem(ACTIVE_PROFILE_NAME_STORAGE_KEY) || undefined
}

export default function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const [notifications, setNotifications] = useState<AppNotification[]>(readStoredNotifications)

  const removeToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const addNotification = useCallback((notification: Omit<Toast, 'id'>) => {
    const id = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
    const nextNotification: AppNotification = {
      ...notification,
      id,
      profileId: notification.profileId ?? readActiveProfileId(),
      profileName: notification.profileName ?? readActiveProfileName(),
      createdAt: new Date().toISOString(),
      read: false,
    }

    setNotifications((current) => {
      const next = [nextNotification, ...current].slice(0, MAX_NOTIFICATIONS)
      storeNotifications(next)
      return next
    })
  }, [])

  const addToast = useCallback(
    (toast: Omit<Toast, 'id'>) => {
      const id = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
      setToasts((current) => [...current, { ...toast, id }])
      addNotification(toast)
      window.setTimeout(() => removeToast(id), 4500)
    },
    [addNotification, removeToast],
  )

  const markNotificationRead = useCallback((id: string) => {
    setNotifications((current) => {
      const next = current.map((notification) => (notification.id === id ? { ...notification, read: true } : notification))
      storeNotifications(next)
      return next
    })
  }, [])

  const markNotificationsRead = useCallback((profileId?: number) => {
    setNotifications((current) => {
      const next = current.map((notification) =>
        profileId === undefined || notification.profileId === profileId ? { ...notification, read: true } : notification,
      )
      storeNotifications(next)
      return next
    })
  }, [])

  const clearNotifications = useCallback(() => {
    setNotifications([])
    storeNotifications([])
  }, [])

  const unreadCount = useMemo(() => notifications.filter((notification) => !notification.read).length, [notifications])

  const value = useMemo(
    () => ({
      toasts,
      addToast,
      addNotification,
      clearNotifications,
      markNotificationRead,
      markNotificationsRead,
      notifications,
      removeToast,
      unreadCount,
    }),
    [addNotification, addToast, clearNotifications, markNotificationRead, markNotificationsRead, notifications, removeToast, toasts, unreadCount],
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
