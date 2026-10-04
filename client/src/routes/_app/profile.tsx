// src/routes/_app/profile.tsx

import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  User,
  Mail,
  Phone,
  Edit3,
  Save,
  X,
  Package,
  CheckCircle,
  Clock,
  TrendingUp,
  Shield,
  Star,
  MessageCircle,
  LogOut,
  Link as LinkIcon,
  ShieldCheck,
} from 'lucide-react'
import { logoutFn, verifySession } from '@/lib/session'
import { myProfileQueryOptions, myStatsQueryOptions } from '@/lib/queries/profile'
import { updateMyProfile } from '@/lib/api/client/profile'
import { initTelegramLinkFn, checkTelegramAuthStatusFn } from '@/lib/api/auth'
import { fetchMyAds } from '@/lib/api/client/ads'
import type { UserProfile, UserProfileUpdate } from '@/types/profile'
import type { MyAd } from '@/types/ad'
import { PhoneVerificationModal } from '@/components/features/profile/phone-verification-modal'
import { PhoneInput } from '@/components/ui/phone-input'
import { normalizePhone, formatPhone } from '@/lib/utils'

export const Route = createFileRoute('/_app/profile')({
  loader: async () => {
    const sessionData = await verifySession()
    return sessionData
  },
  component: ProfilePage,
})

// ─── Тип для мутации с флагом смены телефона ─────────────────────────────
type ProfileUpdatePayload = UserProfileUpdate & { phoneChanged?: boolean }

