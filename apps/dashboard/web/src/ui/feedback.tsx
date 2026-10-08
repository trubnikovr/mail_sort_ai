import { AlertCircle, LoaderCircle } from 'lucide-react'

export function LoadingState({ label = 'Загружаем данные…' }: { label?: string }) {
  return <div className="surface flex min-h-44 items-center justify-center gap-3 text-sm text-muted">
    <LoaderCircle className="size-5 animate-spin text-brand" />{label}
  </div>
}

export function ErrorState({ message }: { message: string }) {
  return <div className="surface flex min-h-36 items-center gap-3 p-6 text-sm text-rose-700">
    <AlertCircle className="size-5 shrink-0" /><span>{message}</span>
  </div>
}

export function EmptyState({ label }: { label: string }) {
  return <div className="px-6 py-14 text-center text-sm text-muted">{label}</div>
}
