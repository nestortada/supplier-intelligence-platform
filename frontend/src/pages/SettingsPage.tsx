import { AlertTriangle, Camera, Check, Cloud, Loader2, RefreshCw, RotateCcw, Save, Trash2, User, X } from 'lucide-react'
import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchSyncStatus, runSync } from '../api/syncApi'
import ConfirmDialog from '../components/ConfirmDialog'
import ProfileAvatar from '../components/ProfileAvatar'
import { useProfile } from '../hooks/useProfile'
import { useToast } from '../hooks/useToast'
import type { SyncStatus } from '../types/opportunity'
import { cx } from '../utils/classNames'

const MAX_AVATAR_BYTES = 900_000

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(new Error('No se pudo leer la imagen.'))
    reader.readAsDataURL(file)
  })
}

export default function SettingsPage() {
  const navigate = useNavigate()
  const { addToast } = useToast()
  const { activeProfile, deleteActiveProfile, updateActiveProfile } = useProfile()
  const [name, setName] = useState(activeProfile?.name ?? '')
  const [avatarDataUrl, setAvatarDataUrl] = useState<string | null>(activeProfile?.avatar_data_url ?? null)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null)
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [syncLoading, setSyncLoading] = useState(false)

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setName(activeProfile?.name ?? '')
      setAvatarDataUrl(activeProfile?.avatar_data_url ?? null)
      setAvatarError(null)
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [activeProfile])

  useEffect(() => {
    let cancelled = false

    async function loadSyncStatus() {
      try {
        const status = await fetchSyncStatus()
        if (!cancelled) {
          setSyncStatus(status)
        }
      } catch {
        if (!cancelled) {
          setSyncStatus(null)
        }
      }
    }

    void loadSyncStatus()

    return () => {
      cancelled = true
    }
  }, [])

  const dirty = useMemo(() => {
    return name.trim() !== (activeProfile?.name ?? '') || avatarDataUrl !== (activeProfile?.avatar_data_url ?? null)
  }, [activeProfile, avatarDataUrl, name])

  function discardChanges() {
    setName(activeProfile?.name ?? '')
    setAvatarDataUrl(activeProfile?.avatar_data_url ?? null)
    setAvatarError(null)
  }

  async function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    setAvatarError(null)

    if (!file) {
      return
    }

    if (!file.type.startsWith('image/')) {
      setAvatarError('Selecciona una imagen valida.')
      return
    }

    if (file.size > MAX_AVATAR_BYTES) {
      setAvatarError('La imagen debe pesar menos de 900 KB.')
      return
    }

    try {
      setAvatarDataUrl(await fileToDataUrl(file))
    } catch (caught) {
      setAvatarError(caught instanceof Error ? caught.message : 'No se pudo leer la imagen.')
    } finally {
      event.target.value = ''
    }
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) {
      setAvatarError('El nombre es obligatorio.')
      return
    }

    setSaving(true)
    try {
      const updatedProfile = await updateActiveProfile(trimmedName, avatarDataUrl)
      setLastSavedAt(
        new Intl.DateTimeFormat('es-CO', {
          hour: '2-digit',
          minute: '2-digit',
        }).format(new Date()),
      )
      addToast({ title: 'Perfil actualizado', message: updatedProfile.name, tone: 'success' })
    } catch (caught) {
      addToast({
        title: 'No se pudo actualizar el perfil',
        message: caught instanceof Error ? caught.message : 'Intentalo nuevamente.',
        tone: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  async function confirmDeleteAccount() {
    if (!activeProfile) {
      return
    }

    setDeleting(true)
    try {
      await deleteActiveProfile()
      addToast({ title: 'Cuenta eliminada', message: activeProfile.name, tone: 'success' })
      setDeleteDialogOpen(false)
      navigate('/profiles')
    } catch (caught) {
      addToast({
        title: 'No se pudo eliminar la cuenta',
        message: caught instanceof Error ? caught.message : 'Intentalo nuevamente.',
        tone: 'error',
      })
    } finally {
      setDeleting(false)
    }
  }

  async function handleRunSync() {
    setSyncLoading(true)
    try {
      const status = await runSync()
      setSyncStatus(status)
      if (status.error || status.last_error) {
        addToast({
          title: 'Firebase no se sincronizo',
          message: status.error || status.last_error || 'Revisa la configuracion.',
          tone: 'error',
        })
      } else {
        addToast({
          title: 'Firebase sincronizado',
          message: `${status.pending_count} pendientes, namespace ${status.namespace}.`,
          tone: 'success',
        })
      }
    } catch (caught) {
      addToast({
        title: 'No se pudo sincronizar Firebase',
        message: caught instanceof Error ? caught.message : 'Intentalo nuevamente.',
        tone: 'error',
      })
    } finally {
      setSyncLoading(false)
    }
  }

  if (!activeProfile) {
    return null
  }

  return (
    <form className="mx-auto w-[calc(100vw-3rem)] max-w-[1440px] min-w-0 space-y-6 pb-28 sm:w-auto" onSubmit={(event) => void handleSave(event)}>
      <header>
        <h1 className="font-display text-3xl font-semibold text-primary md:text-4xl">System Settings</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted md:text-base">
          Configure your executive environment and account profile.
        </p>
      </header>

      <section className="glass-panel glow-border rounded-2xl p-5 sm:p-6">
        <div className="mb-6 flex items-center gap-2">
          <User className="h-5 w-5 text-primary" />
          <h2 className="font-display text-2xl font-semibold text-text">Profile Settings</h2>
        </div>

        <div className="flex flex-col gap-8 md:flex-row md:items-center">
          <div className="relative w-fit">
            <ProfileAvatar
              avatarDataUrl={avatarDataUrl}
              className="h-32 w-32 rounded-2xl border-primary/20 text-3xl ring-2 ring-primary/15"
              name={name}
            />
            <label className="absolute -bottom-2 -right-2 inline-flex h-11 w-11 cursor-pointer items-center justify-center rounded-lg bg-primary text-[#23005c] shadow-glow transition hover:scale-105">
              <Camera className="h-5 w-5" />
              <span className="sr-only">Cambiar foto</span>
              <input accept="image/*" className="sr-only" onChange={(event) => void handleAvatarChange(event)} type="file" />
            </label>
          </div>

          <div className="grid min-w-0 flex-1 gap-4">
            <div className="space-y-1.5">
              <label className="ml-1 block text-xs font-semibold uppercase tracking-wider text-muted" htmlFor="profile-name">
                Full Name / Display Name
              </label>
              <input
                className="field"
                id="profile-name"
                maxLength={120}
                onChange={(event) => {
                  setName(event.target.value)
                  setAvatarError(null)
                }}
                value={name}
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <label className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-outline/50 px-4 py-2.5 text-sm font-semibold text-muted transition hover:border-primary/60 hover:text-primary">
                <Camera className="h-4 w-4" />
                Cambiar foto
                <input accept="image/*" className="sr-only" onChange={(event) => void handleAvatarChange(event)} type="file" />
              </label>
              <button
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-outline/50 px-4 py-2.5 text-sm font-semibold text-muted transition hover:border-danger/50 hover:text-danger disabled:opacity-50"
                disabled={!avatarDataUrl}
                onClick={() => setAvatarDataUrl(null)}
                type="button"
              >
                <X className="h-4 w-4" />
                Quitar foto
              </button>
            </div>

            {avatarError ? <p className="text-sm text-danger">{avatarError}</p> : null}
          </div>
        </div>
      </section>

      <section className="glass-panel glow-border rounded-2xl p-5 sm:p-6">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <Cloud className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="font-display text-2xl font-semibold text-text">Firebase Sync</h2>
              <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold uppercase text-muted">
                <span className={cx('rounded-md px-2 py-1', syncStatus?.enabled ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning')}>
                  {syncStatus?.enabled ? 'Activo' : 'Inactivo'}
                </span>
                <span className="rounded-md bg-white/5 px-2 py-1">Pendientes: {syncStatus?.pending_count ?? 0}</span>
                <span className="rounded-md bg-white/5 px-2 py-1">Fallidos: {syncStatus?.failed_count ?? 0}</span>
                <span className="rounded-md bg-white/5 px-2 py-1">Namespace: {syncStatus?.namespace ?? 'default'}</span>
              </div>
              {syncStatus?.last_successful_sync ? (
                <p className="mt-3 text-sm text-muted">Ultima sincronizacion: {new Date(syncStatus.last_successful_sync).toLocaleString('es-CO')}</p>
              ) : null}
              {syncStatus?.last_error ? <p className="mt-3 max-w-4xl text-sm text-danger">{syncStatus.last_error}</p> : null}
            </div>
          </div>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-bold text-[#23005c] shadow-glow transition hover:bg-primary/90 disabled:opacity-60"
            disabled={syncLoading || syncStatus?.enabled === false}
            onClick={() => void handleRunSync()}
            type="button"
          >
            {syncLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Sincronizar ahora
          </button>
        </div>
      </section>

      <section className="glass-panel relative overflow-hidden rounded-2xl border-danger/20 p-5 sm:p-6">
        <div className="absolute inset-0 bg-danger/5 opacity-0 transition-opacity hover:opacity-100" />
        <div className="relative z-10 flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-danger/10">
              <AlertTriangle className="h-6 w-6 text-danger" />
            </div>
            <div>
              <h2 className="font-display text-2xl font-semibold text-danger">Danger Zone</h2>
              <p className="mt-1 max-w-3xl text-sm text-muted md:text-base">
                All your data, including supplier relationships, intelligence reports, and active email campaigns will be{' '}
                <span className="font-bold text-danger">permanently removed</span>. This action is irreversible.
              </p>
            </div>
          </div>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#93000a] px-6 py-3 text-sm font-bold text-[#ffdad6] transition hover:bg-danger hover:text-[#690005] disabled:opacity-60 md:px-8"
            disabled={deleting}
            onClick={() => setDeleteDialogOpen(true)}
            type="button"
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            Delete My Account
          </button>
        </div>
      </section>

      <div className="fixed bottom-20 left-4 right-4 z-40 lg:bottom-8 lg:left-[19rem] lg:right-8">
        <div className="glass-panel glow-border flex flex-col gap-3 rounded-2xl p-4 shadow-2xl sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 px-1 text-sm text-muted">
            <Check className={cx('h-4 w-4', dirty ? 'text-warning' : 'text-success')} />
            <span>{dirty ? 'Cambios sin guardar' : lastSavedAt ? `Guardado a las ${lastSavedAt}` : 'Sin cambios pendientes'}</span>
          </div>
          <div className="flex gap-3">
            <button
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-text disabled:opacity-50 sm:flex-none sm:px-6"
              disabled={!dirty || saving}
              onClick={discardChanges}
              type="button"
            >
              <RotateCcw className="h-4 w-4" />
              Discard
            </button>
            <button
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-[#23005c] shadow-glow transition hover:bg-primary/90 disabled:opacity-60 sm:flex-none sm:px-8"
              disabled={!dirty || saving}
              type="submit"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Apply Changes
            </button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        confirmLabel="Eliminar cuenta"
        loading={deleting}
        message={`Se borraran proveedores, productos, analisis, campanas, logs y trabajos de "${activeProfile.name}". Esta accion no se puede deshacer.`}
        onCancel={() => setDeleteDialogOpen(false)}
        onConfirm={() => void confirmDeleteAccount()}
        open={deleteDialogOpen}
        title="Eliminar cuenta"
      />
    </form>
  )
}
