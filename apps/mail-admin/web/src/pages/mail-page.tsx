import { useDeferredValue, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Search, SlidersHorizontal, X } from 'lucide-react'
import { api } from '../api/client'
import { ErrorState, LoadingState } from '../ui/feedback'
import { JobTable } from '../ui/job-table'
import { PageHeading } from '../ui/page-heading'

const statusOptions = [
  ['', 'Все статусы'],
  ['pending', 'В очереди'],
  ['processing', 'Обрабатывается'],
  ['completed', 'Готово'],
  ['review', 'Ручная проверка'],
  ['failed', 'Ошибка'],
]

export function MailPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)
  const deferredSearch = useDeferredValue(search)
  const query = useQuery({ queryKey: ['jobs', deferredSearch, status, offset], queryFn: () => api.jobs(deferredSearch, status, offset) })
  const clearFilters = () => { setSearch(''); setStatus(''); setOffset(0) }
  return <>
    <PageHeading title="Письма" description="Поиск по теме, отправителю и идентификатору письма." />
    <section className="surface overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center sm:px-5">
        <label className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={event => { setSearch(event.target.value); setOffset(0) }} placeholder="Например, тема или email отправителя" className="focus-ring h-10 w-full rounded-xl border border-line bg-[#fafbfc] pl-9 pr-9 text-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-300 focus:bg-white" />
          {search && <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100" aria-label="Очистить поиск"><X className="size-4" /></button>}
        </label>
        <label className="relative flex h-10 min-w-[190px] items-center">
          <SlidersHorizontal className="pointer-events-none absolute left-3 size-4 text-slate-400" />
          <select value={status} onChange={event => { setStatus(event.target.value); setOffset(0) }} className="focus-ring h-full w-full appearance-none rounded-xl border border-line bg-white pl-9 pr-8 text-xs font-semibold text-slate-600 outline-none">
            {statusOptions.map(([value, label]) => <option key={value || 'all'} value={value}>{label}</option>)}
          </select>
        </label>
        {(search || status) && <button onClick={clearFilters} className="h-10 rounded-xl px-3 text-xs font-semibold text-slate-500 hover:bg-slate-50">Сбросить</button>}
      </div>
      <div className="flex items-center justify-between px-5 py-3 text-xs text-muted"><span>{query.data ? `Показано ${query.data.items.length} писем` : 'Загрузка списка…'}</span><span>Снимки писем хранятся 7 дней</span></div>
      {query.isPending ? <div className="p-4"><LoadingState /></div> : query.isError ? <div className="p-4"><ErrorState message={`Не удалось загрузить письма: ${query.error.message}`} /></div> : <JobTable rows={query.data.items} />}
      <div className="flex items-center justify-between border-t border-line px-5 py-3">
        <span className="text-xs text-muted">Страница {Math.floor(offset / 25) + 1}</span>
        <div className="flex gap-2">
          <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))} className="focus-ring flex h-8 items-center gap-1 rounded-lg border border-line px-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft className="size-3.5" />Назад</button>
          <button disabled={!query.data || query.data.items.length < 25} onClick={() => setOffset(offset + 25)} className="focus-ring flex h-8 items-center gap-1 rounded-lg border border-line px-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40">Дальше<ChevronRight className="size-3.5" /></button>
        </div>
      </div>
    </section>
  </>
}
