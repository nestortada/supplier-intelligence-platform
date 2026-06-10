import { useCallback, useEffect, useState } from 'react'
import { fetchSuppliers } from '../api/emailApi'
import type { Supplier } from '../types/api'

type UseSuppliersOptions = {
  search?: string
  hasValidEmail?: boolean
  pageSize?: number
}

export function useSuppliers(options: UseSuppliersOptions) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadSuppliers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchSuppliers({
        search: options.search,
        hasValidEmail: options.hasValidEmail,
        page: 1,
        pageSize: options.pageSize ?? 50,
      })
      setSuppliers(response.items)
      setTotal(response.total)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudieron cargar los proveedores.')
    } finally {
      setLoading(false)
    }
  }, [options.hasValidEmail, options.pageSize, options.search])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadSuppliers()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadSuppliers])

  return {
    suppliers,
    total,
    loading,
    error,
    refresh: loadSuppliers,
  }
}
