import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from '@tanstack/react-table'
import { Bot, Folder, FolderCog, LoaderCircle, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Destination } from '../types'
import { EmptyState, ErrorState, LoadingState } from '../ui/feedback'
import { PageHeading } from '../ui/page-heading'

function StatePill({ active, label }: { active: boolean; label: string }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}><span className="size-1.5 rounded-full bg-current" />{active ? label : 'Выключено'}</span>
}

export function DestinationsPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['destinations'], queryFn: api.destinations })
  const [editing, setEditing] = useState<Destination | null>(null)
  const [creating, setCreating] = useState(false)
  const [formError, setFormError] = useState('')
  const formOpen = creating || editing !== null
  useEffect(() => {
    if (!formOpen) return
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') closeForm() }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [formOpen])
  const save = useMutation({
    mutationFn: (destination: Destination) => editing
      ? api.updateDestination(editing.id, destination)
      : api.createDestination(destination),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['destinations'] })
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setEditing(null)
      setCreating(false)
      setFormError('')
    },
    onError: error => setFormError(error.message),
  })
  const remove = useMutation({
    mutationFn: api.deleteDestination,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['destinations'] })
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
  const beginEdit = (destination: Destination) => { setEditing(destination); setCreating(false); setFormError('') }
  const beginCreate = () => { setEditing(null); setCreating(true); setFormError('') }
  const closeForm = () => { setEditing(null); setCreating(false); setFormError('') }
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    save.mutate({
      id: String(data.get('id') || ''),
      name: String(data.get('name') || ''),
      account_id: String(data.get('account_id') || ''),
      mailbox: String(data.get('mailbox') || ''),
      description: String(data.get('description') || ''),
      instruction: String(data.get('instruction') || ''),
      is_active: data.get('is_active') === 'on',
      use_for_ai: data.get('use_for_ai') === 'on',
    })
  }
  const columns = useMemo<ColumnDef<Destination>[]>(() => [
    { accessorKey: 'name', header: 'Папка', cell: ({ row }) => <div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-xl bg-indigo-50 text-brand"><Folder className="size-4" /></span><div><div className="font-semibold text-ink">{row.original.name}</div><div className="mt-0.5 font-mono text-[10px] text-slate-400">{row.original.id}</div></div></div> },
    { accessorKey: 'mailbox', header: 'Папка', cell: ({ row }) => <span className="rounded-md bg-slate-50 px-2 py-1 font-mono text-[11px] text-slate-600">{row.original.mailbox}</span> },
    { accessorKey: 'account_id', header: 'Аккаунт', cell: ({ row }) => <span className="text-xs text-slate-500">{row.original.account_id}</span> },
    { accessorKey: 'is_active', header: 'Статус', cell: ({ row }) => <StatePill active={row.original.is_active} label="Активно" /> },
    { accessorKey: 'use_for_ai', header: 'AI', cell: ({ row }) => row.original.use_for_ai ? <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600"><Bot className="size-4" />Включено</span> : <span className="text-xs text-slate-400">Служебная</span> },
    { accessorKey: 'instruction', header: 'Инструкция', cell: ({ row }) => <span className="line-clamp-2 max-w-[380px] text-xs leading-5 text-slate-500">{row.original.instruction || row.original.description || 'Нет инструкции'}</span> },
  ], [])
  const table = useReactTable({ data: query.data ?? [], columns, getCoreRowModel: getCoreRowModel() })
  return <>
    <PageHeading title="Папки" description="Почтовые папки и инструкции для AI-классификации." />
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState message={`Не удалось загрузить папки: ${query.error.message}`} /> : <section className="surface overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4"><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-xl bg-indigo-50 text-brand"><FolderCog className="size-4" /></span><div><h2 className="text-sm font-bold">Почтовые папки</h2><p className="mt-1 text-xs text-muted">{query.data.length} папок · {query.data.filter(item => item.is_active).length} активных</p></div></div><button onClick={beginCreate} className="focus-ring inline-flex h-9 items-center gap-2 rounded-lg bg-brand px-3 text-xs font-semibold text-white hover:bg-indigo-700"><Plus className="size-4" />Добавить папку</button></div>
      {formOpen && <div role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !save.isPending) closeForm() }} className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/45 p-4 backdrop-blur-sm">
        <section role="dialog" aria-modal="true" aria-labelledby="destination-form-title" className="surface my-auto w-full max-w-2xl overflow-hidden shadow-2xl">
          <div className="flex items-start justify-between border-b border-line px-5 py-4 sm:px-6"><div><h2 id="destination-form-title" className="text-base font-bold text-ink">{editing ? 'Редактировать папку' : 'Новая папка'}</h2><p className="mt-1 text-xs leading-5 text-muted">Укажите почтовую папку и объясните AI, какие письма в неё складывать.</p></div><button type="button" onClick={closeForm} disabled={save.isPending} aria-label="Закрыть окно" className="focus-ring ml-4 inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-ink"><X className="size-4" /></button></div>
          <form onSubmit={submit} className="grid max-h-[calc(100vh-10rem)] gap-4 overflow-y-auto p-5 sm:grid-cols-2 sm:p-6">
            <label className="grid content-start gap-1.5 text-xs font-semibold text-slate-700">Внутренний ID<span className="font-normal leading-4 text-slate-400">Короткий уникальный код, например finance. После создания его нельзя изменить.</span><input name="id" required maxLength={128} pattern="[a-zA-Z0-9][a-zA-Z0-9_-]*" defaultValue={editing?.id} readOnly={Boolean(editing)} placeholder="finance" className="focus-ring mt-1 h-10 rounded-lg border border-line bg-white px-3 text-sm font-normal read-only:bg-slate-50" /></label>
            <label className="grid content-start gap-1.5 text-xs font-semibold text-slate-700">Название папки<span className="font-normal leading-4 text-slate-400">Понятное название, которое видите вы и использует AI.</span><input name="name" required maxLength={128} defaultValue={editing?.name} placeholder="Финансы" className="focus-ring mt-1 h-10 rounded-lg border border-line bg-white px-3 text-sm font-normal" /></label>
            <label className="grid content-start gap-1.5 text-xs font-semibold text-slate-700">Почтовый аккаунт<span className="font-normal leading-4 text-slate-400">Значение должно совпадать с MAILBOX_ACCOUNT_ID в настройке почты.</span><input name="account_id" required maxLength={128} defaultValue={editing?.account_id} placeholder="personal-gmail" className="focus-ring mt-1 h-10 rounded-lg border border-line bg-white px-3 text-sm font-normal" /></label>
            <label className="grid content-start gap-1.5 text-xs font-semibold text-slate-700">Путь к папке<span className="font-normal leading-4 text-slate-400">Полный путь в почтовом ящике, например INBOX/Finance.</span><input name="mailbox" required maxLength={255} defaultValue={editing?.mailbox} placeholder="INBOX/Finance" className="focus-ring mt-1 h-10 rounded-lg border border-line bg-white px-3 text-sm font-normal" /></label>
            <label className="grid gap-1.5 text-xs font-semibold text-slate-700 sm:col-span-2">Описание<span className="font-normal leading-4 text-slate-400">Краткая заметка о том, для чего предназначена папка.</span><input name="description" maxLength={512} defaultValue={editing?.description} placeholder="Счета, оплаты и финансовые отчёты" className="focus-ring mt-1 h-10 rounded-lg border border-line bg-white px-3 text-sm font-normal" /></label>
            <label className="grid gap-1.5 text-xs font-semibold text-slate-700 sm:col-span-2">Инструкция для AI<span className="font-normal leading-4 text-slate-400">Опишите, какие письма нужно направлять в эту папку. Чем точнее инструкция, тем лучше классификация.</span><textarea name="instruction" maxLength={20000} rows={4} defaultValue={editing?.instruction} placeholder="Направляй сюда счета, подтверждения оплат и финансовую отчётность. Не включай рекламные предложения." className="focus-ring mt-1 rounded-lg border border-line bg-white px-3 py-2 text-sm font-normal leading-5" /></label>
            <div className="grid gap-3 rounded-xl bg-slate-50 p-4 sm:col-span-2 sm:grid-cols-2"><label className="flex items-start gap-2.5 text-xs font-semibold text-slate-700"><input type="checkbox" name="is_active" defaultChecked={editing?.is_active ?? true} className="mt-0.5 accent-indigo-600" /><span>Папка активна<span className="mt-1 block font-normal leading-4 text-slate-500">Если выключить, классификатор не будет выбирать эту папку.</span></span></label><label className="flex items-start gap-2.5 text-xs font-semibold text-slate-700"><input type="checkbox" name="use_for_ai" defaultChecked={editing?.use_for_ai ?? true} className="mt-0.5 accent-indigo-600" /><span>Использовать для AI<span className="mt-1 block font-normal leading-4 text-slate-500">Снимите флажок для служебной папки, которую не нужно предлагать AI.</span></span></label></div>
            {formError && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-xs text-rose-700 sm:col-span-2">Не удалось сохранить: {formError}</p>}
            <div className="flex justify-end gap-2 border-t border-line pt-4 sm:col-span-2"><button type="button" onClick={closeForm} disabled={save.isPending} className="focus-ring inline-flex h-10 items-center gap-2 rounded-lg border border-line bg-white px-4 text-xs font-semibold text-slate-600 disabled:opacity-50">Отмена</button><button disabled={save.isPending} className="focus-ring inline-flex h-10 items-center gap-2 rounded-lg bg-brand px-4 text-xs font-semibold text-white disabled:opacity-60">{save.isPending && <LoaderCircle className="size-3.5 animate-spin" />}{save.isPending ? 'Сохраняем…' : editing ? 'Сохранить изменения' : 'Создать папку'}</button></div>
          </form>
        </section>
      </div>}
      {remove.isError && <p role="alert" className="border-b border-rose-100 bg-rose-50 px-5 py-3 text-xs text-rose-700">Не удалось удалить: {remove.error.message}</p>}
      <div className="overflow-x-auto"><table className="w-full min-w-[1120px] text-left"><thead><tr className="border-b border-line bg-slate-50/70">{table.getHeaderGroups()[0]?.headers.map(header => <th key={header.id} className="px-5 py-3 text-[10px] font-bold uppercase tracking-wide text-slate-400">{flexRender(header.column.columnDef.header, header.getContext())}</th>)}<th className="px-5 py-3 text-[10px] font-bold uppercase tracking-wide text-slate-400">Действия</th></tr></thead><tbody className="divide-y divide-line">{table.getRowModel().rows.map(row => <tr key={row.id} className="align-middle hover:bg-slate-50/70">{row.getVisibleCells().map(cell => <td key={cell.id} className="px-5 py-4">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}<td className="px-5 py-4"><div className="flex gap-1"><button onClick={() => beginEdit(row.original)} aria-label={`Редактировать папку ${row.original.name}`} className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-slate-500 hover:bg-indigo-50 hover:text-brand"><Pencil className="size-4" /></button><button onClick={() => { if (window.confirm(`Удалить папку «${row.original.name}»?`)) remove.mutate(row.original.id) }} disabled={remove.isPending} aria-label={`Удалить папку ${row.original.name}`} className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-slate-500 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-40"><Trash2 className="size-4" /></button></div></td></tr>)}</tbody></table>{query.data.length === 0 && <EmptyState label="Папок пока нет." />}</div>
    </section>}
  </>
}
