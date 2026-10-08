import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LoaderCircle, Mail, Plus, Server, Trash2, X } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { MailboxAccount } from '../types'
import { EmptyState, ErrorState, LoadingState } from '../ui/feedback'
import { PageHeading } from '../ui/page-heading'

export function MailboxAccountsPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['mailbox-accounts'], queryFn: api.mailboxAccounts })
  const [editing, setEditing] = useState<MailboxAccount | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const open = creating || editing !== null
  useEffect(() => {
    if (!open) return
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') close() }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [open])
  const save = useMutation({
    mutationFn: (account: Record<string, unknown>) => editing
      ? api.updateMailboxAccount(editing.id, account)
      : api.createMailboxAccount(account),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ['mailbox-accounts'] })
      await client.invalidateQueries({ queryKey: ['destinations'] })
      setEditing(null); setCreating(false); setError('')
    },
    onError: cause => setError(cause.message),
  })
  const remove = useMutation({
    mutationFn: api.deleteMailboxAccount,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ['mailbox-accounts'] })
      await client.invalidateQueries({ queryKey: ['destinations'] })
    },
  })
  const close = () => { setEditing(null); setCreating(false); setError('') }
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    save.mutate({
      id: String(data.get('id') || ''),
      name: String(data.get('name') || ''),
      provider: String(data.get('provider') || 'ews'),
      email_address: String(data.get('email_address') || ''),
      source_mailbox: String(data.get('source_mailbox') || 'INBOX'),
      host: String(data.get('host') || ''),
      port: Number(data.get('port') || 993),
      username: String(data.get('username') || ''),
      password: String(data.get('password') || ''),
      is_active: data.get('is_active') === 'on',
    })
  }
  const beginCreate = () => { setEditing(null); setCreating(true); setError('') }
  const beginEdit = (account: MailboxAccount) => { setEditing(account); setCreating(false); setError('') }

  return <>
    <PageHeading title="Почтовые аккаунты" description="Подключения к ящикам, которые Collector опрашивает, а Router использует для перемещения писем." />
    {query.isPending ? <LoadingState /> : query.isError ? <ErrorState message={`Не удалось загрузить аккаунты: ${query.error.message}`} /> : <section className="surface overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4"><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-xl bg-brand-soft text-brand"><Server className="size-4" /></span><div><h2 className="text-sm font-bold">Подключения</h2><p className="mt-1 text-xs text-muted">{query.data.length} аккаунтов · {query.data.filter(item => item.is_active && item.is_configured).length} активных</p></div></div><button onClick={beginCreate} className="focus-ring inline-flex h-9 items-center gap-2 rounded-lg bg-brand px-3 text-xs font-semibold text-white hover:bg-brand-dark"><Plus className="size-4" />Добавить аккаунт</button></div>
      {remove.isError && <p role="alert" className="border-b border-rose-100 bg-rose-50 px-5 py-3 text-xs text-rose-700">Не удалось удалить: {remove.error.message}</p>}
      <div className="divide-y divide-line">{query.data.map(account => <article key={account.id} className="flex flex-wrap items-center gap-4 px-5 py-4"><span className="flex size-10 items-center justify-center rounded-xl bg-slate-50 text-slate-500"><Mail className="size-4" /></span><div className="min-w-48 flex-1"><h3 className="text-sm font-semibold">{account.name}</h3><p className="mt-1 text-xs text-slate-500">{account.email_address || 'Адрес не настроен'} · {account.provider?.toUpperCase() || 'Провайдер не выбран'}</p><p className="mt-1 font-mono text-[10px] text-slate-400">ID: {account.id}</p></div><span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${account.is_active && account.is_configured ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{account.is_active && account.is_configured ? 'Активен' : 'Требует настройки'}</span><button onClick={() => beginEdit(account)} className="focus-ring rounded-lg border border-line px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50">Настроить</button><button onClick={() => { if (window.confirm(`Удалить аккаунт «${account.name}»?`)) remove.mutate(account.id) }} disabled={remove.isPending} aria-label={`Удалить ${account.name}`} className="focus-ring inline-flex size-9 items-center justify-center rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-40"><Trash2 className="size-4" /></button></article>)}</div>
      {query.data.length === 0 && <EmptyState label="Почтовых аккаунтов пока нет." />}
    </section>}
    {open && <div role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !save.isPending) close() }} className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/45 p-4 backdrop-blur-sm"><section role="dialog" aria-modal="true" aria-labelledby="mailbox-account-title" className="surface my-auto w-full max-w-2xl overflow-hidden shadow-2xl">
      <div className="flex items-start justify-between border-b border-line px-5 py-4 sm:px-6"><div><h2 id="mailbox-account-title" className="text-base font-bold">{editing ? 'Настройки аккаунта' : 'Новый почтовый аккаунт'}</h2><p className="mt-1 text-xs leading-5 text-muted">Пароль шифруется перед записью в базу и не отображается после сохранения.</p></div><button type="button" onClick={close} disabled={save.isPending} aria-label="Закрыть" className="focus-ring ml-4 inline-flex size-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100"><X className="size-4" /></button></div>
      <form onSubmit={submit} className="grid max-h-[calc(100vh-10rem)] gap-4 overflow-y-auto p-5 sm:grid-cols-2 sm:p-6">
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700">Стабильный ID<span className="font-normal text-slate-400">Не меняется при переименовании. Им пользуются папки и история.</span><input name="id" required maxLength={128} pattern={editing ? undefined : '[a-zA-Z0-9][a-zA-Z0-9_-]*'} readOnly={Boolean(editing)} defaultValue={editing?.id} placeholder="dolores-main" className="focus-ring h-10 rounded-lg border border-line px-3 text-sm font-normal read-only:bg-slate-50" /></label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700">Название<span className="font-normal text-slate-400">Можно менять в любое время.</span><input name="name" required maxLength={128} defaultValue={editing?.name} placeholder="Основной рабочий ящик" className="focus-ring h-10 rounded-lg border border-line px-3 text-sm font-normal" /></label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700">Провайдер<select name="provider" required defaultValue={editing?.provider || 'ews'} className="focus-ring h-10 rounded-lg border border-line bg-white px-3 text-sm font-normal"><option value="ews">Exchange (EWS)</option><option value="imap">IMAP</option></select></label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700">Адрес ящика<input name="email_address" type="email" required maxLength={255} defaultValue={editing?.email_address} placeholder="mail@example.com" className="focus-ring h-10 rounded-lg border border-line px-3 text-sm font-normal" /></label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700">Сервер / EWS endpoint<span className="font-normal text-slate-400">Например, imap.gmail.com или https://exchange/EWS/Exchange.asmx.</span><input name="host" required maxLength={512} defaultValue={editing?.host} placeholder="https://exchange.example.com/EWS/Exchange.asmx" className="focus-ring h-10 rounded-lg border border-line px-3 text-sm font-normal" /></label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700">Порт IMAP<span className="font-normal text-slate-400">Для EWS используется порт из endpoint.</span><input name="port" type="number" min={1} max={65535} required defaultValue={editing?.port || 993} className="focus-ring h-10 rounded-lg border border-line px-3 text-sm font-normal" /></label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700">Логин<input name="username" required maxLength={255} defaultValue={editing?.username} placeholder="Пользователь для входа" className="focus-ring h-10 rounded-lg border border-line px-3 text-sm font-normal" /></label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700">Пароль<span className="font-normal text-slate-400">{editing?.has_password ? 'Оставьте пустым, чтобы сохранить текущий.' : 'Нужно заполнить перед активацией.'}</span><input name="password" type="password" required={!editing?.has_password} autoComplete="new-password" maxLength={2048} className="focus-ring h-10 rounded-lg border border-line px-3 text-sm font-normal" /></label>
        <label className="grid gap-1.5 text-xs font-semibold text-slate-700 sm:col-span-2">Папка для чтения<input name="source_mailbox" required maxLength={255} defaultValue={editing?.source_mailbox || 'INBOX'} placeholder="INBOX" className="focus-ring h-10 rounded-lg border border-line px-3 text-sm font-normal" /></label>
        <label className="flex items-start gap-2.5 rounded-xl bg-slate-50 p-4 text-xs font-semibold text-slate-700 sm:col-span-2"><input type="checkbox" name="is_active" defaultChecked={editing?.is_active ?? false} className="mt-0.5 accent-brand" /><span>Аккаунт активен<span className="mt-1 block font-normal leading-4 text-slate-500">Collector будет опрашивать этот ящик, Router будет использовать его для перемещения писем.</span></span></label>
        {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-xs text-rose-700 sm:col-span-2">Не удалось сохранить: {error}</p>}
        <div className="flex justify-end gap-2 border-t border-line pt-4 sm:col-span-2"><button type="button" onClick={close} disabled={save.isPending} className="focus-ring h-10 rounded-lg border border-line px-4 text-xs font-semibold text-slate-600">Отмена</button><button disabled={save.isPending} className="focus-ring inline-flex h-10 items-center gap-2 rounded-lg bg-brand px-4 text-xs font-semibold text-white disabled:opacity-60">{save.isPending && <LoaderCircle className="size-3.5 animate-spin" />}{save.isPending ? 'Сохраняем…' : 'Сохранить'}</button></div>
      </form>
    </section></div>}
  </>
}
