import type { ReactNode } from 'react'
import { Activity, ArrowDownLeft, FolderCog, LayoutDashboard, LogOut, Mail, Search, Settings2 } from 'lucide-react'
import { Link, useLocation } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

const navigation = [
  { to: '/', label: 'Обзор', icon: LayoutDashboard },
  { to: '/mail', label: 'Письма', icon: Mail },
  { to: '/destinations', label: 'Назначения', icon: FolderCog },
  { to: '/logs', label: 'Журнал', icon: Activity },
  { to: '/settings', label: 'Настройки', icon: Settings2 },
] as const

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const queryClient = useQueryClient()
  const auth = useQuery({ queryKey: ['auth'], queryFn: api.auth })
  const logout = useMutation({
    mutationFn: api.logout,
    onSettled: () => {
      queryClient.clear()
      queryClient.setQueryData(['auth'], { authenticated: false })
    },
  })
  const active = location.pathname.startsWith('/mail') ? '/mail'
    : location.pathname.startsWith('/destinations') ? '/destinations'
      : location.pathname.startsWith('/logs') ? '/logs'
        : location.pathname.startsWith('/settings') ? '/settings' : '/'
  return <div className="min-h-screen bg-[#f5f7fb] text-ink">
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[252px] flex-col border-r border-line bg-white lg:flex">
      <Link to="/" className="flex h-[76px] items-center gap-3 border-b border-line px-6">
        <span className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#6974f6] to-[#4e57d9] text-white shadow-lg shadow-indigo-200"><ArrowDownLeft className="size-5" /></span>
        <span><span className="block text-sm font-extrabold tracking-tight">mail<span className="text-brand">sort</span></span><span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[.16em] text-slate-400">Control center</span></span>
      </Link>
      <div className="px-4 pt-7">
        <p className="eyebrow mb-3 px-3">Рабочая область</p>
        <nav className="space-y-1">
          {navigation.map(item => {
            const Icon = item.icon
            const selected = active === item.to
            return <Link key={item.to} to={item.to} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-semibold transition ${selected ? 'bg-brand-soft text-brand' : 'text-slate-500 hover:bg-slate-50 hover:text-ink'}`}>
              <Icon className="size-[18px]" strokeWidth={selected ? 2.2 : 1.8} />{item.label}
              {item.to === '/mail' && <span className="ml-auto rounded-md bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">review</span>}
            </Link>
          })}
        </nav>
      </div>
      <div className="mt-auto p-4">
        <button onClick={() => logout.mutate()} disabled={logout.isPending} className="mt-4 flex w-full items-center gap-3 rounded-xl p-2 text-left hover:bg-slate-50 disabled:opacity-60">
          <span className="flex size-9 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">{auth.data?.username?.slice(0, 2).toUpperCase() || 'AD'}</span>
          <span className="min-w-0 flex-1"><span className="block truncate text-xs font-bold">{auth.data?.username || 'Администратор'}</span><span className="mt-0.5 block truncate text-[10px] text-slate-400">Завершить сеанс</span></span><LogOut className="size-4 text-slate-400" />
        </button>
      </div>
    </aside>

    <div className="lg:pl-[252px]">
      <header className="sticky top-0 z-20 flex h-[68px] items-center justify-between border-b border-line bg-white/90 px-5 backdrop-blur-md sm:px-8">
        <div className="flex items-center gap-2 text-sm text-slate-400"><span className="font-semibold text-slate-600">Почтовая система</span><span>/</span><span className="capitalize text-ink">{active === '/' ? 'Обзор' : active.slice(1)}</span></div>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link to="/mail" className="focus-ring hidden h-9 items-center gap-2 rounded-lg border border-line px-3 text-xs text-slate-400 sm:flex"><Search className="size-3.5" />Найти письмо</Link>
        </div>
      </header>
      <main className="mx-auto max-w-[1500px] px-5 pb-24 pt-7 sm:px-8 sm:pt-9 lg:pb-9">{children}</main>
      <nav className="fixed inset-x-0 bottom-0 z-30 flex border-t border-line bg-white px-2 py-2 lg:hidden">
        {navigation.map(item => {
          const Icon = item.icon
          const selected = active === item.to
          return <Link key={item.to} to={item.to} className={`flex flex-1 flex-col items-center gap-1 rounded-lg py-1.5 text-[10px] font-semibold ${selected ? 'text-brand' : 'text-slate-400'}`}><Icon className="size-[18px]" />{item.label}</Link>
        })}
      </nav>
    </div>
  </div>
}
