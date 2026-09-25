import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  CheckCircle,
  XCircle,
  Clock,
  Package,
  Users,
  Layers,
  Eye,
  Bell,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import {
  adminStatsQueryOptions,
  pendingAdsQueryOptions,
} from '@/lib/queries/moderator'
import { moderateAd } from '@/lib/api/admin/moderator'
import type { AdminAd, ModerateAdPayload } from '@/types/admin'
import { verifySession } from '@/lib/session'

export const Route = createFileRoute('/_admin/admin/')({
  component: AdminPage,
  loader: async () => {
    const session = await verifySession()
    return {
      token: session?.token,
      isAdmin: session?.isAdmin ?? false,
      isModerator: session?.isModerator ?? false,
    }
  },
})

// ─── Компонент пагинации для админки ────────────────────────────────────────
function AdminPagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}) {
  if (totalPages <= 1) return null

  const handlePageClick = (p: number) => {
    onPageChange(p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const renderPageButton = (p: number) => (
    <button
      key={p}
      onClick={() => handlePageClick(p)}
      className={`min-w-[2.5rem] rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
        p === page
          ? 'bg-(--palm) border-(--palm) text-white'
          : 'border-(--line) bg-white text-(--sea-ink) hover:bg-(--link-bg-hover)'
      }`}
    >
      {p}
    </button>
  )

  const renderEllipsis = (key: string) => (
    <span key={key} className="px-2 text-(--sea-ink-soft)">
      ...
    </span>
  )

  const pages: (number | string)[] = []
  const maxVisible = 5

  if (totalPages <= maxVisible) {
    for (let i = 1; i <= totalPages; i++) pages.push(i)
  } else {
    pages.push(1)
    if (page > 3) pages.push('ellipsis-start')

    const start = Math.max(2, page - 1)
    const end = Math.min(totalPages - 1, page + 1)

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    if (page < totalPages - 2) pages.push('ellipsis-end')
    pages.push(totalPages)
  }

  return (
    <div className="flex items-center justify-center gap-1 mt-6 flex-wrap">
      <button
        onClick={() => handlePageClick(Math.max(1, page - 1))}
        disabled={page <= 1}
        className="flex items-center gap-1 rounded-lg border border-(--line) bg-white px-3 py-2 text-sm text-(--sea-ink) hover:bg-(--link-bg-hover) disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronLeft className="size-4" />
        <span className="hidden sm:inline">Назад</span>
      </button>

      {pages.map((p) =>
        typeof p === 'string' ? renderEllipsis(p) : renderPageButton(p),
      )}

      <button
        onClick={() => handlePageClick(Math.min(totalPages, page + 1))}
        disabled={page >= totalPages}
        className="flex items-center gap-1 rounded-lg border border-(--line) bg-white px-3 py-2 text-sm text-(--sea-ink) hover:bg-(--link-bg-hover) disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <span className="hidden sm:inline">Вперед</span>
        <ChevronRight className="size-4" />
      </button>
    </div>
  )
}
// ────────────────────────────────────────────────────────────────────────────

function AdminPage() {
  const { token, isAdmin, isModerator } = Route.useLoaderData()
  const queryClient = useQueryClient()
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [selectedAd, setSelectedAd] = useState<AdminAd | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')

  // ─── Пагинация ────────────────────────────────────────────────────────
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(10)

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit)
    setPage(1) // Сброс на первую страницу при изменении limit
  }
  // ──────────────────────────────────────────────────────────────────────

  const { data: stats, isLoading: statsLoading } = useQuery(
    adminStatsQueryOptions(token!),
  )

  const { data: pendingAds, isLoading: adsLoading } = useQuery(
    pendingAdsQueryOptions(token!, { page, limit }),
  )

  const totalPages = Math.ceil((pendingAds?.total || 0) / limit)
  const ads = pendingAds?.data || []

  const moderateMutation = useMutation({
    mutationFn: ({ adId, payload }: { adId: number; payload: ModerateAdPayload }) =>
      moderateAd(token!, adId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin'] })
      setShowRejectModal(false)
      setSelectedAd(null)
      setRejectionReason('')
    },
    onError: (error) => {
      alert(`Ошибка: ${error.message}`)
    },
  })

  const handleApprove = (ad: AdminAd) => {
    if (confirm(`Одобрить объявление "${ad.title}"?`)) {
      moderateMutation.mutate({
        adId: ad.id,
        payload: { action: 'approve' },
      })
    }
  }

  const handleReject = (ad: AdminAd) => {
    setSelectedAd(ad)
    setRejectionReason('')
    setShowRejectModal(true)
  }

  const confirmReject = () => {
    if (selectedAd) {
      moderateMutation.mutate({
        adId: selectedAd.id,
        payload: {
          action: 'reject',
          rejection_reason: rejectionReason || 'Не указана причина',
        },
      })
    }
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

  return (
    <div className="min-h-screen bg-(--bg)">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-(--line) bg-(--header-bg)">
        <div className="page-wrap">
          <div className="flex h-14 items-center justify-between">
            <h1 className="text-lg font-semibold text-(--sea-ink)">
              {isAdmin ? 'Панель администратора' : 'Модерация'}
            </h1>
            <Link
              to="/"
              className="text-sm text-(--sea-ink-soft) hover:text-(--sea-ink)"
            >
              На главную
            </Link>
          </div>
        </div>
      </header>

      <div className="page-wrap py-8 space-y-8">
        {/* Navigation — только для админов */}
        {isAdmin && (
          <div className="flex gap-4">
            <Link
              to="/admin/categories"
              className="flex items-center gap-2 rounded-lg border border-(--line) bg-white px-4 py-3 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover) transition"
            >
              <Layers className="size-4" />
              Категории
            </Link>
            <Link
              to="/admin/users"
              className="flex items-center gap-2 rounded-lg border border-(--line) bg-white px-4 py-3 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover) transition"
            >
              <Users className="size-4" />
              Пользователи
            </Link>
            <Link
              to="/admin/notifications"
              className="flex items-center gap-2 rounded-lg border border-(--line) bg-white px-4 py-3 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover) transition"
            >
              <Bell className="size-4" />
              Уведомления
            </Link>
          </div>
        )}
        {/* Stats — только для админов */}
        {isAdmin && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              icon={<Users className="size-5" />}
              label="Пользователей"
              value={stats?.total_users ?? 0}
              loading={statsLoading}
            />
            <StatCard
              icon={<Package className="size-5" />}
              label="Всего объявлений"
              value={stats?.total_ads ?? 0}
              loading={statsLoading}
            />
            <StatCard
              icon={<Clock className="size-5" />}
              label="На модерации"
              value={stats?.pending_ads ?? 0}
              loading={statsLoading}
              color="yellow"
            />
            <StatCard
              icon={<CheckCircle className="size-5" />}
              label="Одобрено"
              value={stats?.approved_ads ?? 0}
              loading={statsLoading}
              color="green"
            />
          </div>
        )}

        {/* Pending Ads — видно всем (админам и модераторам) */}
        <div>
          <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-xl font-bold text-(--sea-ink) flex items-center gap-2">
              <Clock className="size-5" />
              Объявления на модерации
              {pendingAds?.total ? (
                <span className="text-sm font-normal text-(--sea-ink-soft)">
                  ({pendingAds.total})
                </span>
              ) : null}
            </h2>

            {/* Селектор количества на странице + инфо о текущей странице */}
            {totalPages > 1 && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-sm text-(--sea-ink-soft)">
                  <span>Показывать по:</span>
                  <select
                    value={limit}
                    onChange={(e) => handleLimitChange(Number(e.target.value))}
                    className="rounded-lg border border-(--line) bg-white px-2 py-1 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
                <div className="text-sm font-medium text-(--sea-ink-soft)">
                  Страница {page} из {totalPages}
                </div>
              </div>
            )}
          </div>

          {adsLoading ? (
            <div className="text-center py-8 text-(--sea-ink-soft)">
              Загрузка...
            </div>
          ) : !ads.length ? (
            <div className="rounded-lg border border-(--line) bg-white p-8 text-center">
              <CheckCircle className="mx-auto size-12 text-green-500 mb-2" />
              <p className="text-(--sea-ink-soft)">
                Нет объявлений на модерации
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {ads.map((ad) => (
                  <AdModerationCard
                    key={ad.id}
                    ad={ad}
                    onApprove={() => handleApprove(ad)}
                    onReject={() => handleReject(ad)}
                    disabled={moderateMutation.isPending}
                  />
                ))}
              </div>

              {/* Пагинация под списком */}
              <AdminPagination
                page={page}
                totalPages={totalPages}
                onPageChange={handlePageChange}
              />
            </>
          )}
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && selectedAd && (
        <RejectModal
          ad={selectedAd}
          reason={rejectionReason}
          onReasonChange={setRejectionReason}
          onConfirm={confirmReject}
          onCancel={() => {
            setShowRejectModal(false)
            setSelectedAd(null)
            setRejectionReason('')
          }}
          disabled={moderateMutation.isPending}
        />
      )}
    </div>
  )
}

