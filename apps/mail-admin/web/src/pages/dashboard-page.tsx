import { useQuery } from '@tanstack/react-query'
import { ArrowRight, CheckCheck, CircleAlert, Clock3, FolderOpen, MailCheck, RefreshCw, Workflow } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { api } from '../api/client'
import { ErrorState, LoadingState } from '../ui/feedback'
import { JobTable } from '../ui/job-table'
import { PageHeading } from '../ui/page-heading'

const metrics = [
  { key: 'processing', label: 'В обработке', icon: Workflow, color: 'text-blue-600 bg-blue-50', note: 'заданий сейчас', description: 'Задания, которые сейчас обрабатываются сервисами Mail Sort.' },
  { key: 'review', label: 'Ручная проверка', icon: CircleAlert, color: 'text-amber-600 bg-amber-50', note: 'заданий ждут проверки', description: 'AI не смог уверенно выбрать папку. Эти задания помечены для ручной проверки.' },
  { key: 'completed', label: 'Обработано', icon: CheckCheck, color: 'text-emerald-600 bg-emerald-50', note: 'заданий завершено', description: 'Задания, обработка которых завершилась успешно.' },
  { key: 'failed', label: 'Ошибки', icon: Clock3, color: 'text-rose-600 bg-rose-50', note: 'заданий с ошибкой', description: 'Задания, которые завершились ошибкой после исчерпания попыток.' },
] as const

export function DashboardPage() {
  const query = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard, refetchInterval: 30_000 })
  return <>
    <PageHeading title="Обзор системы" description="Количество заданий очереди по статусам. Счётчики обновляются каждые 30 секунд." action={<button onClick={() => void query.refetch()} className="focus-ring inline-flex h-10 items-center gap-2 rounded-xl border border-line bg-white px-3.5 text-xs font-semibold text-slate-600 transition hover:border-slate-300"><RefreshCw className={`size-3.5 ${query.isFetching ? 'animate-spin' : ''}`} />Обновить</button>} />
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState message={`Не удалось загрузить обзор: ${query.error.message}`} /> : <>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(metric => {
          const Icon = metric.icon
          return <div key={metric.key} className="surface p-5">
            <div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-500">{metric.label}</span><span title={metric.description} aria-label={metric.description} tabIndex={0} className={`group relative flex size-9 cursor-help items-center justify-center rounded-xl ${metric.color}`}><Icon className="size-[18px]" /><span role="tooltip" className="pointer-events-none absolute right-0 top-full z-20 mt-2 w-56 rounded-lg bg-slate-900 px-3 py-2 text-left text-[11px] font-medium leading-5 text-white opacity-0 shadow-lg transition group-hover:opacity-100 group-focus:opacity-100">{metric.description}</span></span></div>
            <div className="mt-4 flex items-end justify-between"><span className="text-3xl font-bold tracking-tight text-ink">{query.data.jobs[metric.key]}</span><span className="pb-1 text-[11px] text-slate-400">{metric.note}</span></div>
          </div>
        })}
      </div>

      <div className="mb-6 grid gap-4 xl:grid-cols-[1.7fr_1fr]">
        <section className="surface overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-6">
            <div><h2 className="text-sm font-bold">Последние письма</h2><p className="mt-1 text-xs text-muted">Недавняя активность обработки</p></div>
            <Link to="/mail" className="inline-flex items-center gap-1.5 text-xs font-bold text-brand hover:text-brand-dark">Все письма <ArrowRight className="size-3.5" /></Link>
          </div>
          <JobTable rows={query.data.recent_jobs} />
        </section>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <section className="surface flex items-start gap-4 p-5">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand"><FolderOpen className="size-5" /></span>
            <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-slate-500">Активные папки</p><div className="mt-1 text-2xl font-bold">{query.data.destinations}</div><Link to="/destinations" className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand">Посмотреть папки <ArrowRight className="size-3.5" /></Link></div>
          </section>
          <section className={`surface flex items-start gap-4 p-5 ${query.data.pending_alerts ? 'border-rose-100' : ''}`}>
            <span className={`flex size-11 shrink-0 items-center justify-center rounded-xl ${query.data.pending_alerts ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'}`}><MailCheck className="size-5" /></span>
            <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-slate-500">Критические уведомления</p><div className="mt-1 text-2xl font-bold">{query.data.pending_alerts}</div><p className="mt-2 text-xs text-muted">{query.data.pending_alerts ? 'Есть события, ожидающие отправки.' : 'Новых событий нет.'}</p></div>
          </section>
        </div>
      </div>
    </>}
  </>
}
