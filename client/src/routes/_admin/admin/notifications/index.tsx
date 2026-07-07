import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Send, Users, User, Bell, CheckCircle } from 'lucide-react'
import { verifySession } from '@/lib/session'
import { usersQueryOptions } from '@/lib/queries/admin/users'
import { sendAdminNotification, broadcastAdminNotification } from '@/lib/api/admin/notifications'

export const Route = createFileRoute('/_admin/admin/notifications')({
  component: NotificationsPage,
  loader: async () => {
    const session = await verifySession()
    return { token: session?.token }
  },
})

type NotifyMode = 'single' | 'broadcast'

function NotificationsPage() {
  const { token } = Route.useLoaderData()
  const [mode, setMode] = useState<NotifyMode>('single')
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [type, setType] = useState('info')
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [sent, setSent] = useState(false)

  const { data: usersData } = useQuery({
    ...usersQueryOptions(token!, 1, 100, searchTerm),
    enabled: !!token,
  })

  const sendMutation = useMutation({
    mutationFn: () => {
      if (mode === 'single' && selectedUserId) {
        return sendAdminNotification(token!, {
          user_id: selectedUserId,
          title,
          message,
          type,
        })
      }
      return broadcastAdminNotification(token!, { title, message, type })
    },
    onSuccess: () => {
      setSent(true)
      setTimeout(() => {
        setSent(false)
        setTitle('')
        setMessage('')
        setSelectedUserId(null)
      }, 2000)
    },
    onError: (err: any) => {
      alert(`Ошибка: ${err.message}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !message.trim()) {
      alert('Заполните заголовок и текст')
      return
    }
    if (mode === 'single' && !selectedUserId) {
      alert('Выберите пользователя')
      return
    }
    sendMutation.mutate()
  }

  const users = usersData?.items || []
  const filteredUsers = searchTerm
    ? users.filter((u: any) =>
        u.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.first_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        String(u.id).includes(searchTerm)
      )
    : users.slice(0, 20)

  return (
    <div className="min-h-screen bg-(--bg)">
      <header className="sticky top-0 z-40 border-b border-(--line) bg-(--header-bg) backdrop-blur-xl">
        <div className="page-wrap">
          <div className="flex h-14 items-center">
            <h1 className="text-lg font-semibold text-(--sea-ink)">Уведомления</h1>
          </div>
        </div>
      </header>

      <div className="page-wrap py-8 max-w-2xl">
        {sent && (
          <div className="mb-6 rounded-xl bg-green-50 border border-green-200 p-4 flex items-center gap-2 text-green-700">
            <CheckCircle className="size-5" />
            <span className="font-medium">Уведомление отправлено!</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Mode Selection */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode('single')}
              className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                mode === 'single'
                  ? 'bg-(--palm) text-white'
                  : 'bg-(--surface-strong) border border-(--line) text-(--sea-ink-soft) hover:border-(--palm)/30'
              }`}
            >
              <User className="size-4" />
              Конкретному пользователю
            </button>
            <button
              type="button"
              onClick={() => setMode('broadcast')}
              className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                mode === 'broadcast'
                  ? 'bg-(--palm) text-white'
                  : 'bg-(--surface-strong) border border-(--line) text-(--sea-ink-soft) hover:border-(--palm)/30'
              }`}
            >
              <Users className="size-4" />
              Рассылка всем
            </button>
          </div>

          {/* User Selection (single mode) */}
          {mode === 'single' && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-(--sea-ink)">Пользователь</label>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Поиск по имени, username или ID..."
                className="w-full rounded-xl border border-(--line) bg-(--surface-strong) px-4 py-2.5 text-sm text-(--sea-ink) focus:border-(--palm) focus:outline-none"
              />
              <div className="max-h-48 overflow-y-auto rounded-xl border border-(--line) divide-y divide-(--line)">
                {filteredUsers.map((u: any) => (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => setSelectedUserId(u.id)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition ${
                      selectedUserId === u.id
                        ? 'bg-(--palm)/10 text-(--palm)'
                        : 'hover:bg-(--link-bg-hover) text-(--sea-ink)'
                    }`}
                  >
                    <span className="font-medium">{u.first_name || 'Без имени'}</span>
                    <span className="text-(--sea-ink-soft)">@{u.username || u.id}</span>
                  </button>
                ))}
                {filteredUsers.length === 0 && (
                  <div className="px-4 py-3 text-sm text-(--sea-ink-soft)">Нет пользователей</div>
                )}
              </div>
            </div>
          )}

          {/* Title */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-(--sea-ink)">Заголовок</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Заголовок уведомления"
              className="w-full rounded-xl border border-(--line) bg-(--surface-strong) px-4 py-2.5 text-sm text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            />
          </div>

          {/* Message */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-(--sea-ink)">Текст</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Текст уведомления..."
              rows={4}
              className="w-full rounded-xl border border-(--line) bg-(--surface-strong) px-4 py-2.5 text-sm text-(--sea-ink) focus:border-(--palm) focus:outline-none resize-none"
            />
          </div>

          {/* Type */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-(--sea-ink)">Тип</label>
            <div className="flex gap-2">
              {[
                { value: 'info', label: 'Инфо', color: 'bg-blue-100 text-blue-700' },
                { value: 'success', label: 'Успех', color: 'bg-green-100 text-green-700' },
                { value: 'warning', label: 'Внимание', color: 'bg-yellow-100 text-yellow-700' },
                { value: 'error', label: 'Ошибка', color: 'bg-red-100 text-red-700' },
              ].map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setType(t.value)}
                  className={`rounded-xl px-3 py-1.5 text-xs font-medium transition ${
                    type === t.value ? t.color : 'bg-(--surface-strong) border border-(--line) text-(--sea-ink-soft)'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={sendMutation.isPending}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-(--palm) px-6 py-3 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50 transition"
          >
            <Send className="size-4" />
            {sendMutation.isPending ? 'Отправка...' : mode === 'broadcast' ? 'Разослать всем' : 'Отправить'}
          </button>
        </form>
      </div>
    </div>
  )
}
