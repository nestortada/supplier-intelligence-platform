import {
  BarChart3,
  Bell,
  ChevronRight,
  CheckCheck,
  CheckSquare,
  HelpCircle,
  LayoutDashboard,
  Mail,
  Search,
  Settings,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { fetchCampaigns } from '../api/emailApi'
import { fetchJobs } from '../api/opportunityApi'
import ProfileAvatar from './ProfileAvatar'
import { useProfile } from '../hooks/useProfile'
import { useRealtimeEvents } from '../hooks/useRealtimeEvents'
import { useToast } from '../hooks/useToast'
import type { CampaignSummary } from '../types/api'
import type { JobStatus } from '../types/opportunity'
import type { RealtimeEvent } from '../types/realtime'
import { cx } from '../utils/classNames'
import { formatDateTime } from '../utils/format'

type AppShellProps = {
  children: ReactNode
}

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/dashboard' },
  { label: 'Email', icon: Mail, to: '/emails' },
  { label: 'Productos', icon: BarChart3, to: '/ranking' },
  { label: 'Seleccionados', icon: CheckSquare, to: '/seleccionados' },
  { label: 'Ajustes', icon: Settings, to: '/settings' },
]

const WATCHED_WORK_STORAGE_KEY = 'supplierintel.watchedWork'
const NOTIFIED_WORK_STORAGE_KEY = 'supplierintel.notifiedWork'
const terminalStatuses = new Set(['completed', 'failed', 'error', 'canceled'])
const activeStatuses = new Set(['pending', 'in_progress'])

function readStringSet(key: string): Set<string> {
  try {
    const raw = window.localStorage.getItem(key)
    const parsed = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(parsed) ? parsed : [])
  } catch {
    return new Set()
  }
}

function writeStringSet(key: string, values: Set<string>) {
  window.localStorage.setItem(key, JSON.stringify(Array.from(values).slice(-200)))
}

function scopedWorkKey(profileId: number, type: string, id: number): string {
  return `${profileId}:${type}:${id}`
}

function describeCampaign(campaign: CampaignSummary): { title: string; message: string; tone: 'success' | 'error' | 'info'; href: string } {
  if (campaign.status === 'completed') {
    return {
      href: '/emails',
      tone: 'success',
      title: 'Mensajes enviados',
      message: `${campaign.sent} enviados, ${campaign.failed} fallidos, ${campaign.total} proveedores procesados.`,
    }
  }

  if (campaign.status === 'canceled') {
    return {
      href: '/emails',
      tone: 'info',
      title: 'Campana cancelada',
      message: `${campaign.sent + campaign.failed} de ${campaign.total} proveedores procesados.`,
    }
  }

  return {
    href: '/emails',
    tone: 'error',
    title: 'Campana finalizada con errores',
    message: `${campaign.sent} enviados y ${campaign.failed} fallidos.`,
  }
}

function describeAnalysisJob(job: JobStatus): { title: string; message: string; tone: 'success' | 'error' | 'info'; href: string } {
  if (job.status === 'completed') {
    return {
      href: '/ranking',
      tone: 'success',
      title: 'Analisis de productos terminado',
      message: `${job.processed_items}/${job.total_items} productos analizados.`,
    }
  }

  if (job.status === 'canceled') {
    return {
      href: '/ranking',
      tone: 'info',
      title: 'Analisis cancelado',
      message: `${job.processed_items}/${job.total_items} productos procesados.`,
    }
  }

  return {
    href: '/ranking',
    tone: 'error',
    title: 'Analisis de productos con errores',
    message: job.error_message || `${job.failed_items} productos fallaron.`,
  }
}

function navClass({ isActive }: { isActive: boolean }) {
  return cx(
    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition',
    isActive ? 'border-r-2 border-primary bg-white/5 text-primary' : 'text-muted hover:bg-white/5 hover:text-text',
  )
}

