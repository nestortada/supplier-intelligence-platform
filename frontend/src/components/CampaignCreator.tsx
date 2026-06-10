import { Database, FileSpreadsheet, Loader2, Rocket, Trash2, Upload, Users } from 'lucide-react'
import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { DEFAULT_EMAIL_SUBJECT } from '../constants/email'
import type { LaunchCampaignInput, Supplier } from '../types/api'
import { cx } from '../utils/classNames'
import SupplierMultiSelect from './SupplierMultiSelect'

type CampaignCreatorProps = {
  eligibleCount: number
  eligibleLoading: boolean
  suppliers: Supplier[]
  suppliersLoading: boolean
  suppliersError: string | null
  supplierSearch: string
  onSupplierSearchChange: (value: string) => void
  onLaunch: (input: LaunchCampaignInput) => Promise<void>
  onUploadSuppliers: (file: File) => Promise<void>
  onClearDatabase: () => Promise<void>
  executionActive?: boolean
}

export default function CampaignCreator({
  eligibleCount,
  eligibleLoading,
  suppliers,
  suppliersLoading,
  suppliersError,
  supplierSearch,
  onSupplierSearchChange,
  onLaunch,
  onUploadSuppliers,
  onClearDatabase,
  executionActive = false,
}: CampaignCreatorProps) {
  const [target, setTarget] = useState<'eligible' | 'specific'>('eligible')
  const [selectedSuppliers, setSelectedSuppliers] = useState<Supplier[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [clearing, setClearing] = useState(false)

  const disabled =
    submitting ||
    executionActive ||
    (target === 'eligible' && (eligibleLoading || eligibleCount === 0)) ||
    (target === 'specific' && selectedSuppliers.length === 0)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (disabled) {
      return
    }

    setSubmitting(true)
    try {
      await onLaunch({
        target,
        supplierIds: selectedSuppliers.map((supplier) => supplier.id),
        subject: DEFAULT_EMAIL_SUBJECT,
        templateId: null,
      })
      setSelectedSuppliers([])
      setTarget('eligible')
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    setUploading(true)
    try {
      await onUploadSuppliers(file)
      event.target.value = ''
    } finally {
      setUploading(false)
    }
  }

  const handleClearDatabase = async () => {
    const confirmed = window.confirm(
      'Esto borrará proveedores, productos, campañas y logs de email guardados. ¿Quieres continuar?',
    )
    if (!confirmed) {
      return
    }

    setClearing(true)
    try {
      await onClearDatabase()
      setSelectedSuppliers([])
      setTarget('eligible')
    } finally {
      setClearing(false)
    }
  }

  return (
    <section className="glass-panel glow-border rounded-xl p-5 lg:p-6">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Users className="h-5 w-5" />
        </div>
        <div>
          <h2 className="font-display text-2xl font-semibold text-text">Nueva campaña</h2>
          <p className="text-sm text-muted">Carga proveedores, elige destinatarios y lanza el outreach.</p>
        </div>
      </div>

      <form className="space-y-6" onSubmit={handleSubmit}>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-outline/40 bg-background/50 p-4">
            <div className="mb-4 flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-success/15 text-success">
                <FileSpreadsheet className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text">Subir base de proveedores</h3>
                <p className="mt-1 text-sm text-muted">
                  Acepta archivos Excel o CSV con el formato de proveedores_ejemplo.xlsx.
                </p>
              </div>
            </div>
            <label
              className={cx(
                'inline-flex w-full items-center justify-center gap-2 rounded-lg border border-success/30 px-4 py-2.5 text-sm font-semibold transition',
                executionActive
                  ? 'cursor-not-allowed bg-success/5 text-success/50'
                  : 'cursor-pointer bg-success/10 text-success hover:bg-success/15',
              )}
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {uploading ? 'Subiendo...' : 'Subir Excel o CSV'}
              <input
                accept=".xlsx,.xls,.csv"
                className="sr-only"
                disabled={executionActive || uploading}
                onChange={handleUpload}
                type="file"
              />
            </label>
          </div>

          <div className="rounded-xl border border-danger/30 bg-danger/10 p-4">
            <div className="mb-4 flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-danger/15 text-danger">
                <Database className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text">Limpiar base actual</h3>
                <p className="mt-1 text-sm text-muted">
                  Borra proveedores, productos, campañas y logs para cargar una base nueva desde cero.
                </p>
              </div>
            </div>
            <button
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-2.5 text-sm font-semibold text-danger transition hover:bg-danger/15 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={executionActive || clearing}
              onClick={handleClearDatabase}
              type="button"
            >
              {clearing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              {clearing ? 'Eliminando...' : 'Eliminar base de datos'}
            </button>
          </div>
        </div>

        <div>
          <label className="mb-3 block text-xs font-semibold uppercase text-muted">Destinatarios</label>
          <div className="grid gap-3 sm:grid-cols-2">
            <button
              className={cx(
                'rounded-xl border p-4 text-left transition',
                target === 'eligible'
                  ? 'border-primary/60 bg-primary/10 shadow-glow'
                  : 'border-outline/40 bg-panelHigh/40 hover:bg-white/5',
              )}
              onClick={() => setTarget('eligible')}
              type="button"
            >
              <span className="text-sm font-semibold text-text">Todos los elegibles</span>
              <span className="mt-1 block text-sm text-success">
                {eligibleLoading ? 'Calculando...' : `${eligibleCount} proveedores califican`}
              </span>
            </button>

            <button
              className={cx(
                'rounded-xl border p-4 text-left transition',
                target === 'specific'
                  ? 'border-primary/60 bg-primary/10 shadow-glow'
                  : 'border-outline/40 bg-panelHigh/40 hover:bg-white/5',
              )}
              onClick={() => setTarget('specific')}
              type="button"
            >
              <span className="text-sm font-semibold text-text">Proveedores específicos</span>
              <span className="mt-1 block text-sm text-muted">{selectedSuppliers.length} seleccionados</span>
            </button>
          </div>
        </div>

        {target === 'specific' ? (
          <SupplierMultiSelect
            error={suppliersError}
            loading={suppliersLoading}
            onChange={setSelectedSuppliers}
            onSearchChange={onSupplierSearchChange}
            search={supplierSearch}
            selectedSuppliers={selectedSuppliers}
            suppliers={suppliers}
          />
        ) : null}

        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted">
            {target === 'eligible'
              ? 'El backend excluye proveedores ya contactados y emails no válidos.'
              : 'Solo se enviará a los proveedores seleccionados.'}
          </p>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-[#24005f] shadow-glow transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={disabled}
            type="submit"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Rocket className="h-4 w-4" />}
            Lanzar campaña
          </button>
        </div>
      </form>
    </section>
  )
}
