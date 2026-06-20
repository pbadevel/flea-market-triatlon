import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Package } from 'lucide-react'
import { verifySession } from '@/lib/session'
import { serverApi } from '@/lib/api/server-proxy'

interface UserAd {
  id: number; title: string; price: number; city: string; category: string; status: string; created_at: string
}

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

  const { data: ads, isLoading } = useQuery({
    queryKey: ['admin-user-ads', userId],
    queryFn: () => serverApi({ data: { path: `/admin/users/${userId}/ads`, token } }) as Promise<UserAd[]>,
    enabled: !!token,
  })

  const statusMut = useMutation({
    mutationFn: ({ adId, status }: { adId: number; status: string }) =>
      serverApi({ data: { path: `/admin/users/${userId}/ads/${adId}/status`, method: 'PUT', token, body: { status } }}) as Promise<any>,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-user-ads', userId] }),
  })

  return (
    <div className='p-6 max-w-4xl mx-auto'>
      <div className='flex items-center gap-3 mb-6'>
        <Link to='/admin/users' className='rounded p-1.5 hover:bg-gray-100'><ArrowLeft className='size-5' /></Link>
        <h1 className='text-xl font-bold flex items-center gap-2'><Package className='size-5' />Объявления пользователя #{userId}</h1>
      </div>

      {isLoading ? <p className='text-sm text-gray-500'>Загрузка...</p> : !ads?.length ? (
        <p className='text-sm text-gray-500'>У пользователя нет объявлений</p>
      ) : (
        <div className='space-y-2'>
          {ads.map(ad => (
            <div key={ad.id} className='rounded-lg border bg-white p-4 flex items-center justify-between'>
              <div>
                <p className='font-medium'>{ad.title}</p>
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
                <select
                  value={ad.status}
                  onChange={e => statusMut.mutate({ adId: ad.id, status: e.target.value })}
                  className='rounded border px-2 py-1 text-xs'
                >
                  <option value='pending'>pending</option>
                  <option value='approved'>approved</option>
                  <option value='rejected'>rejected</option>
                  <option value='sold'>sold</option>
                  <option value='removed'>removed</option>
                </select>
              </div>
            </div>
          ))}
        </div>
      )}

      <Link to='/admin/users' className='mt-4 inline-block text-sm text-(--palm) hover:underline'>← Назад к пользователям</Link>
    </div>
  )
}
