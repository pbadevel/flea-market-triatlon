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
} from 'lucide-react'
import { logoutFn, verifySession } from '@/lib/session'
import { myProfileQueryOptions, myStatsQueryOptions } from '@/lib/queries/profile'
import { updateMyProfile } from '@/lib/api/client/profile'
import { fetchMyAds } from '@/lib/api/client/ads'
import type { UserProfile, UserProfileUpdate } from '@/types/profile'
import type { MyAd } from '@/types/ad'

export const Route = createFileRoute('/_app/profile')({
  loader: async () => {
    const sessionData = await verifySession()
    return sessionData
  },
  component: ProfilePage,
})

function ProfilePage() {
  const { token } = Route.useLoaderData()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)

  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      const result = await logoutFn();
      if (result.success) {
        // Перенаправляем пользователя на главную на стороне клиента
        await navigate({ to: "/" });
      }
    } catch (error) {
      console.error("Ошибка при выходе:", error);
    }
  };

  
  const { data: profile, isLoading: profileLoading } = useQuery(
    myProfileQueryOptions(token!),
  )
  
  const { data: stats } = useQuery(
    myStatsQueryOptions(token!),
  )
  
  const { data: adsData } = useQuery({
    queryKey: ['my-ads'],
    queryFn: () => fetchMyAds(token!),
    enabled: !!token,
  })

  const updateMutation = useMutation({
    mutationFn: (data: UserProfileUpdate) => updateMyProfile(token!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      setIsEditing(false)
    },
    onError: (err) => {
      alert(`Ошибка: ${err.message}`)
    },
  })

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-(--sea-ink) mb-4">
            Требуется авторизация
          </h1>
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

  // Проверка на наличие способов связи
  const hasNoContact = !profile.username && !(profile.email && profile.is_email_verified) && !profile.phone

  return (
    <div className="min-h-screen bg-(--bg)">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-(--line) bg-(--header-bg)">
        <div className="page-wrap">
          <div className="flex h-14 items-center justify-between">
            <h1 className="text-lg font-semibold text-(--sea-ink)">Профиль</h1>
            <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 text-(--sea-ink-soft) hover:text-red-500 transition-colors"
                  title="Выйти"
                >
                  <LogOut className="size-5" />
                  <span className="text-sm">Выйти</span>
                </button>
            <Link
              to="/"
              className="text-sm text-(--sea-ink-soft) hover:text-(--sea-ink)"
            >
              На главную
            </Link>
          </div>
        </div>
      </header>

      {/* Баннер — нет способов связи */}
      {hasNoContact && (
        <div className="bg-red-50 border-b border-red-200">
          <div className="page-wrap py-3">
            <div className="flex items-center gap-2 text-sm text-red-700">
              <span className="text-lg">⚠️</span>
              <span>
                У вас нет способов связи. <strong>Клиенты не смогут с вами связаться.</strong>{' '}
                <Link to="/profile" className="underline font-medium">Добавьте контакты</Link>
                , чтобы получать отклики.
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="page-wrap py-8 space-y-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              icon={<Package className="size-5" />}
              label="Всего объявлений"
              value={stats.total_ads}
            />
            <StatCard
              icon={<CheckCircle className="size-5" />}
              label="Активные"
              value={stats.active_ads}
              color="green"
            />
            <StatCard
              icon={<Clock className="size-5" />}
              label="На модерации"
              value={stats.pending_ads}
              color="yellow"
            />
            <StatCard
              icon={<TrendingUp className="size-5" />}
              label="Продано"
              value={stats.sold_ads}
              color="blue"
            />
          </div>
        )}

        {/* Profile Info */}
        <div className="rounded-lg border border-(--line) bg-white p-6">
          <div className="flex items-center justify-between mb-6 gap-2 flex-wrap">
            <h2 className="text-xl font-bold text-(--sea-ink) shrink-0">
              Информация о пользователе
            </h2>
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
            />
          ) : (
            <ProfileInfo profile={profile} />
          )}
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-3">
          {profile.is_moderator && (
            <Badge icon={<Shield className="size-4" />} label="Модератор" color="blue" />
          )}
          {profile.is_trusted_seller && (
            <Badge icon={<Star className="size-4" />} label="Проверенный продавец" color="green" />
          )}
        </div>

        {/* My Ads */}
        <div className="rounded-lg border border-(--line) bg-white p-6 mb-10">
          <div className="flex items-center justify-between mb-6 gap-2 flex-wrap">
            <h2 className="text-xl font-bold text-(--sea-ink) shrink-0">
              Мои объявления
            </h2>
            <Link
              to="/create-ad"
              className="shrink-0 text-sm text-(--palm) hover:underline whitespace-nowrap"
            >
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
              <Link
                to="/create-ad"
                className="inline-block mt-4 text-(--palm) hover:underline"
              >
                Создать первое объявление
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ─── Вспомогательные компоненты ── */

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
    <div className="rounded-lg border border-(--line) bg-white p-4">
      <div className={`flex items-center gap-2 ${colorMap[color]} mb-2`}>
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
    </div>
  )
}