function ProfilePage() {
  const { token } = Route.useLoaderData()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [linkState, setLinkState] = useState<'idle' | 'waiting' | 'done'>('idle')
  const [showPhoneVerify, setShowPhoneVerify] = useState(false)
  const [pendingPhone, setPendingPhone] = useState<string | null>(null) // для передачи нового номера в модалку
  const [linkSessionToken, setLinkSessionToken] = useState<string | null>(null)

  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      const result = await logoutFn()
      if (result.success) {
        await navigate({ to: '/' })
      }
    } catch (error) {
      console.error('Ошибка при выходе:', error)
    }
  }

  const { data: profile, isLoading: profileLoading } = useQuery(
    myProfileQueryOptions(token!),
  )

  const { data: stats } = useQuery(myStatsQueryOptions(token!))

  const { data: adsData } = useQuery({
    queryKey: ['my-ads'],
    queryFn: () => fetchMyAds(token!),
    enabled: !!token,
  })

  const updateMutation = useMutation({
    mutationFn: (data: ProfileUpdatePayload) => {
      // Убираем служебный флаг перед отправкой на бэкенд
      const { phoneChanged, ...payload } = data
      return updateMyProfile(token!, payload)
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      setIsEditing(false)

      // Если пользователь сменил номер — открываем модалку верификации
      if (variables.phoneChanged) {
        // setTimeout нужен, чтобы профиль успел обновиться из queryClient
        setTimeout(() => setShowPhoneVerify(true), 300)
      }
    },
    onError: (err) => {
      alert(`Ошибка: ${err.message}`)
    },
  })

  const handleLinkTelegram = async () => {
    try {
      const result = await initTelegramLinkFn({ data: { token: token! } })
      setLinkSessionToken(result.session_token)
      setLinkState('waiting')
      const opened = window.open(result.deeplink, '_blank')
      if (!opened) {
        await navigator.clipboard.writeText(result.deeplink)
        alert('Ссылка скопирована. Откройте Telegram и перейдите по ссылке.')
      }
    } catch (err: any) {
      alert(err.message || 'Ошибка при инициализации привязки')
    }
  }

  useQuery({
    queryKey: ['telegram-link-status', linkSessionToken],
    queryFn: async () => {
      if (!linkSessionToken) return null
      try {
        const res = await checkTelegramAuthStatusFn({
          data: { session_token: linkSessionToken },
        })
        if (res.status === 'completed') {
          setLinkState('done')
          queryClient.invalidateQueries({ queryKey: ['profile'] })
          return { done: true }
        }
        if (res.status === 'expired') {
          setLinkState('idle')
          setLinkSessionToken(null)
          return null
        }
        return { pending: true }
      } catch (err) {
        return { pending: true }
      }
    },
    enabled: linkState === 'waiting' && !!linkSessionToken,
    refetchInterval: 2000,
  })

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-(--sea-ink) mb-4">Требуется авторизация</h1>
          <Link to="/auth/login" className="text-(--palm) hover:underline">
            Войти
          </Link>
        </div>
      </div>
    )
  }

  if (profileLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-(--sea-ink-soft)">Загрузка...</div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-500">Ошибка загрузки профиля</div>
      </div>
    )
  }

  const hasNoContact =
    !profile.username && !(profile.email && profile.is_email_verified) && !profile.phone

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 bg-(--header-bg) backdrop-blur-xl">
        <div className="page-wrap">
          <div className="flex h-14 items-center justify-between">
            <h1 className="text-lg font-semibold text-(--sea-ink)">Профиль</h1>
            <div className="flex items-center gap-3">
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 text-(--sea-ink-soft) hover:text-red-500 transition-colors"
                title="Выйти"
              >
                <LogOut className="size-5" />
                <span className="text-sm">Выйти</span>
              </button>
              <Link to="/" className="text-sm text-(--sea-ink-soft) hover:text-(--sea-ink)">
                На главную
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="page-wrap py-4 space-y-4">
        {/* Telegram linking banners */}
        {linkState === 'waiting' && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl">
            <div className="py-3 px-4">
              <div className="flex items-center gap-2 text-sm text-blue-700">
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                <span>
                  Откройте Telegram и подтвердите привязку. <strong>Ожидание...</strong>
                </span>
              </div>
            </div>
          </div>
        )}

        {linkState === 'done' && (
          <div className="bg-green-50 border border-green-200 rounded-xl">
            <div className="py-3 px-4">
              <div className="flex items-center gap-2 text-sm text-green-700">
                <CheckCircle className="size-4" />
                <span>Telegram успешно привязан!</span>
              </div>
            </div>
          </div>
        )}

        {/* Phone verification banner */}
        {profile.phone && !profile.phone_verified && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl">
            <div className="py-3 px-4 flex items-center gap-2 text-sm text-yellow-800">
              <Phone className="size-4 shrink-0" />
              <span>
                Номер <strong>{profile.phone}</strong> не подтверждён. Без подтверждения вы не
                сможете размещать объявления.
              </span>
              <button
                onClick={() => {
                  setPendingPhone(profile.phone)
                  setShowPhoneVerify(true)
                }}
                className="ml-auto shrink-0 font-medium underline"
              >
                Подтвердить
              </button>
            </div>
          </div>
        )}

        {hasNoContact && (
          <div className="bg-red-50 border border-red-200 rounded-xl">
            <div className="py-3 px-4">
              <div className="flex items-center gap-2 text-sm text-red-700">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                <span>
                  У вас нет способов связи. <strong>Клиенты не смогут с вами связаться.</strong>{' '}
                  <Link to="/profile" className="underline font-medium">
                    Добавьте контакты
                  </Link>
                  , чтобы получать отклики.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard icon={<Package className="size-5" />} label="Всего объявлений" value={stats.total_ads} />
            <StatCard icon={<CheckCircle className="size-5" />} label="Активные" value={stats.active_ads} color="green" />
            <StatCard icon={<Clock className="size-5" />} label="На модерации" value={stats.pending_ads} color="yellow" />
            <StatCard icon={<TrendingUp className="size-5" />} label="Продано" value={stats.sold_ads} color="blue" />
          </div>
        )}

        {/* ─── ЕДИНСТВЕННЫЙ блок с информацией о пользователе ─── */}
        <div className="rounded-2xl border border-(--line) bg-(--surface-strong) p-6">
          <div className="flex items-center justify-between mb-6 gap-2 flex-wrap">
            <h2 className="text-xl font-bold text-(--sea-ink) shrink-0">Информация о пользователе</h2>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="shrink-0 flex items-center gap-1.5 text-sm text-(--palm) hover:underline whitespace-nowrap"
            >
              {isEditing ? (
                <>
                  <X className="size-4 shrink-0" />
                  Отмена
                </>
              ) : (
                <>
                  <Edit3 className="size-4 shrink-0" />
                  Редактировать
                </>
              )}
            </button>
          </div>

          {isEditing ? (
            <EditProfileForm
              profile={profile}
              onSave={(data) => updateMutation.mutate(data)}
              onCancel={() => setIsEditing(false)}
              isPending={updateMutation.isPending}
              onLinkTelegram={handleLinkTelegram}
            />
          ) : (
            <ProfileInfo
              profile={profile}
              onLinkTelegram={handleLinkTelegram}
              onVerifyPhone={() => {
                setPendingPhone(profile.phone)
                setShowPhoneVerify(true)
              }}
            />
          )}
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-2">
          {profile.is_moderator && (
            <Badge icon={<Shield className="size-4" />} label="Модератор" color="blue" />
          )}
          {profile.is_trusted_seller && (
            <Badge icon={<Star className="size-4" />} label="Проверенный продавец" color="green" />
          )}
        </div>

        {/* My ads */}
        <div className="rounded-2xl border border-(--line) bg-(--surface-strong) p-6 mb-10">
          <div className="flex items-center justify-between mb-6 gap-2 flex-wrap">
            <h2 className="text-xl font-bold text-(--sea-ink) shrink-0">Мои объявления</h2>
            <Link to="/create-ad" className="shrink-0 text-sm text-(--palm) hover:underline whitespace-nowrap">
              Создать новое
            </Link>
          </div>

          {adsData?.data && adsData.data.length > 0 ? (
            <div className="space-y-3">
              {adsData.data.map((ad: MyAd) => (
                <AdCard key={ad.id} ad={ad} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-(--sea-ink-soft)">
              <Package className="mx-auto size-12 mb-2 opacity-50" />
              <p>У вас пока нет объявлений</p>
              <Link to="/create-ad" className="inline-block mt-4 text-(--palm) hover:underline">
                Создать первое объявление
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* ─── МОДАЛКА ВЕРИФИКАЦИИ ─── */}
      {showPhoneVerify && (
        <PhoneVerificationModal
          token={token!}
          initialPhone={pendingPhone ?? profile.phone}
          onClose={() => {
            setShowPhoneVerify(false)
            setPendingPhone(null)
          }}
        />
      )}
    </div>
  )
}

// ─── Остальные компоненты ────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  color = 'default',
}: {
  icon: React.ReactNode
  label: string
  value: number
  color?: 'default' | 'green' | 'yellow' | 'blue'
}) {
  const colorMap = {
    default: 'text-(--sea-ink)',
    green: 'text-green-600',
    yellow: 'text-yellow-600',
    blue: 'text-blue-600',
  }

  return (
    <div className="rounded-2xl border border-(--line) bg-(--surface-strong) p-4">
      <div className={`flex items-center gap-2 ${colorMap[color]} mb-2`}>
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
    </div>
  )
}

