import { serverApi } from '../server-proxy'

export const fetchNotifications = (token: string) =>
  serverApi({ data: { path: '/notifications', token } })

export const fetchUnreadCount = (token: string) =>
  serverApi({ data: { path: '/notifications/unread-count', token } })

export const markAllRead = (token: string) =>
  serverApi({ data: { path: '/notifications/read-all', method: 'POST', token } })
