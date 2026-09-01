import { serverApi } from '../server-proxy'

export const fetchAdminStats = (token: string) =>
  serverApi({ data: { path: '/admin/stats', token } })

export const fetchPendingAds = (token: string) =>
  serverApi({ data: { path: '/admin/ads/pending', token } })

export const fetchAllAds = (token: string) =>
  serverApi({ data: { path: '/admin/ads/all', token } })

export const moderateAd = (token: string, adId: number, data: {action: string, rejection_reason?: string}) =>
  serverApi({ data: { path: `/admin/ads/${adId}/moderate`, method: 'POST', token, body: data } })

export const fetchAdminAdDetail = (token: string, adId: number) =>
  serverApi({ data: { path: `/admin/ads/${adId}`, token } })
