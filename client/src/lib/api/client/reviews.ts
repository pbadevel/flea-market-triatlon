import { serverApi } from '../server-proxy'

export const createReview = (token: string, data: { ad_id: number; rating: number; comment?: string }) =>
  serverApi({ data: { path: '/reviews', method: 'POST', token, body: data } })
