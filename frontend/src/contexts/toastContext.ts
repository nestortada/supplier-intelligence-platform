import { createContext } from 'react'

export type ToastTone = 'success' | 'error' | 'info'

export type Toast = {
  id: string
  tone: ToastTone
  title: string
  message?: string
}

export type ToastContextValue = {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

export const ToastContext = createContext<ToastContextValue | null>(null)
