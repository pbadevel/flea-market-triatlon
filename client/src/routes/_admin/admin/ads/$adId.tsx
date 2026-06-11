// src/routes/admin/ads/$adId.tsx
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  MapPin,
  Tag,
  User,
  MessageCircle,
  Star,
  Shield,
  CheckCircle2,
} from 'lucide-react'
import { verifySession } from '@/lib/session'
import { adminAdDetailQueryOptions } from '@/lib/queries/moderator'
import { moderateAd } from '@/lib/api/admin/moderator'
import type { AdminAdPhoto, AdminSeller } from '@/types/admin'

export const Route = createFileRoute('/_admin/admin/ads/$adId')({
  loader: async ({ params }) => {
    const session = await verifySession()
    // console.log(params.adId/)
    
    return {
      token: session?.token ?? null,
      isAdmin: session?.isAdmin ?? false,
      isModerator: session?.isModerator ?? false,
      adId: parseInt(params.adId),
    }
  },
  component: AdminAdPreviewPage,
})


function AdminAdPreviewPage() {
  const { token, adId } = Route.useLoaderData()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [rejectionReason, setRejectionReason] = useState('')
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0)

  const { data: ad, isLoading, isError, error } = useQuery(
    adminAdDetailQueryOptions(token!, adId),
  )


  const moderateMutation = useMutation({
    mutationFn: ({ action, reason }: { action: 'approve' | 'reject'; reason?: string }) =>
      moderateAd(token!, adId, { action, rejection_reason: reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin'] })
      navigate({ to: '/admin' })
    },
    onError: (err) => {
      alert(`Ошибка: ${err.message}`)
    },
  })

  const handleApprove = () => {
    if (confirm(`Одобрить объявление "${ad?.title}"?`)) {
      moderateMutation.mutate({ action: 'approve' })
    }
  }

  const handleReject = () => {
    setShowRejectModal(true)
  }

  const confirmReject = () => {
    moderateMutation.mutate({
      action: 'reject',
      reason: rejectionReason || 'Не указана причина',
    })
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-(--sea-ink) mb-4">
            Требуется авторизация
          </h1>
          <Link to="/" className="text-(--palm) hover:underline">
            На главную
          </Link>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-(--sea-ink-soft)">Загрузка...</div>
      </div>
    )
  }

  if (isError || !ad) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-(--sea-ink) mb-4">
            Объявление не найдено
          </h1>
          <p className="text-(--sea-ink-soft) mb-6">
            {error instanceof Error ? error.message : 'Произошла ошибка'}
          </p>
          <Link to="/admin" className="text-(--palm) hover:underline">
            Вернуться к списку
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-(--bg)">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-(--line) bg-(--header-bg)">
        <div className="page-wrap">
          <div className="flex h-14 items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                to="/admin"
                className="flex items-center gap-1 text-(--sea-ink-soft) hover:text-(--sea-ink)"
              >
                <ArrowLeft className="size-5" />
                <span className="text-sm">Назад</span>
              </Link>
              <h1 className="text-lg font-semibold text-(--sea-ink)">
                Предпросмотр объявления
              </h1>
            </div>
            <StatusBadge status={ad.status} />
          </div>
        </div>
      </header>

      <div className="page-wrap py-8">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Левая колонка - Фотографии */}
          <div className="space-y-4">
            <PhotoCarousel
              photos={ad.photos}
              currentIndex={currentPhotoIndex}
              onIndexChange={setCurrentPhotoIndex}
            />

            {/* Thumbnails */}
            {ad.photos.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-2">
                {ad.photos.map((photo, idx) => (
                  <button
                    key={photo.id}
                    onClick={() => setCurrentPhotoIndex(idx)}
                    className={`shrink-0 aspect-square w-16 overflow-hidden rounded border-2 transition ${
                      currentPhotoIndex === idx
                        ? 'border-(--palm)'
                        : 'border-(--line) hover:border-(--palm)/50'
                    }`}
                  >
                    <PhotoImage photo={photo} className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Правая колонка - Информация */}
          <div className="space-y-6">
            {/* Заголовок и цена */}
            <div>
              <h1 className="text-2xl font-bold text-(--sea-ink) mb-2">
                {ad.title}
              </h1>
              <div className="flex items-baseline gap-3">
                <span className="text-3xl font-bold text-(--sea-ink)">
                  {ad.price.toLocaleString()} ₽
                </span>
                <span className="text-sm text-(--sea-ink-soft)">
                  {ad.ad_type}
                </span>
              </div>
            </div>

            {/* Характеристики */}
            <div className="rounded-lg bg-(--link-bg-hover) p-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <InfoRow label="Город" value={ad.city} icon={<MapPin className="size-4" />} />
                {ad.country && <InfoRow label="Страна" value={ad.country} />}
                <InfoRow label="Категория" value={ad.category} />
                {ad.subcategory && <InfoRow label="Подкатегория" value={ad.subcategory} />}
                {ad.size && <InfoRow label="Размер" value={ad.size} />}
                <InfoRow label="Состояние" value={ad.condition} />
                {ad.delivery_method && <InfoRow label="Доставка" value={ad.delivery_method} />}
                <InfoRow
                  label="Контакт"
                  value={ad.contact_method === 'telegram' ? 'Telegram' : 'Телефон'}
                />
              </div>
            </div>

            {/* Описание */}
            {ad.description && (
              <div className="space-y-2">
                <h2 className="text-lg font-semibold text-(--sea-ink)">Описание</h2>
                <p className="text-(--sea-ink-soft) leading-relaxed whitespace-pre-wrap">
                  {ad.description}
                </p>
              </div>
            )}

            {/* Теги */}
            {ad.tags.length > 0 && (
              <div className="space-y-2">
                <h2 className="text-lg font-semibold text-(--sea-ink) flex items-center gap-2">
                  <Tag className="size-5" />
                  Теги
                </h2>
                <div className="flex flex-wrap gap-2">
                  {ad.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-(--palm)/10 px-3 py-1 text-xs font-medium text-(--palm)"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Продавец */}
            {ad.seller && (
              <SellerInfo seller={ad.seller} />
            )}

            {/* Мета информация */}
            <div className="rounded-lg border border-(--line) bg-white p-4 text-sm">
              <div className="grid grid-cols-2 gap-2 text-(--sea-ink-soft)">
                <div>
                  <span className="font-medium">ID:</span> #{ad.id}
                </div>
                <div>
                  <span className="font-medium">Создано:</span>{' '}
                  {new Date(ad.created_at).toLocaleString('ru-RU')}
                </div>
                {ad.published_at && (
                  <div>
                    <span className="font-medium">Опубликовано:</span>{' '}
                    {new Date(ad.published_at).toLocaleString('ru-RU')}
                  </div>
                )}
                {ad.channel_message_id && (
                  <div>
                    <span className="font-medium">Message ID:</span>{' '}
                    {ad.channel_message_id}
                  </div>
                )}
              </div>
            </div>

            {/* Кнопки модерации */}
            <div className="flex gap-3 pt-4">
              <button
                onClick={handleApprove}
                disabled={moderateMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-green-500 py-3 text-sm font-medium text-white hover:bg-green-600 disabled:opacity-50"
              >
                <CheckCircle className="size-5" />
                Одобрить
              </button>
              <button
                onClick={handleReject}
                disabled={moderateMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-red-500 py-3 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
              >
                <XCircle className="size-5" />
                Отклонить
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6">
            <h3 className="text-lg font-bold text-(--sea-ink) mb-4">
              Отклонить объявление
            </h3>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Укажите причину отклонения..."
              rows={4}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none resize-none"
            />
            <div className="mt-4 flex gap-2">
              <button
                onClick={confirmReject}
                disabled={moderateMutation.isPending}
                className="flex-1 rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
              >
                Отклонить
              </button>
              <button
                onClick={() => {
                  setShowRejectModal(false)
                  setRejectionReason('')
                }}
                className="flex-1 rounded-lg border border-(--line) px-4 py-2 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover)"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Вспомогательные компоненты ── */

function StatusBadge({ status }: { status: string }) {
  const config = {
    pending: { label: 'На модерации', color: 'bg-yellow-100 text-yellow-800' },
    approved: { label: 'Одобрено', color: 'bg-green-100 text-green-800' },
    rejected: { label: 'Отклонено', color: 'bg-red-100 text-red-800' },
    sold: { label: 'Продано', color: 'bg-blue-100 text-blue-800' },
    removed: { label: 'Удалено', color: 'bg-gray-100 text-gray-800' },
  }

  const { label, color } = config[status as keyof typeof config] || config.pending

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium ${color}`}>
      {label}
    </span>
  )
}

function PhotoImage({ photo, className }: { photo: AdminAdPhoto; className?: string }) {
  const url = photo.storage_path
    ? `${import.meta.env.VITE_BACKEND_DOMAIN}/uploads/${photo.storage_path}`
    : photo.file_id
      ? `https://t.me/file/${photo.file_id}`
      : null

  if (!url) {
    return <div className={`${className} bg-gray-200 flex items-center justify-center`}>Нет фото</div>
  }

  return <img src={url} alt="" className={className} />
}

function PhotoCarousel({
  photos,
  currentIndex,
  onIndexChange,
}: {
  photos: AdminAdPhoto[]
  currentIndex: number
  onIndexChange: (index: number) => void
}) {
  if (photos.length === 0) {
    return (
      <div className="aspect-square rounded-lg bg-gray-100 flex items-center justify-center text-(--sea-ink-soft)">
        Нет фотографий
      </div>
    )
  }

  // ИСПРАВЛЕНО: явная проверка на существование фото
  const current = photos[currentIndex]
  if (!current) {
    return (
      <div className="aspect-square rounded-lg bg-gray-100 flex items-center justify-center text-(--sea-ink-soft)">
        Фото не найдено
      </div>
    )
  }

  const next = () => onIndexChange((currentIndex + 1) % photos.length)
  const prev = () => onIndexChange((currentIndex - 1 + photos.length) % photos.length)

  return (
    <div className="relative aspect-square overflow-hidden rounded-lg bg-gray-50">
      <PhotoImage photo={current} className="h-full w-full object-cover" />

      {photos.length > 1 && (
        <>
          <button
            onClick={prev}
            className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-white/80 p-2 text-(--sea-ink) shadow hover:bg-white"
          >
            <ArrowLeft className="size-5" />
          </button>
          <button
            onClick={next}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-white/80 p-2 text-(--sea-ink) shadow hover:bg-white"
          >
            <ArrowLeft className="size-5 rotate-180" />
          </button>
          <div className="absolute bottom-2 right-2 rounded bg-black/50 px-2 py-1 text-xs text-white">
            {currentIndex + 1} / {photos.length}
          </div>
        </>
      )}
    </div>
  )
}

function InfoRow({
  label,
  value,
  icon,
}: {
  label: string
  value: string
  icon?: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-2">
      {icon && <span className="text-(--sea-ink-soft)">{icon}</span>}
      <div>
        <div className="text-xs text-(--sea-ink-soft)">{label}</div>
        <div className="font-medium text-(--sea-ink)">{value}</div>
      </div>
    </div>
  )
}

function SellerInfo({ seller }: { seller: AdminSeller }) {
  return (
    <div className="rounded-lg border border-(--line) bg-white p-4">
      <h2 className="text-lg font-semibold text-(--sea-ink) mb-3 flex items-center gap-2">
        <User className="size-5" />
        Продавец
      </h2>

      <div className="flex items-center gap-3 mb-3">
        <div className="flex size-12 items-center justify-center rounded-full bg-(--link-bg-hover)">
          <User className="size-6 text-(--sea-ink-soft)" />
        </div>
        <div className="flex-1">
          <p className="font-medium text-(--sea-ink)">
            {seller.username || `${seller.first_name || ''} ${seller.last_name || ''}`.trim() || 'Продавец'}
          </p>
          {seller.username && (
            <a
              href={`https://t.me/${seller.username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-(--palm) hover:underline flex items-center gap-1"
            >
              <MessageCircle className="size-3" />
              @{seller.username}
            </a>
          )}
        </div>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-2 mb-3">
        {seller.is_trusted_seller && (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700">
            <CheckCircle2 className="size-3" />
            Проверенный
          </span>
        )}
        {seller.is_moderator && (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">
            <Shield className="size-3" />
            Модератор
          </span>
        )}
      </div>

      {/* Rating */}
      {seller.review_count > 0 && (
        <div className="flex items-center gap-2 text-sm">
          <div className="flex">
            {[1, 2, 3, 4, 5].map((star) => (
              <Star
                key={star}
                className={`size-4 ${
                  star <= Math.round(seller.rating)
                    ? 'fill-yellow-400 text-yellow-400'
                    : 'text-gray-300'
                }`}
              />
            ))}
          </div>
          <span className="font-medium text-(--sea-ink)">{seller.rating.toFixed(1)}</span>
          <span className="text-(--sea-ink-soft)">({seller.review_count} отзывов)</span>
        </div>
      )}
    </div>
  )
}