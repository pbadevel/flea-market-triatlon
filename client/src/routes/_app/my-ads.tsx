// src/routes/my-ads.tsx
import { createFileRoute, Link } from '@tanstack/react-router'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, Plus, Eye, CheckCircle, XCircle, Clock, Pencil, Trash2, Send } from 'lucide-react'
import { deleteAd, fetchMyAds, resendAd } from '@/lib/api/client/ads'
import { verifySession } from '@/lib/session'
import { useState } from 'react'
import { queryClient } from '@/lib/query'

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

  const deleteMutation = useMutation({
    mutationFn: (adId: number) => deleteAd(token!, adId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-ads'] })
    },
  })

  const resendMutation = useMutation({
    mutationFn: (adId: number) => resendAd(token!, adId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-ads'] })
    },
  })

  const handleDelete = (adId: number, title: string) => {
    if (confirm(`Удалить объявление "${title}"?`)) {
      deleteMutation.mutate(adId)
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
              <Link
                key={ad.id}
                to="/product/$productId"
                params={{ productId: String(ad.id) }}
                className="flex rounded-lg border border-(--line) bg-white p-4 hover:bg-(--link-bg-hover) transition"
              >
                <div className="flex w-full justify-between items-start gap-4"> 
                  
                  {/* ЛЕВАЯ ЧАСТЬ: Картинка + Характеристики + Кнопки */}
                  <div className="flex items-start flex-1 min-w-0">
                    {ad.cover_url && (
                      <img
                        src={ad.cover_url}
                        alt={ad.title}
                        className="h-20 w-20 shrink-0 rounded-lg object-cover"
                      />
                    )}
                    <div className="flex flex-col px-3 justify-start flex-1 min-w-0">
                      <h3 className="font-medium text-(--sea-ink) line-clamp-1">{ad.title}</h3>
                      <p className="mt-1 text-lg font-bold text-(--sea-ink)">
                        {ad.price.toLocaleString()} ₽
                      </p>
                      <p className="mt-1 text-sm text-(--sea-ink-soft)">
                        {ad.city} · {ad.category}
                      </p>

                      {/* Причина отклонения, если есть */}
                      {ad.status === 'rejected' && ad.rejection_reason && (
                        <p className="mt-2 text-sm text-red-600 font-medium">
                          Причина: {ad.rejection_reason}
                        </p>
                      )}

                      {/* БЛОК КНОПОК УПРАВЛЕНИЯ */}
                      <div className="flex gap-2 mt-3">
                        {/* Кнопка "Просмотреть" для активных объявлений */}
                        {ad.status === 'approved' && (
                          <Link
                            to="/product/$productId"
                            params={{ productId: String(ad.id) }}
                            onClick={(e) => e.stopPropagation()}
                            className="flex items-center gap-1 rounded-lg border border-(--line) px-3 py-1.5 text-xs font-medium text-(--sea-ink) hover:bg-(--link-bg-hover) transition"
                          >
                            <Eye className="size-3" />
                            Просмотреть
                          </Link>
                        )}

                        {/* Кнопка "Редактировать" */}
                        {(ad.status === 'pending' || ad.status === 'rejected' || ad.status === 'approved') && (
                          <Link
                            to="/ads/$adId/edit"
                            params={{ adId: String(ad.id) }}
                            onClick={(e) => e.stopPropagation()}
                            className="flex items-center gap-1 rounded-lg border border-(--line) px-3 py-1.5 text-xs font-medium text-(--sea-ink) hover:bg-(--link-bg-hover) transition"
                          >
                            <Pencil className="size-3" />
                            Редактировать
                          </Link>
                        )}

                        {/* Кнопка "Отправить на модерацию" (только для отклонённых) */}
                        {ad.status === 'rejected' && (
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              resendMutation.mutate(ad.id);
                            }}
                            disabled={resendMutation.isPending}
                            className="flex items-center gap-1 rounded-lg border border-(--palm) px-3 py-1.5 text-xs font-medium text-(--palm) hover:bg-(--palm)/5 disabled:opacity-50 transition"
                          >
                            <Send className="size-3" />
                            {resendMutation.isPending ? 'Отправка...' : 'На модерацию'}
                          </button>
                        )}

                        {/* Кнопка "Удалить" */}
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            handleDelete(ad.id, ad.title);
                          }}
                          disabled={deleteMutation?.isPending}
                          className="flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 transition"
                        >
                          <Trash2 className="size-3" />
                          Удалить
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* ПРАВАЯ ЧАСТЬ: Статус + Дата */}
                  <div className="flex flex-col gap-2 items-end justify-between min-h-[108px] shrink-0">
                    {/* Ваша функция отрисовки статуса */}
                    {getStatusBadge(ad.status)}
                    
                    {/* Дата создания */}
                    <span className="text-xs text-(--sea-ink-soft)">
                      {new Date(ad.created_at).toLocaleDateString('ru-RU')}
                    </span>
                  </div>

                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
