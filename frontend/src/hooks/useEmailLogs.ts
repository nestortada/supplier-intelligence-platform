import { useCallback, useEffect, useState } from 'react'
import { fetchEmailLogs } from '../api/emailApi'
import type { EmailLog, EmailLogFilters } from '../types/api'

export function useEmailLogs(filters: EmailLogFilters) {
  const [logs, setLogs] = useState<EmailLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadLogs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchEmailLogs(filters)
      setLogs(response)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los logs.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadLogs()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadLogs])

  return {
    logs,
    loading,
    error,
    refresh: loadLogs,
  }
}