function ProfileInfo({ profile }: { profile: UserProfile }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <InfoField
          icon={<User className="size-4" />}
          label="Имя"
          value={profile.first_name || 'Не указано'}
        />
        <InfoField
          icon={<User className="size-4" />}
          label="Фамилия"
          value={profile.last_name || 'Не указано'}
        />
        <InfoField
          icon={<MessageCircle className="size-4" />}
          label="Telegram Username"
          value={profile.username ? `@${profile.username}` : 'Не указан'}
        />
        <InfoField
          icon={<Mail className="size-4" />}
          label="Email"
          value={profile.email || 'Не указан'}
        />
        {profile.email && !profile.is_email_verified && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-yellow-50 border border-yellow-200">
            <span className="text-yellow-600 text-lg">⚠️</span>
            <div className="text-sm text-yellow-800">
              <p className="font-medium">Email не подтверждён</p>
              <p className="text-xs mt-0.5">Проверьте почту {profile.email} и перейдите по ссылке из письма</p>
            </div>
          </div>
        )}
        <InfoField
          icon={<Phone className="size-4" />}
          label="Телефон"
          value={profile.phone || 'Не указан'}
        />
      </div>
      
      <div className="pt-4 border-t border-(--line)">
        <p className="text-sm text-(--sea-ink-soft)">
          Зарегистрирован: {new Date(profile.created_at).toLocaleDateString('ru-RU')}
        </p>
        <p className="text-sm text-(--sea-ink-soft)">
          Telegram ID: {profile.tg_user_id}
        </p>
      </div>
    </div>
  )
}


function InfoField({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
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
}: {
  profile: UserProfile
  onSave: (data: UserProfileUpdate) => void
  onCancel: () => void
  isPending: boolean
}) {
  const [formData, setFormData] = useState({
    first_name: profile.first_name || '',
    last_name: profile.last_name || '',
    phone: profile.phone || '',
    email: profile.email || '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
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
            className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            placeholder="Иван"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-(--sea-ink)">Фамилия</label>
          <input
            type="text"
            value={formData.last_name}
            onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
            className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            placeholder="Иванов"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-(--sea-ink)">Email</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            placeholder="example@mail.ru"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-(--sea-ink)">Телефон</label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            placeholder="+7 (999) 123-45-67"
          />
        </div>
      </div>

      <div className="p-4 bg-blue-50 rounded-lg text-sm text-blue-800">
        <p className="font-medium mb-1">Telegram Username</p>
        <p className="text-blue-600">
          {profile.username ? `@${profile.username}` : 'Не указан'}
        </p>
        <p className="text-xs text-blue-500 mt-1">
          Изменяется только через Telegram
        </p>
      </div>

      <div className="flex gap-3 pt-4">
        <button
          type="submit"
          disabled={isPending}
          className="flex items-center gap-2 rounded-lg bg-(--palm) px-6 py-2 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50"
        >
          <Save className="size-4" />
          {isPending ? 'Сохранение...' : 'Сохранить'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-(--line) px-6 py-2 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover)"
        >
          Отмена
        </button>
      </div>
    </form>
  )
}

function Badge({
  icon,
  label,
  color,
}: {
  icon: React.ReactNode
  label: string
  color: 'blue' | 'green'
}) {
  const colorMap = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${colorMap[color]}`}>
      {icon}
      {label}
    </span>
  )
}

function ContactInfo({ contactMethod }: { contactMethod: string }) {
  // Определяем тип контакта
  let type = 'Контакт'
  let displayValue = contactMethod
  let link = null

  if (contactMethod.startsWith('@')) {
    type = 'Telegram'
    displayValue = contactMethod
    link = `https://t.me/${contactMethod.substring(1)}`
  } else if (contactMethod.startsWith('tg://user?id=')) {
    type = 'Telegram'
    const userId = contactMethod.replace('tg://user?id=', '')
    displayValue = `ID: ${userId}`
    link = contactMethod
  } else if (/^\+?\d{10,15}$/.test(contactMethod.replace(/\s/g, ''))) {
    type = 'Телефон'
    displayValue = contactMethod
    link = `tel:${contactMethod}`
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-(--sea-ink-soft)">{type}:</span>
      {link ? (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-(--palm) hover:underline"
        >
          {displayValue}
        </a>
      ) : (
        <span className="text-sm font-medium text-(--sea-ink)">{displayValue}</span>
      )}
    </div>
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

  const { label, color } = statusConfig[ad.status as keyof typeof statusConfig] || statusConfig.pending

  return (
    <Link
      to="/product/$productId"
      params={{ productId: String(ad.id) }}
      className="flex gap-2 rounded-lg border border-(--line) p-4 hover:bg-(--link-bg-hover) transition"
    >
      {/* Добавили w-full для растягивания и justify-between для разнесения по краям */}
      <div className="flex w-full justify-between items-start"> 
        
        {/* ЛЕВАЯ ЧАСТЬ: Картинка + Характеристики */}
        <div className="flex">
          {ad.cover_url && (
            <img
              src={ad.cover_url}
              alt={ad.title}
              className="h-20 w-20 shrink-0 rounded-lg object-cover"
            />
          )}
          <div className="flex flex-col px-3 justify-start">
            <h3 className="font-medium text-(--sea-ink) line-clamp-1">{ad.title}</h3>
            <p className="mt-1 text-lg font-bold text-(--sea-ink)">
              {ad.price.toLocaleString()} ₽
            </p>
            <p className="mt-1 text-sm text-(--sea-ink-soft)">
              {ad.city} · {ad.category}
            </p>
          </div>
        </div>

        {/* ПРАВАЯ ЧАСТЬ: Статус (одобрено) + Дата */}
        {/* Изменено на items-end, чтобы текст внутри выравнивался по правому краю */}
        <div className="flex flex-col gap-2 items-end justify-between h-full min-h-[80px]">
          <span className={`rounded-full px-2 py-1 text-xs text-center font-medium ${color}`}>
            {label}
          </span>
          <span className="text-xs text-(--sea-ink-soft)">
            {new Date(ad.created_at).toLocaleDateString('ru-RU')}
          </span>
        </div>

      </div>
    </Link>
  )
}