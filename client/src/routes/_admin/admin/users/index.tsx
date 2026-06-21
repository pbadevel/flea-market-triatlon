import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Users, Search, Shield, ShieldOff, Ban, CheckCircle, Star, Eye } from 'lucide-react'
import { verifySession } from '@/lib/session'
import { fetchUsers, updateUserRole, banUser, unbanUser, makeAdmin } from '@/lib/api/admin/users'
import { toast } from '@/components/ui/toast'
import type { AdminUser } from '@/types/admin'

export const Route = createFileRoute('/_admin/admin/users/')({
  component: UsersPage,
  loader: async () => {
    const session = await verifySession()
    return { token: session?.token, isAdmin: session?.isAdmin ?? false }
  },
})

function UsersPage() {
  const { token, isAdmin } = Route.useLoaderData()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [confirmAction, setConfirmAction] = useState<{ type: string; user: AdminUser } | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', search],
    queryFn: () => fetchUsers(token!, search || undefined),
    enabled: !!token,
  })

  const updateMut = useMutation({
    mutationFn: (d: { id: number; data: { role?: string } }) => updateUserRole(token!, d.id, d.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('Роль обновлена')
    },
    onError: (e) => toast.error(e.message),
  })

  const banMut = useMutation({
    mutationFn: (id: number) => banUser(token!, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('Пользователь забанен')
      setConfirmAction(null)
    },
    onError: (e) => toast.error(e.message),
  })

  const unbanMut = useMutation({
    mutationFn: (id: number) => unbanUser(token!, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('Пользователь разбанен')
      setConfirmAction(null)
    },
    onError: (e) => toast.error(e.message),
  })

  const makeAdminMut = useMutation({
    mutationFn: (id: number) => makeAdmin(token!, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('Пользователь назначен админом')
      setConfirmAction(null)
    },
    onError: (e) => toast.error(e.message),
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold flex items-center gap-2 mb-6"><Users className="size-5" />Пользователи</h1>

      <div className="mb-4 relative">
        <Search className="absolute left-3 top-2.5 size-4 text-gray-400" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Поиск по имени, username или ID..." className="w-full rounded-lg border pl-9 pr-4 py-2 text-sm focus:border-(--palm) focus:outline-none" />
      </div>

      {isLoading ? <p className="text-sm text-gray-500">Загрузка...</p> : !data?.data.length ? <p className="text-sm text-gray-500">Ничего не найдено</p> : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">ID</th>
                <th className="px-4 py-3 text-left font-medium">TG ID</th>
                <th className="px-4 py-3 text-left font-medium">Имя</th>
                <th className="px-4 py-3 text-left font-medium">Username</th>
                <th className="px-4 py-3 text-left font-medium">Роль</th>
                <th className="px-4 py-3 text-left font-medium">Статус</th>
                <th className="px-4 py-3 text-left font-medium">Объявления</th>
                <th className="px-4 py-3 text-left font-medium">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.data.map(u => (
                <tr key={u.id} className={`hover:bg-gray-50 ${u.is_banned ? 'bg-red-50' : ''}`}>
                  <td className="px-4 py-3">{u.id}</td>
                  <td className="px-4 py-3">{u.tg_user_id ?? '-'}</td>
                  <td className="px-4 py-3">{u.first_name || '-'}</td>
                  <td className="px-4 py-3">
                    <Link to="/admin/users/$userId" params={{ userId: String(u.id) }} className="text-(--palm) hover:underline">
                      {u.username ? `@${u.username}` : '-'}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-1">
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                        u.role === 'admin' ? 'bg-purple-100 text-purple-700' :
                        u.role === 'moderator' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>{u.role}</span>
                      {u.is_root && <Star className="size-3 text-yellow-500" title="Root admin" />}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {u.is_banned ? (
                      <span className="rounded px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700">Забанен</span>
                    ) : (
                      <span className="rounded px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700">Активен</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Link to="/admin/users/$userId" params={{ userId: String(u.id) }} className="flex items-center gap-1 text-(--palm) hover:underline whitespace-nowrap">
                      <Eye className="size-3 shrink-0" /> Смотреть
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 shrink-0">
                      {isAdmin && u.role !== 'admin' && !u.is_root && (
                        <button onClick={() => updateMut.mutate({ id: u.id, data: { role: u.role === 'moderator' ? 'user' : 'moderator' } })}
                          className="rounded p-1.5 hover:bg-gray-100"
                          title={u.role === 'moderator' ? 'Снять модератора' : 'Назначить модератором'}>
                          {u.role === 'moderator' ? <ShieldOff className="size-4 text-orange-500" /> : <Shield className="size-4 text-blue-500" />}
                        </button>
                      )}
                      {isAdmin && !u.is_root && u.role !== 'admin' && (
                        <button onClick={() => setConfirmAction({ type: 'makeAdmin', user: u })} className="rounded p-1.5 hover:bg-purple-50" title="Назначить админом">
                          <Star className="size-4 text-purple-500" />
                        </button>
                      )}
                      {!u.is_root && (
                        u.is_banned ? (
                          <button onClick={() => unbanMut.mutate(u.id)} className="rounded p-1.5 hover:bg-green-50" title="Разбанить">
                            <CheckCircle className="size-4 text-green-500" />
                          </button>
                        ) : (
                          <button onClick={() => setConfirmAction({ type: 'ban', user: u })} className="rounded p-1.5 hover:bg-red-50" title="Забанить">
                            <Ban className="size-4 text-red-500" />
                          </button>
                        )
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Link to="/admin" className="mt-4 inline-block text-sm text-(--palm) hover:underline">← Назад в админку</Link>

      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-lg bg-white p-6">
            <h3 className="text-lg font-bold text-(--sea-ink) mb-2">
              {confirmAction.type === 'ban' ? 'Забанить пользователя?' :
               confirmAction.type === 'makeAdmin' ? 'Назначить админом?' : ''}
            </h3>
            <p className="text-sm text-(--sea-ink-soft) mb-4">
              {confirmAction.user.first_name || confirmAction.user.username || `#${confirmAction.user.id}`}
              {confirmAction.type === 'ban' && ' — пользователь потеряет доступ к сервису'}
              {confirmAction.type === 'makeAdmin' && ' — получит полные права администратора'}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  if (confirmAction.type === 'ban') banMut.mutate(confirmAction.user.id)
                  else if (confirmAction.type === 'makeAdmin') makeAdminMut.mutate(confirmAction.user.id)
                }}
                className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium text-white ${
                  confirmAction.type === 'ban' ? 'bg-red-500 hover:bg-red-600' : 'bg-purple-500 hover:bg-purple-600'
                }`}
              >
                {confirmAction.type === 'ban' ? 'Забанить' : 'Назначить'}
              </button>
              <button onClick={() => setConfirmAction(null)} className="flex-1 rounded-lg border border-(--line) px-4 py-2 text-sm font-medium text-(--sea-ink) hover:bg-gray-50">
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