/* ─── Вспомогательные компоненты ── */

function StatCard({
  icon,
  label,
  value,
  loading,
  color = 'default',
}: {
  icon: React.ReactNode
  label: string
  value: number
  loading: boolean
  color?: 'default' | 'yellow' | 'green'
}) {
  const colorMap = {
    default: 'text-(--sea-ink)',
    yellow: 'text-yellow-600',
    green: 'text-green-600',
  }

  return (
    <div className="rounded-lg border border-(--line) bg-white p-4">
      <div className={`flex items-center gap-2 ${colorMap[color]} mb-2`}>
        {icon}
        <span className="text-sm">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${colorMap[color]}`}>
        {loading ? '...' : value}
      </p>
    </div>
  )
}

function AdModerationCard({
  ad,
  onApprove,
  onReject,
  disabled,
}: {
  ad: AdminAd
  onApprove: () => void
  onReject: () => void
  disabled: boolean
}) {
  return (
    <div className="rounded-lg border border-(--line) bg-white p-4">
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex gap-4 flex-1 min-w-0">
          {ad.cover_url && (
            <Link
              to="/admin/ads/$adId"
              params={{ adId: String(ad.id) }}
              className="shrink-0 block"
            >
              <img
                src={ad.cover_url}
                alt={ad.title}
                className="h-20 w-20 md:h-24 md:w-24 rounded-lg object-cover hover:opacity-80 transition"
              />
            </Link>
          )}
          <div className="flex-1 min-w-0">
            <Link
              to="/admin/ads/$adId"
              params={{ adId: String(ad.id) }}
              className="font-medium text-(--sea-ink) line-clamp-2 hover:text-(--palm) transition block"
            >
              {ad.title}
            </Link>
            <p className="mt-1 text-lg font-bold text-(--sea-ink)">
              {ad.price.toLocaleString()} ₽
            </p>
            <p className="mt-1 text-sm text-(--sea-ink-soft)">
              {ad.city}
              {ad.country ? `, ${ad.country}` : ''} · {ad.category}
            </p>
            <p className="mt-1 text-xs text-(--sea-ink-soft)">
              {new Date(ad.created_at).toLocaleString('ru-RU')}
            </p>
          </div>
        </div>
        <div className="flex flex-row md:flex-col gap-2 shrink-0">
          <Link
            to="/admin/ads/$adId"
            params={{ adId: String(ad.id) }}
            className="flex-1 md:flex-none flex items-center justify-center gap-1 rounded-lg border border-(--line) px-3 py-2 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover)"
          >
            <Eye className="size-4" />
            Просмотр
          </Link>
          <button
            onClick={onApprove}
            disabled={disabled}
            className="flex-1 md:flex-none flex items-center justify-center gap-1 rounded-lg bg-green-500 px-3 py-2 text-sm font-medium text-white hover:bg-green-600 disabled:opacity-50"
          >
            <CheckCircle className="size-4" />
            Одобрить
          </button>
          <button
            onClick={onReject}
            disabled={disabled}
            className="flex-1 md:flex-none flex items-center justify-center gap-1 rounded-lg bg-red-500 px-3 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
          >
            <XCircle className="size-4" />
            Отклонить
          </button>
        </div>
      </div>
    </div>
  )
}

function RejectModal({
  ad,
  reason,
  onReasonChange,
  onConfirm,
  onCancel,
  disabled,
}: {
  ad: AdminAd
  reason: string
  onReasonChange: (v: string) => void
  onConfirm: () => void
  onCancel: () => void
  disabled: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6">
        <h3 className="text-lg font-bold text-(--sea-ink) mb-2">
          Отклонить объявление
        </h3>
        <p className="text-sm text-(--sea-ink-soft) mb-4 line-clamp-2">
          {ad.title}
        </p>
        <textarea
          value={reason}
          onChange={(e) => onReasonChange(e.target.value)}
          placeholder="Укажите причину отклонения..."
          rows={4}
          className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none resize-none"
        />
        <div className="mt-4 flex gap-2">
          <button
            onClick={onConfirm}
            disabled={disabled}
            className="flex-1 rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
          >
            Отклонить
          </button>
          <button
            onClick={onCancel}
            className="flex-1 rounded-lg border border-(--line) px-4 py-2 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover)"
          >
            Отмена
          </button>
        </div>
      </div>
    </div>
  )
}