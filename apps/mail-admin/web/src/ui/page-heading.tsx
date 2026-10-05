import type { ReactNode } from 'react'

export function PageHeading({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
    <div>
      <div className="eyebrow mb-2">Mail Sort · Admin</div>
      <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-[28px]">{title}</h1>
      <p className="mt-1.5 text-sm text-muted">{description}</p>
    </div>
    {action}
  </div>
}
