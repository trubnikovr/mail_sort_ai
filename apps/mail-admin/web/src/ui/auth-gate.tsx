import type { ReactNode } from 'react'
import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { LoginPage } from '../pages/login-page'

export function AuthGate({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const auth = useQuery({ queryKey: ['auth'], queryFn: api.auth, retry: false })

  useEffect(() => {
    const onUnauthorized = () => {
      queryClient.clear()
      queryClient.setQueryData(['auth'], { authenticated: false })
    }
    window.addEventListener('mail-admin:unauthorized', onUnauthorized)
    return () => window.removeEventListener('mail-admin:unauthorized', onUnauthorized)
  }, [queryClient])

  if (auth.isPending) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f5f7fb] text-sm font-medium text-slate-500">Проверяем сессию…</div>
  }
  if (auth.isError) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f5f7fb] p-6 text-center text-sm text-rose-700">Не удалось связаться с Mail Sort API. Обновите страницу или проверьте подключение.</div>
  }
  if (!auth.data.authenticated) return <LoginPage />
  return children
}
