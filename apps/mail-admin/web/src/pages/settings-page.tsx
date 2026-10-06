import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BrainCircuit, CircleCheck, CirclePause, LoaderCircle, Pause, Play } from 'lucide-react'
import { api } from '../api/client'
import { ErrorState, LoadingState } from '../ui/feedback'
import { PageHeading } from '../ui/page-heading'

export function SettingsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['settings'], queryFn: api.settings, refetchInterval: 10_000 })
  const update = useMutation({
    mutationFn: api.setDecisionEnabled,
    onSuccess: setting => queryClient.setQueryData(['settings'], setting),
  })

  return <>
    <PageHeading title="Настройки системы" description="Управление обработчиками и рабочими параметрами Mail Sort." />
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState message={`Не удалось загрузить настройки: ${query.error.message}`} /> : <section className="surface max-w-3xl overflow-hidden">
      <div className="flex items-center gap-4 border-b border-line p-5 sm:p-6">
        <span className={`flex size-11 items-center justify-center rounded-xl ${query.data.value ? 'bg-brand-soft text-brand' : 'bg-amber-50 text-amber-700'}`}><BrainCircuit className="size-5" /></span>
        <div className="min-w-0 flex-1"><h2 className="text-sm font-bold">AI-классификация · Decision</h2><p className="mt-1 text-xs leading-5 text-muted">{query.data.description}</p></div>
        <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${query.data.value ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
          {query.data.value ? <CircleCheck className="size-3.5" /> : <CirclePause className="size-3.5" />}
          {query.data.value ? 'Работает' : 'Приостановлена'}
        </span>
      </div>
      <div className="p-5 sm:p-6">
        <p className="max-w-2xl text-xs leading-6 text-slate-500">При паузе Decision завершит текущую обработку и перестанет брать новые задачи. Collector продолжит сохранять письма, а Router — выполнять уже созданные маршруты. Если AI-провайдер сообщит об исчерпанном балансе, Decision поставит себя на паузу, вернёт текущее письмо в очередь и создаст критический алерт. После решения проблемы возобновите обработку здесь.</p>
        {update.isError && <p role="alert" className="mt-4 rounded-lg bg-rose-50 p-3 text-xs text-rose-700">Не удалось изменить настройку: {update.error.message}</p>}
        <button onClick={() => update.mutate(!query.data.value)} disabled={update.isPending} className={`focus-ring mt-5 inline-flex h-10 items-center gap-2 rounded-xl px-4 text-xs font-semibold text-white transition disabled:cursor-wait disabled:opacity-60 ${query.data.value ? 'bg-amber-600 hover:bg-amber-700' : 'bg-brand hover:bg-brand-dark'}`}>
          {update.isPending ? <LoaderCircle className="size-4 animate-spin" /> : query.data.value ? <Pause className="size-4" /> : <Play className="size-4" />}
          {update.isPending ? 'Сохраняем…' : query.data.value ? 'Приостановить Decision' : 'Возобновить Decision'}
        </button>
      </div>
    </section>}
  </>
}
