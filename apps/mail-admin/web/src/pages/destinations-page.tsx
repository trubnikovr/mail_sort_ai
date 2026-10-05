import { useQuery } from '@tanstack/react-query'
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from '@tanstack/react-table'
import { Bot, Folder, FolderCog } from 'lucide-react'
import { useMemo } from 'react'
import { api } from '../api/client'
import type { Destination } from '../types'
import { EmptyState, ErrorState, LoadingState } from '../ui/feedback'
import { PageHeading } from '../ui/page-heading'

function StatePill({ active, label }: { active: boolean; label: string }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}><span className="size-1.5 rounded-full bg-current" />{active ? label : 'Выключено'}</span>
}

export function DestinationsPage() {
  const query = useQuery({ queryKey: ['destinations'], queryFn: api.destinations })
  const columns = useMemo<ColumnDef<Destination>[]>(() => [
    { accessorKey: 'name', header: 'Назначение', cell: ({ row }) => <div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-xl bg-indigo-50 text-brand"><Folder className="size-4" /></span><div><div className="font-semibold text-ink">{row.original.name}</div><div className="mt-0.5 font-mono text-[10px] text-slate-400">{row.original.id}</div></div></div> },
    { accessorKey: 'mailbox', header: 'Папка', cell: ({ row }) => <span className="rounded-md bg-slate-50 px-2 py-1 font-mono text-[11px] text-slate-600">{row.original.mailbox}</span> },
    { accessorKey: 'account_id', header: 'Аккаунт', cell: ({ row }) => <span className="text-xs text-slate-500">{row.original.account_id}</span> },
    { accessorKey: 'is_active', header: 'Статус', cell: ({ row }) => <StatePill active={row.original.is_active} label="Активно" /> },
    { accessorKey: 'use_for_ai', header: 'AI', cell: ({ row }) => row.original.use_for_ai ? <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600"><Bot className="size-4" />Включено</span> : <span className="text-xs text-slate-400">Служебная</span> },
    { accessorKey: 'instruction', header: 'Инструкция', cell: ({ row }) => <span className="line-clamp-2 max-w-[380px] text-xs leading-5 text-slate-500">{row.original.instruction || row.original.description || 'Нет инструкции'}</span> },
  ], [])
  const table = useReactTable({ data: query.data ?? [], columns, getCoreRowModel: getCoreRowModel() })
  return <>
    <PageHeading title="Назначения" description="Папки и инструкции классификации, сохранённые в PostgreSQL." />
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState message={`Не удалось загрузить назначения: ${query.error.message}`} /> : <section className="surface overflow-hidden">
      <div className="flex items-center gap-3 border-b border-line px-5 py-4"><span className="flex size-9 items-center justify-center rounded-xl bg-indigo-50 text-brand"><FolderCog className="size-4" /></span><div><h2 className="text-sm font-bold">Каталог папок</h2><p className="mt-1 text-xs text-muted">{query.data.length} назначений · {query.data.filter(item => item.is_active).length} активных</p></div></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[1000px] text-left"><thead><tr className="border-b border-line bg-slate-50/70">{table.getHeaderGroups()[0]?.headers.map(header => <th key={header.id} className="px-5 py-3 text-[10px] font-bold uppercase tracking-wide text-slate-400">{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr></thead><tbody className="divide-y divide-line">{table.getRowModel().rows.map(row => <tr key={row.id} className="align-middle hover:bg-slate-50/70">{row.getVisibleCells().map(cell => <td key={cell.id} className="px-5 py-4">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table>{query.data.length === 0 && <EmptyState label="Назначения ещё не созданы." />}</div>
    </section>}
  </>
}