function ProfileInfo({
  profile,
  onLinkTelegram,
  onVerifyPhone,
}: {
  profile: UserProfile
  onLinkTelegram?: () => void
  onVerifyPhone?: () => void
}) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <InfoField icon={<User className="size-4" />} label="Имя" value={profile.first_name || 'Не указано'} />
        <InfoField icon={<User className="size-4" />} label="Фамилия" value={profile.last_name || 'Не указано'} />

        {/* ─── Блок телефона с бейджем верификации ─── */}
        <div>
          <InfoField icon={<Phone className="size-4" />} label="Телефон" value={profile.phone || 'Не указан'} />
          {profile.phone ? (
            profile.phone_verified ? (
              <span className="mt-1.5 inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">
                <ShieldCheck className="size-3" />
                Подтверждён
              </span>
            ) : (
              <button
                onClick={onVerifyPhone}
                className="mt-1.5 inline-flex items-center gap-1 rounded-full border border-yellow-200 bg-yellow-50 px-2.5 py-0.5 text-xs font-medium text-yellow-800 hover:bg-yellow-100"
              >
                Не подтверждён — подтвердить
              </button>
            )
          ) : (
            <button
              onClick={onVerifyPhone}
              className="mt-1.5 text-xs font-medium text-(--palm) hover:underline"
            >
              Добавить и подтвердить телефон
            </button>
          )}
        </div>

        {/* Telegram */}
        <div>
          <InfoField
            icon={<MessageCircle className="size-4" />}
            label="Telegram Username"
            value={profile.username ? `@${profile.username}` : 'Не указан'}
          />
          {!profile.tg_user_id && onLinkTelegram && (
            <button
              onClick={onLinkTelegram}
              className="mt-2 flex items-center gap-1.5 text-sm text-(--palm) hover:underline"
            >
              <LinkIcon className="size-3.5" />
              Привязать Telegram
            </button>
          )}
        </div>

        {/* Email */}
        <div>
          <InfoField icon={<Mail className="size-4" />} label="Email" value={profile.email || 'Не указан'} />
          {profile.email && !profile.is_email_verified && (
            <div className="mt-1.5 flex items-center gap-2 p-3 rounded-xl bg-yellow-50 border border-yellow-200">
              <div className="w-2 h-2 rounded-full bg-yellow-500" />
              <div className="text-sm text-yellow-800">
                <p className="font-medium">Email не подтверждён</p>
                <p className="text-xs mt-0.5">
                  Проверьте почту {profile.email} и перейдите по ссылке из письма
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Preferred contact */}
        <InfoField
          icon={<MessageCircle className="size-4" />}
          label="Предпочтительная связь"
          value={
            profile.preferred_contact === 'TELEGRAM'
              ? `Telegram: ${profile.contact_value || 'Не указан'}`
              : profile.preferred_contact === 'EMAIL'
                ? `Email: ${profile.contact_value || 'Не указан'}`
                : profile.preferred_contact === 'PHONE'
                  ? `Телефон: ${profile.contact_value || 'Не указан'}`
                  : profile.preferred_contact === 'MAX'
                    ? `MAX: ${profile.contact_value || 'Не указан'}`
                    : 'Не указан'
          }
        />
      </div>

      <div className="pt-4 border-t border-(--line)">
        <p className="text-sm text-(--sea-ink-soft)">
          Зарегистрирован: {new Date(profile.created_at).toLocaleDateString('ru-RU')}
        </p>
        <p className="text-sm text-(--sea-ink-soft)">
          Telegram ID: {profile.tg_user_id ?? 'Не привязан'}
        </p>
      </div>
    </div>
  )
}

