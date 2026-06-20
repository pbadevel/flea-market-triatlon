import { serverApi } from '../server-proxy'

export const fetchMyProfile = (token: string) =>
  serverApi({ data: { path: '/users/me', token } })

export const updateMyProfile = (token: string, data: Record<string, any>) =>
  serverApi({ data: { path: '/users/me', method: 'PATCH', token, body: data } })

export const fetchMyStats = (token: string) =>
  serverApi({ data: { path: '/users/me/stats', token } })
