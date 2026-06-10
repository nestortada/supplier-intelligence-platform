import { useCallback, useEffect, useState } from 'react'
import { fetchEligibleSuppliers } from '../api/emailApi'
import type { Supplier } from '../types/api'

export function useEligibleSuppliers(search = '') {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadEligibleSuppliers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchEligibleSuppliers({
        search,
        page: 1,
        pageSize: 25,
      })
      setSuppliers(response.items)
      setTotal(response.total)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los proveedores elegibles.')
    } finally {
      setLoading(false)
    }
  }, [search])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadEligibleSuppliers()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadEligibleSuppliers])

  return {
    suppliers,
    total,
    loading,
    error,
    refresh: loadEligibleSuppliers,
  }
}
