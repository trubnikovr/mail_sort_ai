import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from '@tanstack/react-table'
import { ArrowUpRight } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import type { JobSummary } from '../types'
import { StatusBadge } from './status-badge'
import { EmptyState } from './feedback'

const formatDate = (value: string | null) => value
  ? new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
  : '—'

const columns: ColumnDef<JobSummary>[] = [
  {
    accessorKey: 'subject',
    header: 'Письмо',
    cell: ({ row }) => <div className="min-w-0">
      <div className="max-w-[380px] truncate font-semibold text-ink">{row.original.subject || '(без темы)'}</div>
      <div className="mt-1 max-w-[380px] truncate text-xs text-muted">{row.original.sender || row.original.provider_message_id}</div>
    </div>,
  },
  { accessorKey: 'status', header: 'Статус', cell: ({ row }) => <StatusBadge status={row.original.status} /> },
  { accessorKey: 'destination_id', header: 'Папка', cell: ({ row }) => <span className="text-sm text-slate-600">{row.original.destination_id || '—'}</span> },
  { accessorKey: 'created_at', header: 'Получено', cell: ({ row }) => <span className="whitespace-nowrap text-xs text-muted">{formatDate(row.original.received_at || row.original.created_at)}</span> },
  {
    id: 'open',
    header: '',
    cell: ({ row }) => <Link to="/mail/$jobId" params={{ jobId: row.original.id }} className="focus-ring inline-flex size-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-brand-soft hover:text-brand" aria-label="Открыть письмо"><ArrowUpRight className="size-4" /></Link>,
  },
]

export function JobTable({ rows }: { rows: JobSummary[] }) {
  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel() })
  return <div className="overflow-x-auto">
    <table className="w-full min-w-[760px] text-left">
      <thead><tr className="border-b border-line bg-slate-50/70">
        {table.getHeaderGroups()[0]?.headers.map(header => <th key={header.id} className="px-5 py-3 text-[11px] font-bold uppercase tracking-wide text-slate-400">{flexRender(header.column.columnDef.header, header.getContext())}</th>)}
      </tr></thead>
      <tbody className="divide-y divide-line">
        {table.getRowModel().rows.map(row => <tr key={row.id} className="transition hover:bg-slate-50/70">
          {row.getVisibleCells().map(cell => <td key={cell.id} className="px-5 py-4 align-middle">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
        </tr>)}
      </tbody>
    </table>
    {rows.length === 0 && <EmptyState label="Писем пока нет — новые появятся здесь после синхронизации почты." />}
  </div>
}