export default function AppShell({ children }: AppShellProps) {
  const { activeProfile } = useProfile()
  const { addToast, clearNotifications, markNotificationRead, markNotificationsRead, notifications, unreadCount } = useToast()
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const notificationsRef = useRef<HTMLDivElement | null>(null)
  const navigate = useNavigate()

  const currentProfileUnreadCount = useMemo(
    () => notifications.filter((notification) => !notification.read && notification.profileId === activeProfile?.id).length,
    [activeProfile?.id, notifications],
  )

  const openNotifications = useCallback(() => {
    setNotificationsOpen((current) => !current)
  }, [])

  const handleNotificationClick = useCallback(
    (notificationId: string, href?: string) => {
      markNotificationRead(notificationId)
      setNotificationsOpen(false)
      if (href) {
        navigate(href)
      }
    },
    [markNotificationRead, navigate],
  )

  const handleRealtimeEvent = useCallback(
    (event: RealtimeEvent) => {
      if (!activeProfile || (event.profile_id !== null && event.profile_id !== activeProfile.id)) {
        return
      }

      if (event.type === 'job.updated') {
        const job = event.payload as Partial<JobStatus>
        if (!job.job_id || !job.type || !job.status || !terminalStatuses.has(job.status)) {
          return
        }
        const jobKey = scopedWorkKey(activeProfile.id, String(job.type), Number(job.job_id))
        const notified = readStringSet(NOTIFIED_WORK_STORAGE_KEY)
        if (notified.has(jobKey)) {
          return
        }
        const notification = describeAnalysisJob({
          job_id: Number(job.job_id),
          type: String(job.type),
          status: String(job.status),
          progress: Number(job.progress ?? 100),
          total_items: Number(job.total_items ?? 0),
          processed_items: Number(job.processed_items ?? 0),
          failed_items: Number(job.failed_items ?? 0),
          error_message: typeof job.error_message === 'string' ? job.error_message : null,
          created_at: new Date().toISOString(),
          updated_at: typeof job.updated_at === 'string' ? job.updated_at : new Date().toISOString(),
        })
        addToast({ ...notification, profileId: activeProfile.id, profileName: activeProfile.name })
        notified.add(jobKey)
        writeStringSet(NOTIFIED_WORK_STORAGE_KEY, notified)
      }

      if (event.type === 'email_campaign.updated') {
        const campaign = event.payload as Partial<CampaignSummary>
        if (!campaign.campaign_id || !campaign.status || !terminalStatuses.has(campaign.status)) {
          return
        }
        const campaignKey = scopedWorkKey(activeProfile.id, 'campaign', Number(campaign.campaign_id))
        const notified = readStringSet(NOTIFIED_WORK_STORAGE_KEY)
        if (notified.has(campaignKey)) {
          return
        }
        const notification = describeCampaign({
          campaign_id: Number(campaign.campaign_id),
          status: String(campaign.status),
          total: Number(campaign.total ?? 0),
          sent: Number(campaign.sent ?? 0),
          failed: Number(campaign.failed ?? 0),
          pending: Number(campaign.pending ?? 0),
          subject: typeof campaign.subject === 'string' ? campaign.subject : null,
          template_id: null,
          created_at: new Date().toISOString(),
          updated_at: typeof campaign.updated_at === 'string' ? campaign.updated_at : new Date().toISOString(),
        })
        addToast({ ...notification, profileId: activeProfile.id, profileName: activeProfile.name })
        notified.add(campaignKey)
        writeStringSet(NOTIFIED_WORK_STORAGE_KEY, notified)
      }
    },
    [activeProfile, addToast],
  )

  useRealtimeEvents(activeProfile?.id, handleRealtimeEvent)

  useEffect(() => {
    if (!notificationsOpen) {
      return undefined
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target
      if (target instanceof Node && notificationsRef.current && !notificationsRef.current.contains(target)) {
        setNotificationsOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [notificationsOpen])

  useEffect(() => {
    if (!activeProfile) {
      return undefined
    }

    let cancelled = false

    const pollFinishedWork = async () => {
      try {
        const [campaignsResult, analysisJobsResult] = await Promise.allSettled([
          fetchCampaigns(),
          fetchJobs({ type: 'product_analysis' }),
        ])

        if (cancelled) {
          return
        }

        const watched = readStringSet(WATCHED_WORK_STORAGE_KEY)
        const notified = readStringSet(NOTIFIED_WORK_STORAGE_KEY)

        if (campaignsResult.status === 'fulfilled') {
          campaignsResult.value.items.forEach((campaign) => {
            const key = scopedWorkKey(activeProfile.id, 'campaign', campaign.campaign_id)
            if (activeStatuses.has(campaign.status)) {
              watched.add(key)
              return
            }

            if (terminalStatuses.has(campaign.status) && watched.has(key) && !notified.has(key)) {
              const notification = describeCampaign(campaign)
              addToast({ ...notification, profileId: activeProfile.id, profileName: activeProfile.name })
              watched.delete(key)
              notified.add(key)
            }
          })
        }

        if (analysisJobsResult.status === 'fulfilled') {
          analysisJobsResult.value.forEach((job) => {
            const key = scopedWorkKey(activeProfile.id, 'product_analysis', job.job_id)
            if (activeStatuses.has(job.status)) {
              watched.add(key)
              return
            }

            if (terminalStatuses.has(job.status) && watched.has(key) && !notified.has(key)) {
              const notification = describeAnalysisJob(job)
              addToast({ ...notification, profileId: activeProfile.id, profileName: activeProfile.name })
              watched.delete(key)
              notified.add(key)
            }
          })
        }

        writeStringSet(WATCHED_WORK_STORAGE_KEY, watched)
        writeStringSet(NOTIFIED_WORK_STORAGE_KEY, notified)
      } catch {
        // Regular page-level loaders still surface API errors.
      }
    }

    void pollFinishedWork()
    const interval = window.setInterval(() => {
      void pollFinishedWork()
    }, 3000)

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [activeProfile, addToast])

  return (
    <div className="min-h-screen bg-background text-text">
      <aside className="fixed left-0 top-0 z-50 hidden h-screen w-72 flex-col border-r border-outline/40 bg-panel/70 px-4 py-6 backdrop-blur-3xl lg:flex">
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primaryStrong text-[#24005f] shadow-glow">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <p className="font-display text-xl font-bold text-primary">SupplierIntel</p>
            <p className="text-xs font-semibold uppercase text-muted">Portal ejecutivo</p>
          </div>
        </div>

        <nav className="custom-scrollbar flex-1 space-y-1 overflow-y-auto pr-1">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink className={navClass} key={item.label} to={item.to}>
                <Icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>

        {activeProfile ? (
          <div className="border-t border-outline/40 pt-4">
            <Link
              className="relative flex w-full items-center gap-3 rounded-lg border border-outline/40 bg-white/[0.03] p-3 transition hover:border-primary/50 hover:bg-white/[0.06]"
              to="/profiles"
            >
              {currentProfileUnreadCount > 0 ? <span className="absolute right-3 top-3 h-2.5 w-2.5 rounded-full bg-danger ring-2 ring-panel" /> : null}
              <ProfileAvatar avatarDataUrl={activeProfile.avatar_data_url} className="h-10 w-10" name={activeProfile.name} />
              <div className="min-w-0 flex-1 text-left">
                <p className="truncate text-sm font-semibold text-text">{activeProfile.name}</p>
                <p className="text-xs text-muted">Cambiar perfil</p>
              </div>
              <ChevronRight className="h-4 w-4 text-muted" />
            </Link>
          </div>
        ) : null}
      </aside>

      <header className="fixed left-0 top-0 z-40 flex h-16 w-full items-center justify-between border-b border-outline/30 bg-background/85 px-4 backdrop-blur-xl lg:left-72 lg:w-[calc(100%-18rem)] lg:px-8">
        <div className="flex items-center gap-3 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primaryStrong text-[#24005f]">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="font-display text-lg font-bold text-primary">SupplierIntel</span>
        </div>

        <div className="hidden w-72 items-center rounded-full border border-outline/40 bg-panelHigh/70 px-3 py-2 lg:flex">
          <Search className="mr-2 h-4 w-4 text-muted" />
          <input
            className="w-full border-0 bg-transparent p-0 text-sm text-text placeholder:text-muted focus:outline-none focus:ring-0"
            placeholder="Buscar..."
            type="search"
          />
        </div>

        <div className="ml-auto hidden items-center gap-3 sm:flex">
          <div className="relative" ref={notificationsRef}>
            <button
              className="relative rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-primary"
              onClick={openNotifications}
              type="button"
            >
              <span className="sr-only">Notificaciones</span>
              <Bell className="h-5 w-5" />
              {unreadCount > 0 ? <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger" /> : null}
            </button>
            {notificationsOpen ? (
              <div className="absolute right-0 top-12 z-[90] w-[min(24rem,calc(100vw-2rem))] rounded-xl border border-outline/40 bg-panelHigh p-4 shadow-glow">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-text">Notificaciones</p>
                    <p className="text-xs text-muted">{unreadCount} sin leer</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      className="rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-primary"
                      onClick={() => markNotificationsRead(activeProfile?.id)}
                      type="button"
                    >
                      <span className="sr-only">Marcar como leidas</span>
                      <CheckCheck className="h-4 w-4" />
                    </button>
                    <button
                      className="rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-danger"
                      onClick={clearNotifications}
                      type="button"
                    >
                      <span className="sr-only">Limpiar notificaciones</span>
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="custom-scrollbar max-h-80 space-y-2 overflow-y-auto pr-1">
                  {notifications.length === 0 ? (
                    <div className="rounded-lg border border-outline/40 bg-background/50 p-4 text-sm text-muted">
                      No hay notificaciones todavia.
                    </div>
                  ) : (
                    notifications.map((notification) => (
                      <button
                        className={cx(
                          'block w-full rounded-lg border bg-background/50 p-3 text-left transition hover:border-primary/40 hover:bg-white/[0.04]',
                          notification.read ? 'border-outline/30' : 'border-danger/30',
                        )}
                        key={notification.id}
                        onClick={() => handleNotificationClick(notification.id, notification.href)}
                        type="button"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-sm font-semibold text-text">{notification.title}</p>
                          {!notification.read ? <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-danger" /> : null}
                        </div>
                        <p className="mt-1 text-[11px] font-semibold uppercase text-primary">
                          Perfil: {notification.profileName || 'Perfil actual'}
                        </p>
                        {notification.message ? <p className="mt-1 text-xs text-muted">{notification.message}</p> : null}
                        <div className="mt-2 flex items-center justify-between gap-3 text-[10px] uppercase text-muted">
                          <span>{formatDateTime(notification.createdAt)}</span>
                          {notification.href ? <span>Abrir</span> : null}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            ) : null}
          </div>
          <button className="rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-primary" type="button">
            <span className="sr-only">Ayuda</span>
            <HelpCircle className="h-5 w-5" />
          </button>
          {activeProfile ? (
            <Link className="relative hidden items-center gap-2 rounded-full border border-outline/40 bg-panelHigh/70 py-1 pl-1 pr-3 transition hover:border-primary/50 sm:flex" to="/profiles">
              {currentProfileUnreadCount > 0 ? <span className="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-danger ring-2 ring-panelHigh" /> : null}
              <ProfileAvatar avatarDataUrl={activeProfile.avatar_data_url} className="h-8 w-8 text-xs" name={activeProfile.name} />
              <span className="max-w-32 truncate text-sm font-semibold text-text">{activeProfile.name}</span>
            </Link>
          ) : null}
        </div>
      </header>

      <main className="min-h-screen min-w-0 overflow-x-hidden px-4 pb-24 pt-20 lg:ml-72 lg:px-8 lg:pb-12">{children}</main>

      <nav className="fixed bottom-0 left-0 z-50 grid w-[100vw] max-w-[100vw] grid-cols-5 overflow-hidden border-t border-outline/40 bg-panel/90 px-2 py-2 backdrop-blur-xl lg:hidden">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              className={({ isActive }) =>
                cx(
                  'flex min-w-0 flex-col items-center gap-1 rounded-lg px-0.5 py-2 text-[10px] font-medium transition sm:px-2 sm:text-xs',
                  isActive ? 'bg-white/5 text-primary' : 'text-muted hover:text-text',
                )
              }
              key={item.label}
              to={item.to}
            >
              <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
              <span className="max-w-full truncate">{item.label}</span>
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}
