import { serverApi } from '../server-proxy'

interface SendNotificationPayload {
  user_id: number
  title: string
  message: string
  type?: string
}

interface BroadcastNotificationPayload {
  title: string
  message: string
  type?: string
}

export const sendAdminNotification = (token: string, payload: SendNotificationPayload) =>
  serverApi({
    data: {
      path: '/admin/notifications/send',
      method: 'POST',
      body: payload,
      token,
    },
  })

export const broadcastAdminNotification = (token: string, payload: BroadcastNotificationPayload) =>
  serverApi({
    data: {
      path: '/admin/notifications/broadcast',
      method: 'POST',
      body: payload,
      token,
    },
  })
