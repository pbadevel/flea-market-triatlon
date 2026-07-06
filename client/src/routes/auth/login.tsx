// src/routes/auth/login.tsx
import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Mail,
  Lock,
  MessageCircle,
  Eye,
  EyeOff,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Loader2,
  ExternalLink,
} from 'lucide-react'
import {
  checkTelegramAuthStatusFn,
  initTelegramAuthFn,
  loginEmailFn,
} from '@/lib/api/auth'
import { getSession } from '@/lib/session'


export const Route = createFileRoute('/auth/login')({
  loader: async () => {
    const sessionData = await getSession()
    return sessionData
  },
  component: LoginPage,
})

type AuthMethod = 'telegram' | 'email'
type TelegramAuthStatus = 'idle' | 'waiting' | 'success' | 'error' | 'expired'

function LoginPage() {
  const { token } = Route.useLoaderData()
  const navigate = useNavigate()
  
  const [method, setMethod] = useState<AuthMethod>('telegram')
  const [showPassword, setShowPassword] = useState(false)
  const [tgAuthStatus, setTgAuthStatus] = useState<TelegramAuthStatus>('idle')
  const [deeplink, setDeeplink] = useState('')
  const [sessionToken, setSessionToken] = useState('')
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })
  const [error, setError] = useState('')

  const telegramInitMutation = useMutation({
    mutationFn: initTelegramAuthFn,
    onSuccess: (data) => {
      setDeeplink(data.deeplink)
      setSessionToken(data.session_token)
      setTgAuthStatus('waiting')
    },
    onError: () => {
      setTgAuthStatus('error')
    },
  })

  useEffect(() => {
    if (tgAuthStatus !== 'waiting' || !sessionToken) return

    const pollInterval = setInterval(async () => {
      try {
        const status = await checkTelegramAuthStatusFn({data: { session_token: sessionToken }})
        
        if (status.status === 'completed' && status.token) {
          setTgAuthStatus('success')
          navigate({ to: '/' })
        } else if (status.status === 'expired') {
          setTgAuthStatus('expired')
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [tgAuthStatus, sessionToken, navigate])

  const loginMutation = useMutation({
    mutationFn: () => loginEmailFn({ data: {
      email: formData.email,
      password: formData.password,
    }}),
    onSuccess: () => {
      navigate({ to: '/' })
    },
    onError: (err) => {
      setError(err.message || 'Неверный email или пароль')
    },
  })

  const handleTelegramAuth = () => {
    setError('')
    setTgAuthStatus('idle')
    telegramInitMutation.mutate({})
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (method === 'email') {
      if (!formData.email || !formData.password) {
        setError('Заполните все поля')
        return
      }
      
      loginMutation.mutate()
    }
  }

  if (token) {
    navigate({ to: '/' })
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-(--sea-ink) mb-2">TBSALE</h1>
          <p className="text-(--sea-ink-soft)">Войдите в аккаунт</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8">
          {/* Method Selection */}
          <div className="space-y-3 mb-6">
            <button
              onClick={() => {
                setMethod('telegram')
                setTgAuthStatus('idle')
              }}
              className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                method === 'telegram'
                  ? 'border-(--palm) bg-(--palm)/5'
                  : 'border-(--line) hover:border-(--palm)/30'
              }`}
            >
              <div className={`flex size-10 items-center justify-center rounded-full ${
                method === 'telegram' ? 'bg-(--palm) text-white' : 'bg-(--link-bg-hover) text-(--sea-ink-soft)'
              }`}>
                <MessageCircle className="size-5" />
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium text-(--sea-ink)">Telegram</div>
                <div className="text-xs text-(--sea-ink-soft)">Быстрый вход через бота</div>
              </div>
              {method === 'telegram' && <CheckCircle className="size-5 text-(--palm)" />}
            </button>

            <button
              onClick={() => setMethod('email')}
              className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                method === 'email'
                  ? 'border-(--palm) bg-(--palm)/5'
                  : 'border-(--line) hover:border-(--palm)/30'
              }`}
            >
              <div className={`flex size-10 items-center justify-center rounded-full ${
                method === 'email' ? 'bg-(--palm) text-white' : 'bg-(--link-bg-hover) text-(--sea-ink-soft)'
              }`}>
                <Mail className="size-5" />
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium text-(--sea-ink)">Email</div>
                <div className="text-xs text-(--sea-ink-soft)">Классический вход</div>
              </div>
              {method === 'email' && <CheckCircle className="size-5 text-(--palm)" />}
            </button>
          </div>

          {/* Telegram Auth */}
          {method === 'telegram' && (
            <div className="space-y-4">
              {tgAuthStatus === 'idle' && (
                <button
                  onClick={handleTelegramAuth}
                  disabled={telegramInitMutation.isPending}
                  className="w-full bg-[#0088cc] hover:bg-[#0099dd] text-white font-medium py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <MessageCircle className="size-5" />
                  {telegramInitMutation.isPending ? 'Загрузка...' : 'Войти через Telegram'}
                </button>
              )}

              {tgAuthStatus === 'waiting' && (
                <div className="text-center space-y-4">
                  <div className="flex justify-center">
                    <Loader2 className="size-12 text-blue-500 animate-spin" />
                  </div>
                  <div>
                    <p className="font-medium text-(--sea-ink) mb-2">
                      Откройте бота в Telegram
                    </p>
                    <a
                      href={deeplink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-blue-600 hover:underline"
                    >
                      <ExternalLink className="size-4" />
                      Открыть бота
                    </a>
                  </div>
                  <p className="text-sm text-(--sea-ink-soft)">
                    Ожидание подтверждения...
                  </p>
                </div>
              )}

              {tgAuthStatus === 'success' && (
                <div className="text-center space-y-2">
                  <CheckCircle className="mx-auto size-12 text-green-500" />
                  <p className="font-medium text-green-600">Вход выполнен!</p>
                </div>
              )}

              {tgAuthStatus === 'error' && (
                <div className="text-center space-y-2">
                  <AlertCircle className="mx-auto size-12 text-red-500" />
                  <p className="text-red-600">Ошибка авторизации</p>
                  <button
                    onClick={handleTelegramAuth}
                    className="text-blue-600 hover:underline text-sm"
                  >
                    Попробовать ещё раз
                  </button>
                </div>
              )}

              {tgAuthStatus === 'expired' && (
                <div className="text-center space-y-2">
                  <AlertCircle className="mx-auto size-12 text-orange-500" />
                  <p className="text-orange-600">Время ожидания истекло</p>
                  <button
                    onClick={handleTelegramAuth}
                    className="text-blue-600 hover:underline text-sm"
                  >
                    Начать заново
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Email Form */}
          {method === 'email' && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-(--sea-ink)">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-(--line) focus:border-(--palm) focus:ring-2 focus:ring-(--palm)/20 outline-none transition bg-(--chip-bg) text-(--sea-ink)"
                    placeholder="example@mail.ru"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-(--sea-ink)">Пароль</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full pl-10 pr-12 py-2.5 rounded-xl border border-(--line) focus:border-(--palm) focus:ring-2 focus:ring-(--palm)/20 outline-none transition bg-(--chip-bg) text-(--sea-ink)"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 p-3 rounded-xl">
                  <AlertCircle className="size-5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loginMutation.isPending}
                className="w-full bg-(--palm) hover:bg-(--palm)/90 text-white font-medium py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loginMutation.isPending ? (
                  'Загрузка...'
                ) : (
                  <>
                    Войти
                    <ArrowRight className="size-5" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Footer */}
          <div className="mt-6 text-center text-sm text-(--sea-ink-soft)">
            Нет аккаунта?{' '}
            <Link
              to="/auth/register"
              className="text-(--palm) hover:underline font-medium"
            >
              Зарегистрироваться
            </Link>
          </div>
        </div>

        {/* Back to home */}
        <div className="text-center mt-6">
          <Link to="/" className="text-(--sea-ink-soft) hover:text-(--sea-ink) text-sm">
            ← На главную
          </Link>
        </div>
      </div>
    </div>
  )
}