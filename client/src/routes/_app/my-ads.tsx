// src/routes/my-ads.tsx
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Plus, Eye, CheckCircle, XCircle, Clock } from 'lucide-react'
import { fetchMyAds } from '@/lib/api/client/ads'
import { verifySession } from '@/lib/session'
import { useState } from 'react'

export const Route = createFileRoute('/_app/my-ads')({
  loader: async () => {
    // Резолвим сессию в loader
    const session = await verifySession()

    console.log("session in my ads")
    
    return {
      isAuthenticated: !!session.token,
      token: session.token ?? null,
    }
  },
  component: MyAdsPage,
})

function MyAdsPage() {
  const { token } = Route.useLoaderData()
  const [statusFilter, setStatusFilter] = useState<string>('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['my-ads', statusFilter],
    queryFn: () => fetchMyAds(token!, { status: statusFilter || undefined }),
    enabled: !!token,
  })


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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-800">
            <Clock className="size-3" />
            На модерации
          </span>
        )
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
            <CheckCircle className="size-3" />
            Одобрено
          </span>
        )
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
            <XCircle className="size-3" />
            Отклонено
          </span>
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-(--bg)">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-(--line) bg-(--header-bg)">
        <div className="page-wrap">
          <div className="flex h-14 items-center justify-between">
            <div className="flex items-center gap-3">
              <Link
                to="/"
                className="flex items-center gap-1 text-(--sea-ink-soft) hover:text-(--sea-ink)"
              >
                <ArrowLeft className="size-5" />
                <span className="text-sm">Назад</span>
              </Link>
              <h1 className="text-lg font-semibold text-(--sea-ink)">
                Мои объявления
              </h1>
            </div>
            <Link
              to="/create-ad"
              className="flex items-center gap-1 rounded-lg bg-(--palm) px-3 py-1.5 text-sm font-medium text-white hover:bg-(--palm)/90"
            >
              <Plus className="size-4" />
              Создать
            </Link>
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="page-wrap py-4">
        <div className="flex gap-2 overflow-x-auto">
          <button
            onClick={() => setStatusFilter('')}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm ${
              !statusFilter
                ? 'bg-(--palm) text-white'
                : 'border border-(--line) text-(--sea-ink) hover:bg-(--link-bg-hover)'
            }`}
          >
            Все
          </button>
          <button
            onClick={() => setStatusFilter('pending')}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm ${
              statusFilter === 'pending'
                ? 'bg-(--palm) text-white'
                : 'border border-(--line) text-(--sea-ink) hover:bg-(--link-bg-hover)'
            }`}
          >
            На модерации
          </button>
          <button
            onClick={() => setStatusFilter('approved')}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm ${
              statusFilter === 'approved'
                ? 'bg-(--palm) text-white'
                : 'border border-(--line) text-(--sea-ink) hover:bg-(--link-bg-hover)'
            }`}
          >
            Одобрено
          </button>
          <button
            onClick={() => setStatusFilter('rejected')}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm ${
              statusFilter === 'rejected'
                ? 'bg-(--palm) text-white'
                : 'border border-(--line) text-(--sea-ink) hover:bg-(--link-bg-hover)'
            }`}
          >
            Отклонено
          </button>
        </div>
      </div>

      {/* Ads List */}
      <div className="page-wrap pb-8">
        {isLoading ? (
          <div className="text-center py-8 text-(--sea-ink-soft)">Загрузка...</div>
        ) : isError ? (
          <div className="text-center py-8 text-red-500">Ошибка загрузки</div>
        ) : !data?.data.length ? (
          <div className="text-center py-12">
            <p className="text-(--sea-ink-soft) mb-4">У вас пока нет объявлений</p>
            <Link
              to="/create-ad"
              className="inline-flex items-center gap-2 text-(--palm) hover:underline"
            >
              <Plus className="size-4" />
              Создать первое объявление
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {data.data.map((ad) => (
              <div
                key={ad.id}
                className="rounded-lg border border-(--line) bg-white p-4"
              >
                <div className="flex gap-4">
                  {ad.cover_url && (
                    <img
                      src={ad.cover_url}
                      alt={ad.title}
                      className="h-20 w-20 shrink-0 rounded-lg object-cover"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-medium text-(--sea-ink) line-clamp-2">
                        {ad.title}
                      </h3>
                      {getStatusBadge(ad.status)}
                    </div>
                    <p className="mt-1 text-lg font-bold text-(--sea-ink)">
                      {ad.price.toLocaleString()} ₽
                    </p>
                    <p className="mt-1 text-sm text-(--sea-ink-soft)">
                      {ad.city} · {ad.category}
                    </p>
                    {ad.status === 'rejected' && ad.rejection_reason && (
                      <p className="mt-2 text-sm text-red-600">
                        Причина: {ad.rejection_reason}
                      </p>
                    )}
                    <div className="mt-2 flex gap-2">
                      {ad.status === 'approved' && (
                        <Link
                          to="/product/$productId"
                          params={{ productId: String(ad.id) }}
                          className="inline-flex items-center gap-1 text-sm text-(--palm) hover:underline"
                        >
                          <Eye className="size-3" />
                          Просмотреть
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}