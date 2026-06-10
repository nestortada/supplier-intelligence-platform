import { useContext } from 'react'
import { ToastContext } from '../contexts/toastContext'

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast debe usarse dentro de ToastProvider')
  }

  return context
}
