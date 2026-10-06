import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from '@tanstack/react-router'
import { ArrowLeft, Clock3, FileText, Fingerprint, Inbox, UserRound } from 'lucide-react'
import { api } from '../api/client'
import { ErrorState, LoadingState } from '../ui/feedback'
import { PageHeading } from '../ui/page-heading'
import { StatusBadge } from '../ui/status-badge'

const dateTime = (value: string | null | undefined) => value ? new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'

export function JobDetailPage() {
  const { jobId } = useParams({ strict: false }) as { jobId: string }
  const query = useQuery({ queryKey: ['job', jobId], queryFn: () => api.job(jobId), enabled: Boolean(jobId) })
  return <>
    <Link to="/mail" className="mb-5 inline-flex items-center gap-2 text-xs font-semibold text-slate-500 transition hover:text-brand"><ArrowLeft className="size-4" />К списку писем</Link>
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState message={`Не удалось открыть письмо: ${query.error.message}`} /> : <>
      <PageHeading title={query.data.subject || '(без темы)'} description={`${query.data.sender || 'Отправитель неизвестен'} · ${dateTime(query.data.received_at || query.data.created_at)}`} action={<StatusBadge status={query.data.status} />} />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(280px,.8fr)]">
        <div className="space-y-5">
          <section className="surface overflow-hidden">
            <div className="flex items-center gap-2 border-b border-line px-5 py-4"><FileText className="size-4 text-brand" /><h2 className="text-sm font-bold">Содержимое письма</h2></div>
            {query.data.email ? <div className="p-5">
              <div className="mb-4 grid gap-3 rounded-xl bg-slate-50 p-4 text-xs sm:grid-cols-2">
                <div><span className="text-slate-400">Отправитель</span><div className="mt-1 break-all font-semibold text-slate-700">{query.data.email.sender || '—'}</div></div>
                <div><span className="text-slate-400">Получено</span><div className="mt-1 font-semibold text-slate-700">{dateTime(query.data.email.received_at)}</div></div>
              </div>
              <pre className="max-h-[560px] overflow-auto whitespace-pre-wrap break-words font-sans text-sm leading-7 text-slate-700">{query.data.email.body || '(пустое тело письма)'}</pre>
              <p className="mt-5 border-t border-line pt-3 text-[11px] text-slate-400">Снимок автоматически удаляется {dateTime(query.data.email.expires_at)}</p>
            </div> : <div className="p-8 text-center text-sm text-muted">Снимок письма уже удалён или недоступен.</div>}
          </section>
          <section className="surface overflow-hidden">
            <div className="flex items-center gap-2 border-b border-line px-5 py-4"><Clock3 className="size-4 text-brand" /><h2 className="text-sm font-bold">История обработки</h2></div>
            {query.data.audit.length ? <div className="divide-y divide-line">{query.data.audit.map((entry, index) => <div key={`${entry.action}-${entry.created_at}-${index}`} className="flex gap-4 p-5">
              <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-brand"><span className="text-xs font-bold">{index + 1}</span></span>
              <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-semibold">{entry.action}</span><span className="text-[11px] text-slate-400">{dateTime(entry.created_at)}</span></div>{entry.error && <p className="mt-2 rounded-lg bg-rose-50 p-3 text-xs text-rose-700">{entry.error}</p>}{Object.keys(entry.details).length > 0 && <pre className="mt-2 overflow-auto rounded-lg bg-slate-50 p-3 text-[11px] leading-5 text-slate-600">{JSON.stringify(entry.details, null, 2)}</pre>}</div>
            </div>)}</div> : <div className="p-8 text-center text-sm text-muted">Записей аудита пока нет.</div>}
          </section>
        </div>
        <aside className="space-y-5">
          <section className="surface p-5">
            <h2 className="text-sm font-bold">Карточка задачи</h2>
            <dl className="mt-4 space-y-4 text-xs">
              <div className="flex items-start gap-3"><Fingerprint className="mt-0.5 size-4 text-slate-400" /><div className="min-w-0"><dt className="text-slate-400">Идентификатор письма</dt><dd className="mt-1 break-all font-mono text-[11px] text-slate-700">{query.data.provider_message_id}</dd></div></div>
              <div className="flex items-start gap-3"><Inbox className="mt-0.5 size-4 text-slate-400" /><div><dt className="text-slate-400">Провайдер / тип</dt><dd className="mt-1 font-semibold text-slate-700">{query.data.provider} · {query.data.type}</dd></div></div>
              <div className="flex items-start gap-3"><UserRound className="mt-0.5 size-4 text-slate-400" /><div><dt className="text-slate-400">Целевая папка</dt><dd className="mt-1 font-semibold text-slate-700">{query.data.destination_id || 'Не назначена'}</dd></div></div>
              <div className="border-t border-line pt-3"><dt className="text-slate-400">Попытки</dt><dd className="mt-1 font-semibold text-slate-700">{query.data.attempts} из {query.data.max_attempts}</dd></div>
              <div><dt className="text-slate-400">Создана</dt><dd className="mt-1 font-semibold text-slate-700">{dateTime(query.data.created_at)}</dd></div>
              {query.data.last_error && <div><dt className="text-slate-400">Последняя ошибка</dt><dd className="mt-1 rounded-lg bg-rose-50 p-3 text-rose-700">{query.data.last_error}</dd></div>}
            </dl>
          </section>
          <section className="surface p-5">
            <h2 className="text-sm font-bold">Технические данные</h2>
            <pre className="mt-3 overflow-auto rounded-xl bg-slate-50 p-3 text-[10px] leading-5 text-slate-600">{JSON.stringify(query.data.payload, null, 2)}</pre>
          </section>
        </aside>
      </div>
    </>}
  </>
}
