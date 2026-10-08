import { useDeferredValue, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, FileSearch, Search, X } from 'lucide-react'
import { api } from '../api/client'
import { ErrorState, LoadingState } from '../ui/feedback'
import { PageHeading } from '../ui/page-heading'

const dateTime = (value: string) => new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'medium' }).format(new Date(value))

function levelStyle(level: string) {
  if (['error', 'critical', 'fatal'].includes(level)) return 'bg-rose-50 text-rose-700'
  if (level === 'warning') return 'bg-amber-50 text-amber-700'
  return 'bg-slate-100 text-slate-600'
}

export function SystemLogsPage() {
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const deferredSearch = useDeferredValue(search)
  const query = useQuery({ queryKey: ['system-logs', deferredSearch, offset], queryFn: () => api.systemLogs(deferredSearch, offset) })

  return <>
    <PageHeading title="Логи сервисов" description="Технические логи приложений из PostgreSQL: ошибки, предупреждения и события запуска. Хранятся 30 дней." />
    <section className="surface overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center sm:px-5">
        <label className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={event => { setSearch(event.target.value); setOffset(0) }} placeholder="Сообщение, сервис или logger" className="focus-ring h-10 w-full rounded-xl border border-line bg-[#fafbfc] pl-9 pr-9 text-sm outline-none transition placeholder:text-slate-400 focus:border-brand-accent focus:bg-white" />
          {search && <button onClick={() => { setSearch(''); setOffset(0) }} className="absolute right-2 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100" aria-label="Очистить поиск"><X className="size-4" /></button>}
        </label>
      </div>
      <div className="flex items-center justify-between px-5 py-3 text-xs text-muted"><span>{query.data ? `${query.data.total.toLocaleString('ru-RU')} записей` : 'Загрузка логов…'}</span><span>Подробные логи контейнера: docker compose logs</span></div>
      {query.isPending ? <div className="p-4"><LoadingState label="Загружаем логи…" /></div> : query.isError ? <div className="p-4"><ErrorState message={`Не удалось загрузить логи: ${query.error.message}`} /></div> : query.data.items.length === 0 ? <div className="px-6 py-16 text-center"><FileSearch className="mx-auto size-8 text-slate-300" /><p className="mt-3 text-sm font-semibold text-slate-600">Логи не найдены</p><p className="mt-1 text-xs text-muted">Попробуйте изменить поисковый запрос.</p></div> : <div className="divide-y divide-line">
        {query.data.items.map(item => <article key={item.id} className="grid gap-3 px-5 py-4 lg:grid-cols-[170px_minmax(0,1fr)_auto] lg:items-start">
          <div className="text-xs text-slate-500">{dateTime(item.created_at)}</div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-brand-soft px-2 py-1 text-[10px] font-bold text-brand">{item.service}</span>
              <span className="font-mono text-[10px] text-slate-500">{item.logger}</span>
              <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${levelStyle(item.level)}`}>{item.level}</span>
            </div>
            <p className="mt-2 whitespace-pre-wrap break-words text-sm text-ink">{item.message}</p>
            {item.exception && <pre className="mt-3 max-h-96 overflow-auto rounded-lg bg-rose-50 p-3 text-xs leading-5 text-rose-700">{item.exception}</pre>}
            {Object.keys(item.context).length > 0 && <details className="mt-3">
              <summary className="cursor-pointer text-xs font-semibold text-slate-500 hover:text-brand">Контекст</summary>
              <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-slate-50 p-3 text-[11px] leading-5 text-slate-600">{JSON.stringify(item.context, null, 2)}</pre>
            </details>}
          </div>
        </article>)}
      </div>}
      <div className="flex items-center justify-between border-t border-line px-5 py-3">
        <span className="text-xs text-muted">Страница {Math.floor(offset / 50) + 1}</span>
        <div className="flex gap-2">
          <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))} className="focus-ring flex h-8 items-center gap-1 rounded-lg border border-line px-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft className="size-3.5" />Назад</button>
          <button disabled={!query.data || offset + query.data.items.length >= query.data.total} onClick={() => setOffset(offset + 50)} className="focus-ring flex h-8 items-center gap-1 rounded-lg border border-line px-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40">Дальше<ChevronRight className="size-3.5" /></button>
        </div>
      </div>
    </section>
  </>
}
