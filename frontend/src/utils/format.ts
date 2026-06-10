export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return 'Sin fecha'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Sin fecha'
  }

  return new Intl.DateTimeFormat('es-CO', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('es-CO').format(value)
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`
}

export function supplierDisplayName(
  supplier: {
    supplier_name?: string | null
    company?: string | null
    email?: string | null
  },
): string {
  return supplier.supplier_name || supplier.company || supplier.email || 'Proveedor sin nombre'
}
