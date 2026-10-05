import { useQuery } from '@tanstack/react-query'
import { ArrowRight, CheckCheck, CircleAlert, Clock3, FolderOpen, MailCheck, RefreshCw, Workflow } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { api } from '../api/client'
import { ErrorState, LoadingState } from '../ui/feedback'
import { JobTable } from '../ui/job-table'
import { PageHeading } from '../ui/page-heading'

const metrics = [
  { key: 'processing', label: 'В обработке', icon: Workflow, color: 'text-blue-600 bg-blue-50', note: 'активные задачи' },
  { key: 'review', label: 'Нужна проверка', icon: CircleAlert, color: 'text-amber-600 bg-amber-50', note: 'ждут решения' },
  { key: 'completed', label: 'Обработано', icon: CheckCheck, color: 'text-emerald-600 bg-emerald-50', note: 'успешные задачи' },
  { key: 'failed', label: 'Ошибки', icon: Clock3, color: 'text-rose-600 bg-rose-50', note: 'требуют внимания' },
] as const

export function DashboardPage() {
  const query = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard, refetchInterval: 30_000 })
  return <>
    <PageHeading title="Обзор системы" description="Почта, классификация и маршрутизация — текущее состояние." action={<button onClick={() => void query.refetch()} className="focus-ring inline-flex h-10 items-center gap-2 rounded-xl border border-line bg-white px-3.5 text-xs font-semibold text-slate-600 transition hover:border-slate-300"><RefreshCw className={`size-3.5 ${query.isFetching ? 'animate-spin' : ''}`} />Обновить</button>} />
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState message={`Не удалось загрузить обзор: ${query.error.message}`} /> : <>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(metric => {
          const Icon = metric.icon
          return <div key={metric.key} className="surface p-5">
            <div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-500">{metric.label}</span><span className={`flex size-9 items-center justify-center rounded-xl ${metric.color}`}><Icon className="size-[18px]" /></span></div>
            <div className="mt-4 flex items-end justify-between"><span className="text-3xl font-bold tracking-tight text-ink">{query.data.jobs[metric.key]}</span><span className="pb-1 text-[11px] text-slate-400">{metric.note}</span></div>
          </div>
        })}
      </div>

      <div className="mb-6 grid gap-4 xl:grid-cols-[1.7fr_1fr]">
        <section className="surface overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6">
            <div><h2 className="text-sm font-bold">Последние письма</h2><p className="mt-1 text-xs text-muted">Недавняя активность обработки</p></div>
            <Link to="/mail" className="inline-flex items-center gap-1.5 text-xs font-bold text-brand hover:text-indigo-700">Все письма <ArrowRight className="size-3.5" /></Link>
          </div>
          <JobTable rows={query.data.recent_jobs} />
        </section>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <section className="surface flex items-start gap-4 p-5">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-brand"><FolderOpen className="size-5" /></span>
            <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-slate-500">Активные назначения</p><div className="mt-1 text-2xl font-bold">{query.data.destinations}</div><Link to="/destinations" className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand">Посмотреть папки <ArrowRight className="size-3.5" /></Link></div>
          </section>
          <section className={`surface flex items-start gap-4 p-5 ${query.data.pending_alerts ? 'border-rose-100' : ''}`}>
            <span className={`flex size-11 shrink-0 items-center justify-center rounded-xl ${query.data.pending_alerts ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'}`}><MailCheck className="size-5" /></span>
            <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-slate-500">Критические уведомления</p><div className="mt-1 text-2xl font-bold">{query.data.pending_alerts}</div><p className="mt-2 text-xs text-muted">{query.data.pending_alerts ? 'Есть события, ожидающие отправки.' : 'Новых событий нет.'}</p></div>
          </section>
          <section className="hidden rounded-2xl bg-gradient-to-br from-[#5964e9] to-[#7981f4] p-5 text-white xl:block">
            <div className="flex items-center gap-2 text-sm font-bold"><Workflow className="size-4" />Конвейер обработки</div>
            <div className="mt-5 flex items-center justify-between text-center">
              {['Почта', 'AI', 'Папка'].map((step, index) => <div key={step} className="flex flex-1 items-center"><div className="flex flex-1 flex-col items-center"><span className="flex size-8 items-center justify-center rounded-full bg-white/20 text-xs font-bold">{index + 1}</span><span className="mt-2 text-[11px] text-white/80">{step}</span></div>{index < 2 && <span className="-mt-5 h-px flex-1 bg-white/30" />}</div>)}
            </div>
            <p className="mt-5 text-xs leading-5 text-white/75">Новые обращения проходят через Collector, Decision и Router.</p>
          </section>
        </div>
      </div>
    </>}
  </>
}
