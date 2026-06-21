import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ArrowLeft, Package, Trash2, Mail, Phone, Calendar, Ban, Shield, Star } from 'lucide-react'
import { verifySession } from '@/lib/session'
import { fetchUserDetail, fetchUserAds, deleteUserAd } from '@/lib/api/admin/users'
import { toast } from '@/components/ui/toast'
import type { AdminUserDetail, AdminAd } from '@/types/admin'

export const Route = createFileRoute('/_admin/admin/users/$userId')({
  component: UserDetailPage,
  loader: async ({ params }) => {
    const session = await verifySession()
    return { token: session?.token, userId: Number(params.userId) }
  },
})

function UserDetailPage() {
  const { token, userId } = Route.useLoaderData()
  const qc = useQueryClient()
  const [deleteAdId, setDeleteAdId] = useState<number | null>(null)

  const { data: user, isLoading: userLoading } = useQuery({
    queryKey: ['admin-user-detail', userId],
    queryFn: () => fetchUserDetail(token!, userId) as Promise<AdminUserDetail>,
    enabled: !!token,
  })

  const { data: ads, isLoading: adsLoading } = useQuery({
    queryKey: ['admin-user-ads', userId],
    queryFn: () => fetchUserAds(token!, userId) as Promise<AdminAd[]>,
    enabled: !!token,
  })

  const deleteAdMut = useMutation({
    mutationFn: (adId: number) => deleteUserAd(token!, userId, adId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-user-ads', userId] })
      qc.invalidateQueries({ queryKey: ['admin-user-detail', userId] })
      toast.success('Объявление удалено')
      setDeleteAdId(null)
    },
    onError: (e) => toast.error(e.message),
  })

  const roleColor = (role: string) =>
    role === 'admin' ? 'bg-purple-100 text-purple-700' :
    role === 'moderator' ? 'bg-blue-100 text-blue-700' :
    'bg-gray-100 text-gray-600'

  return (
    <div className='p-6 max-w-4xl mx-auto'>
      <div className='flex items-center gap-3 mb-6'>
        <Link to='/admin/users' className='rounded p-1.5 hover:bg-gray-100'><ArrowLeft className='size-5' /></Link>
        <h1 className='text-xl font-bold flex items-center gap-2'>
          <Package className='size-5' />
          {userLoading ? 'Загрузка...' : `Пользователь #${userId}`}
        </h1>
      </div>

      {user && (
        <div className='rounded-lg border bg-white p-6 mb-6'>
          <div className='flex items-start justify-between mb-4'>
            <div>
              <h2 className='text-lg font-bold flex items-center gap-2'>
                {user.first_name || user.username || `#${user.id}`}
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${roleColor(user.role)}`}>
                  {user.role}
                </span>
                {user.is_root && <Star className='size-4 text-yellow-500' title='Root admin' />}
                {user.is_banned && <Ban className='size-4 text-red-500' title='Забанен' />}
              </h2>
              {user.username && <p className='text-sm text-gray-500'>@{user.username}</p>}
            </div>
            {user.is_banned && (
              <span className='rounded px-3 py-1 text-sm font-medium bg-red-100 text-red-700'>Забанен</span>
            )}
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 gap-4 text-sm'>
            <div className='space-y-2'>
              <div className='flex items-center gap-2 text-gray-600'>
                <span className='font-medium text-gray-500 w-24'>ID:</span>
                <span>{user.id}</span>
              </div>
              <div className='flex items-center gap-2 text-gray-600'>
                <span className='font-medium text-gray-500 w-24'>TG ID:</span>
                <span>{user.tg_user_id ?? 'Не привязан'}</span>
              </div>
              <div className='flex items-center gap-2 text-gray-600'>
                <Calendar className='size-4 text-gray-400' />
                <span className='font-medium text-gray-500 w-20'>Регистрация:</span>
                <span>{user.created_at ? new Date(user.created_at).toLocaleDateString('ru-RU') : '-'}</span>
              </div>
            </div>
            <div className='space-y-2'>
              {user.email && (
                <div className='flex items-center gap-2 text-gray-600'>
                  <Mail className='size-4 text-gray-400' />
                  <span className='font-medium text-gray-500 w-20'>Email:</span>
                  <span>{user.email}</span>
                  {user.is_email_verified && <span className='text-xs text-green-600'>✓</span>}
                </div>
              )}
              {user.phone && (
                <div className='flex items-center gap-2 text-gray-600'>
                  <Phone className='size-4 text-gray-400' />
                  <span className='font-medium text-gray-500 w-20'>Телефон:</span>
                  <span>{user.phone}</span>
                </div>
              )}
              <div className='flex items-center gap-2 text-gray-600'>
                <span className='font-medium text-gray-500 w-24'>Объявлений:</span>
                <span>{user.ads_count}</span>
              </div>
              <div className='flex items-center gap-2 text-gray-600'>
                <Shield className='size-4 text-gray-400' />
                <span className='font-medium text-gray-500 w-20'>Доверенный:</span>
                <span>{user.is_trusted_seller ? 'Да' : 'Нет'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <h2 className='text-lg font-bold mb-4 flex items-center gap-2'>
        <Package className='size-5' />
        Объявления
      </h2>

      {adsLoading ? <p className='text-sm text-gray-500'>Загрузка...</p> : !ads?.length ? (
        <p className='text-sm text-gray-500'>У пользователя нет объявлений</p>
      ) : (
        <div className='space-y-2'>
          {ads.map(ad => (
            <div key={ad.id} className='rounded-lg border bg-white p-4 flex items-center justify-between'>
              <div>
                <Link to='/admin/ads/$adId' params={{ adId: String(ad.id) }} className='font-medium text-(--palm) hover:underline'>
                  {ad.title}
                </Link>
                <p className='text-sm text-gray-500'>{ad.price.toLocaleString()} ₽ — {ad.city} — {ad.category}</p>
                <p className='text-xs text-gray-400'>{ad.created_at}</p>
              </div>
              <div className='flex items-center gap-2'>
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                  ad.status === 'approved' ? 'bg-green-100 text-green-700' :
                  ad.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                  ad.status === 'rejected' ? 'bg-red-100 text-red-700' :
                  ad.status === 'sold' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-600'
                }`}>{ad.status}</span>
                <button
                  onClick={() => setDeleteAdId(ad.id)}
                  className='rounded p-1.5 hover:bg-red-50 text-red-500'
                  title='Удалить'
                >
                  <Trash2 className='size-4' />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Link to='/admin/users' className='mt-4 inline-block text-sm text-(--palm) hover:underline'>← Назад к пользователям</Link>

      {deleteAdId !== null && (
        <div className='fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4'>
          <div className='w-full max-w-sm rounded-lg bg-white p-6'>
            <h3 className='text-lg font-bold text-(--sea-ink) mb-2'>Удалить объявление?</h3>
            <p className='text-sm text-(--sea-ink-soft) mb-4'>Объявление #{deleteAdId} будет удалено безвозвратно</p>
            <div className='flex gap-2'>
              <button
                onClick={() => deleteAdMut.mutate(deleteAdId)}
                className='flex-1 rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600'
              >
                Удалить
              </button>
              <button onClick={() => setDeleteAdId(null)} className='flex-1 rounded-lg border border-(--line) px-4 py-2 text-sm font-medium text-(--sea-ink) hover:bg-gray-50'>
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
