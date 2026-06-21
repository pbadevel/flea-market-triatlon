import { serverApi } from '../server-proxy'

export const fetchUsers = (token: string, search?: string, page?: number) => {
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (page) params.set('page', String(page))
  return serverApi({ data: { path: `/admin/users?${params.toString()}`, token } })
}

export const fetchUserDetail = (token: string, userId: number) =>
  serverApi({ data: { path: `/admin/users/${userId}`, token } })

export const fetchUserAds = (token: string, userId: number) =>
  serverApi({ data: { path: `/admin/users/${userId}/ads`, token } })

export const updateUserRole = (token: string, userId: number, data: { role: string }) =>
  serverApi({ data: { path: `/admin/users/${userId}`, method: 'PUT', token, body: data } })

export const banUser = (token: string, userId: number) =>
  serverApi({ data: { path: `/admin/users/${userId}/ban`, method: 'POST', token } })

export const unbanUser = (token: string, userId: number) =>
  serverApi({ data: { path: `/admin/users/${userId}/unban`, method: 'POST', token } })

export const makeAdmin = (token: string, userId: number) =>
  serverApi({ data: { path: `/admin/users/${userId}/make-admin`, method: 'POST', token } })

export const deleteUserAd = (token: string, userId: number, adId: number) =>
  serverApi({ data: { path: `/admin/users/${userId}/ads/${adId}`, method: 'DELETE', token } })
