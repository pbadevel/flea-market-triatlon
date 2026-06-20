import { createFileRoute, Link } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { useEffect, useState } from 'react'
import { CheckCircle, XCircle } from 'lucide-react'
import { useAppSession } from '@/lib/session'

const confirmEmailFn = createServerFn()
  .inputValidator((data: { token: string }) => data)
  .handler(async ({ data }) => {
    const resp = await fetch(`http://127.0.0.1:8000/v1/auth/confirm-email?token=${encodeURIComponent(data.token)}`)
    const result = await resp.json()
    if (result.success) {
        const session = await useAppSession()
        await session.update({ token: result.token, isAdmin: result.role === 'ADMIN', isModerator: result.role === 'MODERATOR' })
    }
    return await res.json()
  })

export const Route = createFileRoute('/auth/confirm-email')({
  component: ConfirmEmailPage,
  validateSearch: (search: Record<string, unknown>) => ({
    token: search.token as string | undefined,
  }),
})

function ConfirmEmailPage() {
  const { token } = Route.useSearch()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Отсутствует токен подтверждения')
      return
    }

    const confirm = async () => {
      try {
        const data = await confirmEmailFn({ data: { token } })
        if (data.success) {
          setStatus('success')
          setMessage('Email успешно подтверждён!')
          // Сохраняем токен сессии (автоматический вход)
          if (data.token) {
            document.cookie = `session=${data.token}; path=/; max-age=${30*24*60*60}; SameSite=Lax`
          }
          // Redirect to profile after 2 seconds
          setTimeout(() => {
            window.location.href = '/profile'
          }, 2000)
        } else {
          setStatus('error')
          setMessage(data.message || 'Ошибка подтверждения')
        }
      } catch (e) {
        setStatus('error')
        setMessage('Не удалось подтвердить email')
      }
    }

    confirm()
  }, [token])

  return (
    <div className="min-h-screen flex items-center justify-center bg-(--bg)">
      <div className="text-center max-w-md mx-auto p-8">
        {status === 'loading' && (
          <div className="animate-pulse">
            <div className="size-16 mx-auto rounded-full bg-(--link-bg-hover) mb-4" />
            <p className="text-(--sea-ink-soft)">Подтверждение email...</p>
          </div>
        )}
        {status === 'success' && (
          <>
            <CheckCircle className="size-16 mx-auto text-green-500 mb-4" />
            <h1 className="text-xl font-bold text-(--sea-ink) mb-2">{message}</h1>
            <p className="text-sm text-(--sea-ink-soft)">Сейчас перенаправим в профиль...</p>
            <Link
              to="/profile"
              className="mt-4 inline-block text-(--palm) hover:underline text-sm"
            >
              Перейти в профиль
            </Link>
          </>
        )}
        {status === 'error' && (
          <>
            <XCircle className="size-16 mx-auto text-red-500 mb-4" />
            <h1 className="text-xl font-bold text-(--sea-ink) mb-2">Ошибка</h1>
            <p className="text-sm text-(--sea-ink-soft) mb-4">{message}</p>
            <Link
              to="/profile"
              className="text-(--palm) hover:underline text-sm"
            >
              В профиль
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
