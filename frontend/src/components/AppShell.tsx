import {
  BarChart3,
  Bell,
  ChevronRight,
  HelpCircle,
  LayoutDashboard,
  Mail,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'
import ProfileAvatar from './ProfileAvatar'
import { useProfile } from '../hooks/useProfile'
import { cx } from '../utils/classNames'

type AppShellProps = {
  children: ReactNode
}

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/dashboard' },
  { label: 'Email', icon: Mail, to: '/emails' },
  { label: 'Productos', icon: BarChart3, to: '/ranking' },
  { label: 'Ajustes', icon: Settings, to: '/settings' },
]

function navClass({ isActive }: { isActive: boolean }) {
  return cx(
    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition',
    isActive ? 'border-r-2 border-primary bg-white/5 text-primary' : 'text-muted hover:bg-white/5 hover:text-text',
  )
}

export default function AppShell({ children }: AppShellProps) {
  const { activeProfile } = useProfile()

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
              className="flex w-full items-center gap-3 rounded-lg border border-outline/40 bg-white/[0.03] p-3 transition hover:border-primary/50 hover:bg-white/[0.06]"
              to="/profiles"
            >
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
          <button className="relative rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-primary" type="button">
            <span className="sr-only">Notificaciones</span>
            <Bell className="h-5 w-5" />
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger" />
          </button>
          <button className="rounded-lg p-2 text-muted transition hover:bg-white/5 hover:text-primary" type="button">
            <span className="sr-only">Ayuda</span>
            <HelpCircle className="h-5 w-5" />
          </button>
          {activeProfile ? (
            <Link className="hidden items-center gap-2 rounded-full border border-outline/40 bg-panelHigh/70 py-1 pl-1 pr-3 transition hover:border-primary/50 sm:flex" to="/profiles">
              <ProfileAvatar avatarDataUrl={activeProfile.avatar_data_url} className="h-8 w-8 text-xs" name={activeProfile.name} />
              <span className="max-w-32 truncate text-sm font-semibold text-text">{activeProfile.name}</span>
            </Link>
          ) : null}
        </div>
      </header>

      <main className="min-h-screen min-w-0 overflow-x-hidden px-4 pb-24 pt-20 lg:ml-72 lg:px-8 lg:pb-12">{children}</main>

      <nav className="fixed bottom-0 left-0 z-50 grid w-[100vw] max-w-[100vw] grid-cols-4 overflow-hidden border-t border-outline/40 bg-panel/90 px-2 py-2 backdrop-blur-xl lg:hidden">
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
