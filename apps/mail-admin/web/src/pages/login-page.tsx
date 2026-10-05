import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ArrowDownLeft, Eye, EyeOff, LockKeyhole, UserRound } from 'lucide-react'
import { api } from '../api/client'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const queryClient = useQueryClient()
  const login = useMutation({
    mutationFn: () => api.login(username, password),
    onSuccess: result => queryClient.setQueryData(['auth'], result),
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    login.mutate()
  }

  const errorMessage = login.error?.message.includes('429')
    ? 'Слишком много попыток. Подождите 15 минут и попробуйте снова.'
    : 'Не удалось войти. Проверьте имя пользователя и пароль.'

  return <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#f5f7fb] px-5 py-12">
    <div className="pointer-events-none absolute -left-32 -top-36 size-[420px] rounded-full bg-indigo-200/40 blur-3xl" />
    <div className="pointer-events-none absolute -bottom-40 -right-32 size-[470px] rounded-full bg-sky-200/40 blur-3xl" />
    <div className="relative w-full max-w-[420px]">
      <div className="mb-8 flex items-center justify-center gap-3">
        <span className="flex size-11 items-center justify-center rounded-2xl bg-gradient-to-br from-[#6974f6] to-[#4e57d9] text-white shadow-lg shadow-indigo-200"><ArrowDownLeft className="size-5" /></span>
        <span className="text-lg font-extrabold tracking-tight">mail<span className="text-brand">sort</span></span>
      </div>
      <section className="surface p-7 shadow-xl shadow-slate-200/50 sm:p-9">
        <div className="mb-7 text-center">
          <div className="eyebrow mb-2">Защищённая область</div>
          <h1 className="text-2xl font-bold tracking-tight">Вход в админку</h1>
          <p className="mt-2 text-sm text-muted">Введите учётные данные администратора.</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">Имя пользователя</span>
            <span className="relative block"><UserRound className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><input autoComplete="username" required value={username} onChange={event => setUsername(event.target.value)} className="focus-ring h-11 w-full rounded-xl border border-line bg-white pl-10 pr-3 text-sm outline-none transition focus:border-indigo-300" placeholder="admin" /></span>
          </label>
          <label className="block"><span className="mb-1.5 block text-xs font-semibold text-slate-600">Пароль</span>
            <span className="relative block"><LockKeyhole className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><input autoComplete="current-password" required type={showPassword ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)} className="focus-ring h-11 w-full rounded-xl border border-line bg-white pl-10 pr-11 text-sm outline-none transition focus:border-indigo-300" placeholder="Ваш пароль" /><button type="button" onClick={() => setShowPassword(value => !value)} className="absolute right-2 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-50" aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}>{showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}</button></span>
          </label>
          {login.isError && <p role="alert" className="rounded-xl bg-rose-50 px-3 py-2.5 text-xs font-medium text-rose-700">{errorMessage}</p>}
          <button disabled={login.isPending} className="focus-ring flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-brand text-sm font-bold text-white shadow-md shadow-indigo-200 transition hover:bg-indigo-600 disabled:cursor-wait disabled:opacity-70">
            {login.isPending ? 'Входим…' : <>Войти в систему <ArrowRight className="size-4" /></>}
          </button>
        </form>
        <p className="mt-6 text-center text-[11px] leading-5 text-slate-400">Сессия автоматически завершится по таймауту.</p>
      </section>
      <p className="mt-5 text-center text-[11px] text-slate-400">Mail Sort · внутренний доступ</p>
    </div>
  </main>
}
