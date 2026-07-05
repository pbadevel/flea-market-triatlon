// src/routes/auth/register.tsx
import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Mail,
  Lock,
  User,
  Phone,
  MessageCircle,
  Eye,
  EyeOff,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Loader2,
  ExternalLink,
  MailCheck,
  RefreshCw,
} from 'lucide-react'
import {
  initTelegramAuthFn,
  checkTelegramAuthStatusFn,
  registerEmailFn,
  resendConfirmationFn,
} from '@/lib/api/auth'
import { getSession } from '@/lib/session'

export const Route = createFileRoute('/auth/register')({
  loader: async () => {
    const sessionData = await getSession()
    return sessionData
  },
  component: RegisterPage,
})

type AuthMethod = 'telegram' | 'email'
type TelegramAuthStatus = 'idle' | 'waiting' | 'success' | 'error' | 'expired'

function RegisterPage() {
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
    firstName: '',
    lastName: '',
    preferredContact: 'TELEGRAM' as string,
    contactValue: '',
  })
  const [error, setError] = useState('')
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null)

  // Telegram auth
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

  // Polling для Telegram
  useEffect(() => {
    if (tgAuthStatus !== 'waiting' || !sessionToken) return

    const pollInterval = setInterval(async () => {
      try {
        const status = await checkTelegramAuthStatusFn({ data: {session_token: sessionToken} })
        console.log('[TG Auth] polling:', status)
        
        if (status.status === 'completed' && status.token) {
          // Сохраняем сессию
          const session = await import('@/lib/session').then(m => m.useAppSession())
          await session.update({ 
            token: status.token, 
            isAdmin: status.role === 'ADMIN', 
            isModerator: status.role === 'MODERATOR' 
          })
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

  // Email registration
  const registerMutation = useMutation({
    mutationFn: () => registerEmailFn({data: {
      email: formData.email,
      password: formData.password,
      firstName: formData.firstName,
      lastName: formData.lastName || undefined,
      phone: formData.preferredContact === 'PHONE' ? formData.contactValue : '',
      preferredContact: formData.preferredContact,
      contactValue: formData.contactValue,
    }}),
    onSuccess: () => {
      setRegisteredEmail(formData.email)
    },
    onError: (err) => {
      setError(err.message || 'Произошла ошибка')
    },
  })

  const resendMutation = useMutation({
    mutationFn: (email: string) => resendConfirmationFn({data: { email }}),
    onSuccess: (data) => {
      alert(data.message || 'Письмо отправлено')
    },
    onError: (err) => {
      alert(err.message || 'Ошибка отправки')
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
      if (!formData.email || !formData.password || !formData.firstName.trim() || !formData.contactValue.trim()) {
        setError('Заполните все обязательные поля')
        return
      }
      if (formData.password.length < 6) {
        setError('Пароль должен быть не менее 6 символов')
        return
      }
      
      registerMutation.mutate()
    }
  }

  // Если уже авторизован - редирект
  if (token) {
    navigate({ to: '/' })
    return null
  }

  // Показываем экран подтверждения email
  if (registeredEmail) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <MailCheck className="mx-auto size-16 text-green-500 mb-4" />
            <h1 className="text-2xl font-bold text-(--sea-ink) mb-2">
              Почти готово!
            </h1>
            <p className="text-(--sea-ink-soft)">
              Письмо отправлено на <strong>{registeredEmail}</strong>
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8 text-center space-y-4">
            <div className="bg-green-50 rounded-xl p-4">
              <p className="text-sm text-green-800">
                Нажмите на ссылку в письме, чтобы подтвердить регистрацию.
                После подтверждения вы будете автоматически авторизованы.
              </p>
            </div>

            <div className="text-sm text-(--sea-ink-soft)">
              <p>Не пришло письмо?</p>
              <ol className="mt-2 text-left space-y-1 list-decimal list-inside">
                <li>Проверьте папку «Спам»</li>
                <li>Убедитесь, что адрес {registeredEmail} указан верно</li>
              </ol>
              <button
                onClick={() => resendMutation.mutate(registeredEmail)}
                disabled={resendMutation.isPending}
                className="mt-3 inline-flex items-center gap-1 text-sm text-(--palm) hover:underline disabled:opacity-50"
              >
                <RefreshCw className={`size-3.5 ${resendMutation.isPending ? 'animate-spin' : ''}`} />
                {resendMutation.isPending ? 'Отправка...' : 'Выслать повторно'}
              </button>
            </div>

            <div className="pt-4 border-t border-(--line)">
              <p className="text-xs text-(--sea-ink-soft) mb-3">
                Уже подтвердили?{' '}
                <Link to="/auth/login" className="text-(--palm) hover:underline font-medium">
                  Войти
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-(--sea-ink) mb-2">TBSALE</h1>
          <p className="text-(--sea-ink-soft)">Создайте аккаунт</p>
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
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className={`flex size-10 items-center justify-center rounded-full ${
                method === 'telegram' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600'
              }`}>
                <MessageCircle className="size-5" />
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium text-(--sea-ink)">Telegram</div>
                <div className="text-xs text-(--sea-ink-soft)">Быстрая регистрация через бота</div>
              </div>
              {method === 'telegram' && <CheckCircle className="size-5 text-blue-500" />}
            </button>

            <button
              onClick={() => setMethod('email')}
              className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                method === 'email'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className={`flex size-10 items-center justify-center rounded-full ${
                method === 'email' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600'
              }`}>
                <Mail className="size-5" />
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium text-(--sea-ink)">Email</div>
                <div className="text-xs text-(--sea-ink-soft)">Классическая регистрация</div>
              </div>
              {method === 'email' && <CheckCircle className="size-5 text-blue-500" />}
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
                  {telegramInitMutation.isPending ? 'Загрузка...' : 'Продолжить с Telegram'}
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
                  <p className="font-medium text-green-600">Регистрация успешна!</p>
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
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-(--sea-ink)">Имя <span className="text-red-500">*</span></label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
                    <input
                      type="text"
                      value={formData.firstName}
                      onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition"
                      placeholder="Иван"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-(--sea-ink)">Фамилия</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
                    <input
                      type="text"
                      value={formData.lastName}
                      onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition"
                      placeholder="Иванов"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-(--sea-ink)">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition"
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
                    className="w-full pl-10 pr-12 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition"
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

              <div className="space-y-2">
                <label className="text-sm font-medium text-(--sea-ink)">Предпочтительный способ связи <span className="text-red-500">*</span></label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { value: 'TELEGRAM', label: 'Telegram', icon: '📱' },
                    { value: 'EMAIL', label: 'Email', icon: '📧' },
                    { value: 'PHONE', label: 'Телефон', icon: '📞' },
                    { value: 'MAX', label: 'MAX', icon: '💬' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setFormData({ ...formData, preferredContact: opt.value, contactValue: '' })}
                      className={`flex items-center justify-center gap-1.5 rounded-xl border px-3 py-2.5 text-sm font-medium transition ${
                        formData.preferredContact === opt.value
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <span>{opt.icon}</span>
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-(--sea-ink)">
                  {formData.preferredContact === 'TELEGRAM' && 'Telegram username или ID'}
                  {formData.preferredContact === 'EMAIL' && 'Email'}
                  {formData.preferredContact === 'PHONE' && 'Телефон'}
                  {formData.preferredContact === 'MAX' && 'Контакт в MAX'}
                  {!formData.preferredContact && 'Контакт'}
                  {' '}<span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={formData.preferredContact === 'EMAIL' ? 'email' : formData.preferredContact === 'PHONE' ? 'tel' : 'text'}
                    value={formData.contactValue}
                    onChange={(e) => setFormData({ ...formData, contactValue: e.target.value })}
                    className="w-full rounded-xl border border-gray-300 px-4 py-2.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition"
                    placeholder={
                      formData.preferredContact === 'TELEGRAM' ? '@username или 123456789' :
                      formData.preferredContact === 'EMAIL' ? 'example@mail.ru' :
                      formData.preferredContact === 'PHONE' ? '+7 (999) 123-45-67' :
                      formData.preferredContact === 'MAX' ? 'Ваш логин в MAX' :
                      'Контакт для связи'
                    }
                    required
                  />
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
                disabled={registerMutation.isPending}
                className="w-full bg-(--palm) hover:bg-(--palm)/90 text-white font-medium py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {registerMutation.isPending ? (
                  'Загрузка...'
                ) : (
                  <>
                    Создать аккаунт
                    <ArrowRight className="size-5" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Footer */}
          <div className="mt-6 text-center text-sm text-(--sea-ink-soft)">
            Уже есть аккаунт?{' '}
            <Link
              to="/auth/login"
              className="text-(--palm) hover:underline font-medium"
            >
              Войти
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