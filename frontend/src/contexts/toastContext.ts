import { createContext } from 'react'

export type ToastTone = 'success' | 'error' | 'info'

export type Toast = {
  id: string
  tone: ToastTone
  title: string
  message?: string
  href?: string
  profileId?: number
  profileName?: string
}

export type AppNotification = Toast & {
  createdAt: string
  read: boolean
}

export type ToastContextValue = {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  addNotification: (notification: Omit<Toast, 'id'>) => void
  clearNotifications: () => void
  markNotificationRead: (id: string) => void
  markNotificationsRead: (profileId?: number) => void
  notifications: AppNotification[]
  removeToast: (id: string) => void
  unreadCount: number
}

export const ToastContext = createContext<ToastContextValue | null>(null)