function InfoField({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 text-(--sea-ink-soft)">{icon}</div>
      <div>
        <div className="text-xs text-(--sea-ink-soft)">{label}</div>
        <div className="font-medium text-(--sea-ink)">{value}</div>
      </div>
    </div>
  )
}

function EditProfileForm({
  profile,
  onSave,
  onCancel,
  isPending,
  onLinkTelegram,
}: {
  profile: UserProfile
  onSave: (data: ProfileUpdatePayload) => void
  onCancel: () => void
  isPending: boolean
  onLinkTelegram?: () => void
}) {
  // Форматируем номер при инициализации (из E.164 в маску)
  const [formData, setFormData] = useState({
    first_name: profile.first_name || '',
    last_name: profile.last_name || '',
    phone: profile.phone ? formatPhone(profile.phone) : '',
    email: profile.email || '',
    preferred_contact: profile.preferred_contact || 'TELEGRAM',
    contact_value: profile.contact_value || '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Определяем, изменился ли номер (сравниваем нормализованные)
    const oldPhone = profile.phone ? normalizePhone(profile.phone) : ''
    const newPhone = formData.phone ? normalizePhone(formData.phone) : ''
    const phoneChanged = oldPhone !== newPhone

    // Нормализуем телефон перед отправкой (E.164)
    const payload: ProfileUpdatePayload = {
      first_name: formData.first_name || undefined,
      last_name: formData.last_name || undefined,
      phone: newPhone || undefined,
      email: formData.email || undefined,
      preferred_contact: formData.preferred_contact,
      contact_value: formData.contact_value || undefined,
      phoneChanged, // Служебный флаг для onSuccess
    }

    onSave(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-(--sea-ink)">Имя</label>
          <input
            type="text"
            value={formData.first_name}
            onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
            className="w-full rounded-xl border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            placeholder="Иван"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-(--sea-ink)">Фамилия</label>
          <input
            type="text"
            value={formData.last_name}
            onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
            className="w-full rounded-xl border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            placeholder="Иванов"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-(--sea-ink)">Email</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full rounded-xl border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            placeholder="example@mail.ru"
          />
        </div>

        <div className="space-y-2">
          <PhoneInput
            value={formData.phone}
            onChange={(v) => setFormData({ ...formData, phone: v })}
            label="Телефон"
          />
          {profile.phone_verified && formData.phone === (profile.phone ? formatPhone(profile.phone) : '') && (
            <p className="text-xs text-green-700">
              ✓ Номер подтверждён
            </p>
          )}
          {profile.phone_verified && formData.phone !== (profile.phone ? formatPhone(profile.phone) : '') && formData.phone && (
            <p className="text-xs text-yellow-700">
              Номер изменён. После сохранения потребуется повторное подтверждение по SMS.
            </p>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-(--sea-ink)">Предпочтительный способ связи</label>
        <div className="grid grid-cols-2 gap-2">
          {[
            { value: 'TELEGRAM', label: 'Telegram' },
            { value: 'EMAIL', label: 'Email' },
            { value: 'PHONE', label: 'Телефон' },
            { value: 'MAX', label: 'MAX' },
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setFormData({ ...formData, preferred_contact: opt.value, contact_value: '' })}
              className={`flex items-center justify-center gap-1.5 rounded-xl border px-3 py-2.5 text-sm font-medium transition ${
                formData.preferred_contact === opt.value
                  ? 'border-(--palm) bg-(--palm)/10 text-(--palm)'
                  : 'border-(--line) text-(--sea-ink-soft) hover:bg-(--link-bg-hover)'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-(--sea-ink)">
          {formData.preferred_contact === 'TELEGRAM' && 'Telegram username или ID'}
          {formData.preferred_contact === 'EMAIL' && 'Email для связи'}
          {formData.preferred_contact === 'PHONE' && 'Телефон для связи'}
          {formData.preferred_contact === 'MAX' && 'Контакт в MAX'}
        </label>
        <input
          type={
            formData.preferred_contact === 'EMAIL'
              ? 'email'
              : formData.preferred_contact === 'PHONE'
                ? 'tel'
                : 'text'
          }
          value={formData.contact_value}
          onChange={(e) => setFormData({ ...formData, contact_value: e.target.value })}
          className="w-full rounded-xl border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
          placeholder={
            formData.preferred_contact === 'TELEGRAM'
              ? '@username или 123456789'
              : formData.preferred_contact === 'EMAIL'
                ? 'example@mail.ru'
                : formData.preferred_contact === 'PHONE'
                  ? '+7 (999) 123-45-67'
                  : 'Ваш логин в MAX'
          }
        />
      </div>

      <div className="p-4 bg-(--palm)/5 rounded-xl text-sm">
        <p className="font-medium mb-1 text-(--sea-ink)">Telegram Username</p>
        <p className="text-(--palm)">{profile.username ? `@${profile.username}` : 'Не указан'}</p>
        {profile.tg_user_id == null ? (
          <button
            onClick={onLinkTelegram}
            className="mt-2 flex items-center gap-1.5 text-sm font-medium text-(--palm) hover:underline"
          >
            <LinkIcon className="size-3.5" />
            Привязать Telegram
          </button>
        ) : (
          <p className="text-xs text-(--sea-ink-soft) mt-1">Изменяется только через Telegram</p>
        )}
      </div>

      <div className="flex gap-3 pt-4">
        <button
          type="submit"
          disabled={isPending}
          className="flex items-center gap-2 rounded-xl bg-(--palm) px-6 py-2.5 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50"
        >
          <Save className="size-4" />
          {isPending ? 'Сохранение...' : 'Сохранить'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-xl border border-(--line) px-6 py-2.5 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover)"
        >
          Отмена
        </button>
      </div>
    </form>
  )
}

function Badge({ icon, label, color }: { icon: React.ReactNode; label: string; color: 'blue' | 'green' }) {
  const colorMap = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${colorMap[color]}`}
    >
      {icon}
      {label}
    </span>
  )
}

function AdCard({ ad }: { ad: MyAd }) {
  const statusConfig = {
    pending: { label: 'На модерации', color: 'bg-yellow-100 text-yellow-800' },
    approved: { label: 'Одобрено', color: 'bg-green-100 text-green-800' },
    rejected: { label: 'Отклонено', color: 'bg-red-100 text-red-800' },
    sold: { label: 'Продано', color: 'bg-blue-100 text-blue-800' },
    removed: { label: 'Удалено', color: 'bg-gray-100 text-gray-800' },
  }

  const { label, color } =
    statusConfig[ad.status as keyof typeof statusConfig] || statusConfig.pending

  return (
    <Link
      to="/product/$productId"
      params={{ productId: String(ad.id) }}
      className="flex gap-2 rounded-2xl border border-(--line) p-4 hover:bg-(--link-bg-hover) transition"
    >
      <div className="flex w-full justify-between items-start">
        <div className="flex">
          {ad.cover_url && (
            <img src={ad.cover_url} alt={ad.title} className="h-20 w-20 shrink-0 rounded-xl object-cover" />
          )}
          <div className="flex flex-col px-3 justify-start">
            <h3 className="font-medium text-(--sea-ink) line-clamp-1">{ad.title}</h3>
            <p className="mt-1 text-lg font-bold text-(--sea-ink)">{ad.price.toLocaleString()} ₽</p>
            <p className="mt-1 text-sm text-(--sea-ink-soft)">
              {ad.city} · {ad.category}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2 items-end justify-between h-full min-h-[80px]">
          <span className={`rounded-full px-2 py-1 text-xs text-center font-medium ${color}`}>{label}</span>
          <span className="text-xs text-(--sea-ink-soft)">
            {new Date(ad.created_at).toLocaleDateString('ru-RU')}
          </span>
        </div>
      </div>
    </Link>
  )
}