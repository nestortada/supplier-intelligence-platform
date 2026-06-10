import { AlertCircle, BarChart3, ImagePlus, Loader2, Plus, UserPlus, X } from 'lucide-react'
import { type ChangeEvent, type FormEvent, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ProfileAvatar from '../components/ProfileAvatar'
import { useProfile } from '../hooks/useProfile'
import { useToast } from '../hooks/useToast'
import { cx } from '../utils/classNames'
import type { UserProfile } from '../types/profile'

const MAX_AVATAR_BYTES = 900_000

function roleForIndex(index: number): string {
  const roles = ['Lead Analyst', 'Supply Chain Manager', 'Executive VP', 'Logistics Analyst']
  return roles[index % roles.length]
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(new Error('No se pudo leer la imagen.'))
    reader.readAsDataURL(file)
  })
}

export default function ProfileSelectionPage() {
  const navigate = useNavigate()
  const { addToast } = useToast()
  const { activeProfile, createUserProfile, error, loading, profiles, selectProfile } = useProfile()
  const [modalOpen, setModalOpen] = useState(false)
  const [name, setName] = useState('')
  const [avatarDataUrl, setAvatarDataUrl] = useState<string | null>(null)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const sortedProfiles = useMemo(() => profiles.slice().sort((a, b) => a.id - b.id), [profiles])

  function openDashboard(profile: UserProfile) {
    selectProfile(profile)
    navigate('/dashboard')
  }

  async function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    setAvatarError(null)

    if (!file) {
      setAvatarDataUrl(null)
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
    }
  }

  async function handleCreateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) {
      setAvatarError('El nombre es obligatorio.')
      return
    }

    setSubmitting(true)
    try {
      const profile = await createUserProfile(trimmedName, avatarDataUrl)
      setModalOpen(false)
      setName('')
      setAvatarDataUrl(null)
      addToast({ title: 'Perfil creado', message: profile.name, tone: 'success' })
      navigate('/dashboard')
    } catch (caught) {
      addToast({
        title: 'No se pudo crear el perfil',
        message: caught instanceof Error ? caught.message : 'Intentalo nuevamente.',
        tone: 'error',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black px-6 py-12 text-text">
      <div className="pointer-events-none fixed right-[-12rem] top-[-10rem] h-[36rem] w-[36rem] rounded-full bg-primary/10 blur-[140px]" />
      <div className="pointer-events-none fixed bottom-[-12rem] left-[-10rem] h-[32rem] w-[32rem] rounded-full bg-success/5 blur-[120px]" />

      <section className="relative z-10 mx-auto flex w-full max-w-6xl flex-col items-center">
        <div className="mb-14 text-center">
          <div className="mb-6 flex items-center justify-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/30 bg-primary/20">
              <BarChart3 className="h-6 w-6 text-primary" />
            </div>
            <h2 className="font-display text-3xl font-bold tracking-normal text-primary md:text-4xl">Amazon Intelligence</h2>
          </div>
          <h1 className="font-display text-2xl font-semibold tracking-normal text-text md:text-4xl">
            Who is entering the Command Center?
          </h1>
          <p className="mt-2 text-sm text-muted md:text-lg">Select a profile to access your executive workspace.</p>
        </div>

        {error ? (
          <div className="mb-8 flex items-center gap-2 rounded-lg border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="flex items-center gap-3 text-muted">
            <Loader2 className="h-5 w-5 animate-spin" />
            Cargando perfiles
          </div>
        ) : (
          <div className="grid w-full max-w-5xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {sortedProfiles.map((profile, index) => {
              const isActive = activeProfile?.id === profile.id
              return (
                <button
                  className="group flex min-w-0 flex-col items-center text-center transition-transform duration-200 hover:scale-[1.04] focus:outline-none"
                  key={profile.id}
                  onClick={() => openDashboard(profile)}
                  type="button"
                >
                  <div className="relative mb-6">
                    <div
                      className={cx(
                        'absolute -inset-4 rounded-full blur-2xl transition-opacity',
                        isActive ? 'bg-primary/20 opacity-100' : 'bg-white/5 opacity-0 group-hover:opacity-100',
                      )}
                    />
                    <ProfileAvatar
                      avatarDataUrl={profile.avatar_data_url}
                      className={cx(
                        'relative h-32 w-32 shadow-2xl transition duration-300 lg:h-40 lg:w-40',
                        isActive ? 'ring-4 ring-primary' : 'ring-2 ring-white/10 group-hover:ring-white/30',
                      )}
                      name={profile.name}
                    />
                    <span
                      className={cx(
                        'absolute bottom-2 right-2 h-8 w-8 rounded-full border-4 border-black shadow-lg',
                        index % 2 === 0 ? 'bg-success' : 'bg-zinc-700',
                      )}
                    />
                    {isActive ? (
                      <span className="absolute -right-3 -top-3 rounded-full bg-primary px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[#23005c] shadow-xl">
                        Current
                      </span>
                    ) : null}
                  </div>
                  <h3 className="max-w-full truncate font-display text-xl font-semibold text-text transition group-hover:text-primary md:text-2xl">
                    {profile.name}
                  </h3>
                  <p className="mt-1 text-xs font-medium text-muted md:text-sm">{roleForIndex(index)}</p>
                </button>
              )
            })}
          </div>
        )}

        <div className="mt-16 flex flex-col items-center gap-8">
          <button
            className="inline-flex items-center justify-center gap-3 rounded-full border border-outline/70 px-8 py-3 text-sm font-semibold text-text transition hover:border-primary hover:bg-white/5"
            onClick={() => setModalOpen(true)}
            type="button"
          >
            <UserPlus className="h-4 w-4 text-primary" />
            Add New Profile
          </button>
          <div className="flex flex-wrap justify-center gap-x-10 gap-y-3 border-t border-white/5 pt-6 text-xs font-medium text-muted/60">
            <span>System Status: Optimal</span>
            <span>Security: AES-256</span>
            <span>Support</span>
          </div>
        </div>
      </section>

      {modalOpen ? (
        <div className="fixed inset-0 z-[90] flex items-center justify-center p-6">
          <button
            aria-label="Cerrar modal"
            className="absolute inset-0 bg-black/85 backdrop-blur-xl"
            onClick={() => setModalOpen(false)}
            type="button"
          />
          <section className="glass-panel relative z-10 w-full max-w-lg rounded-2xl border-primary/20 p-6 shadow-2xl sm:p-8">
            <div className="mb-8 flex items-start justify-between gap-4">
              <div>
                <h2 className="flex items-center gap-2 font-display text-2xl font-semibold text-text">
                  <UserPlus className="h-5 w-5 text-primary" />
                  Create New Profile
                </h2>
                <p className="mt-1 text-sm text-muted">Deploy access for a new team member.</p>
              </div>
              <button
                className="rounded-full p-2 text-muted transition hover:bg-white/5 hover:text-text"
                onClick={() => setModalOpen(false)}
                type="button"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form className="space-y-6" onSubmit={(event) => void handleCreateProfile(event)}>
              <div className="flex flex-col items-center gap-3">
                <ProfileAvatar avatarDataUrl={avatarDataUrl} className="h-24 w-24 ring-2 ring-white/10" name={name} />
                <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-outline/70 px-4 py-2 text-sm font-semibold text-muted transition hover:border-primary hover:text-primary">
                  <ImagePlus className="h-4 w-4" />
                  Foto opcional
                  <input accept="image/*" className="sr-only" onChange={(event) => void handleAvatarChange(event)} type="file" />
                </label>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-muted" htmlFor="profile-name">
                  Full Name
                </label>
                <input
                  className="field"
                  id="profile-name"
                  maxLength={120}
                  onChange={(event) => {
                    setName(event.target.value)
                    setAvatarError(null)
                  }}
                  placeholder="e.g. Robert Smith"
                  value={name}
                />
              </div>

              {avatarError ? <p className="text-sm text-danger">{avatarError}</p> : null}

              <div className="flex flex-col gap-3 pt-2">
                <button
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-4 font-bold text-[#23005c] shadow-glow transition hover:bg-primary/90 disabled:opacity-60"
                  disabled={submitting}
                  type="submit"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  Deploy New Profile
                </button>
                <button
                  className="w-full rounded-lg px-4 py-2 text-sm font-semibold text-muted transition hover:bg-white/5 hover:text-text"
                  onClick={() => setModalOpen(false)}
                  type="button"
                >
                  Cancel
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </main>
  )
}
