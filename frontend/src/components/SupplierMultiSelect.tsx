import { Check, Search, X } from 'lucide-react'
import type { Supplier } from '../types/api'
import { cx } from '../utils/classNames'
import { supplierDisplayName } from '../utils/format'

type SupplierMultiSelectProps = {
  suppliers: Supplier[]
  selectedSuppliers: Supplier[]
  search: string
  loading: boolean
  error: string | null
  onSearchChange: (value: string) => void
  onChange: (suppliers: Supplier[]) => void
}

export default function SupplierMultiSelect({
  suppliers,
  selectedSuppliers,
  search,
  loading,
  error,
  onSearchChange,
  onChange,
}: SupplierMultiSelectProps) {
  const selectedIds = new Set(selectedSuppliers.map((supplier) => supplier.id))

  const toggleSupplier = (supplier: Supplier) => {
    if (selectedIds.has(supplier.id)) {
      onChange(selectedSuppliers.filter((selected) => selected.id !== supplier.id))
      return
    }

    onChange([...selectedSuppliers, supplier])
  }

  const removeSupplier = (supplierId: number) => {
    onChange(selectedSuppliers.filter((supplier) => supplier.id !== supplierId))
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          className="field pl-10"
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Buscar proveedor, empresa o email"
          type="search"
          value={search}
        />
      </div>

      {selectedSuppliers.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {selectedSuppliers.map((supplier) => (
            <span
              className="inline-flex max-w-full items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-sm text-primary"
              key={supplier.id}
            >
              <span className="truncate">{supplierDisplayName(supplier)}</span>
              <button
                className="rounded-full p-0.5 transition hover:bg-white/10"
                onClick={() => removeSupplier(supplier.id)}
                type="button"
              >
                <span className="sr-only">Quitar proveedor</span>
                <X className="h-3.5 w-3.5" />
              </button>
            </span>
          ))}
        </div>
      ) : null}

      <div className="custom-scrollbar max-h-64 overflow-y-auto rounded-lg border border-outline/40 bg-background/50">
        {loading ? (
          <div className="space-y-2 p-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <div className="h-12 animate-pulse rounded-lg bg-white/10" key={index} />
            ))}
          </div>
        ) : null}

        {!loading && error ? <div className="p-4 text-sm text-danger">{error}</div> : null}

        {!loading && !error && suppliers.length === 0 ? (
          <div className="p-4 text-sm text-muted">No hay proveedores para mostrar.</div>
        ) : null}

        {!loading && !error
          ? suppliers.map((supplier) => {
              const selected = selectedIds.has(supplier.id)
              return (
                <button
                  className={cx(
                    'flex w-full items-center gap-3 border-b border-outline/20 px-3 py-3 text-left transition last:border-b-0 hover:bg-white/5',
                    selected && 'bg-primary/10',
                  )}
                  key={supplier.id}
                  onClick={() => toggleSupplier(supplier)}
                  type="button"
                >
                  <span
                    className={cx(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded border',
                      selected ? 'border-primary bg-primary text-[#24005f]' : 'border-outline',
                    )}
                  >
                    {selected ? <Check className="h-3.5 w-3.5" /> : null}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-text">{supplierDisplayName(supplier)}</span>
                    <span className="block truncate text-xs text-muted">{supplier.email ?? 'Sin email'}</span>
                  </span>
                </button>
              )
            })
          : null}
      </div>
    </div>
  )
}
