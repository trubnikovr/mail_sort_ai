import type { JobStatus } from '../types'

const labels: Record<JobStatus, string> = {
  pending: 'В очереди',
  processing: 'Обрабатывается',
  completed: 'Готово',
  review: 'Проверить',
  failed: 'Ошибка',
}

const colors: Record<JobStatus, string> = {
  pending: 'bg-slate-100 text-slate-600',
  processing: 'bg-blue-50 text-blue-700',
  completed: 'bg-emerald-50 text-emerald-700',
  review: 'bg-amber-50 text-amber-700',
  failed: 'bg-rose-50 text-rose-700',
}

export function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${colors[status]}`}>
    <span className="size-1.5 rounded-full bg-current" />{labels[status]}
  </span>
}
